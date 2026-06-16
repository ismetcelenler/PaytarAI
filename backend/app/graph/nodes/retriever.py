"""
PaytarAI — Retriever Node (Phase 3: Hybrid Retrieval)

Cok kanalli retrieval (production medical RAG 2026 patterni):
  1) Dense (BGE-M3) — orijinal sorgu
  2) Dense — enriched keywords (TR+EN)
  3) Dense — Multi-HyDE (3 hayali cevap varyanti)
  4) Dense — Step-Back (genis kavramsal form)
  5) BM25 (sparse) — orijinal sorgu, spesifik isim/jargon eslemesi icin
  6) Cross-encoder reranker (BGE-reranker-v2-m3) — ince elek

Reference: MEGA-RAG (PMC 2026), Multi-HyDE (arxiv 2509.16369),
Step-Back (DeepMind 2024), Hybrid BM25+Dense 2026 production guide.
"""

import time

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
from app.rag.bm25_store import bm25_search
from app.rag.reranker import rerank
from app.graph.audit import audit_log
from app.graph.debug_trace import trace_node
from app.graph.query_compose import compose_user_query

# NOT: step_back kanalı v7'de KALDIRILDI. HyDE × 3 zaten kavramsal genişletmenin
# büyük kısmını yapıyordu, step-back ile %70+ örtüşme ölçüldü. 3-5s LLM cağrısı
# tasarrufu için kaldırıldı. step_back.py dosyası tarihsel veri için duruyor.


def _snapshot_chunks(chunks: list[dict], top_n: int = 10) -> list[dict]:
    """Bir kanaldan gelen chunk listesini debug trace icin kucuk snapshot'a indirger."""
    out = []
    for c in chunks[:top_n]:
        meta = c.get("metadata", {}) or {}
        out.append({
            "title": meta.get("source_title", "?"),
            "score": round(float(c.get("score") or 0.0), 4),
            "text_preview": (c.get("text", "") or "")[:300],
            "text_len": len(c.get("text", "") or ""),
        })
    return out


# Dense retrieval'da kac chunk getirelim — reranker bunu top-3'e indirir.
# 30 makul: yeterli aday ama reranker GPU latency hala sub-100ms.
DENSE_TOP_N = 30
BM25_TOP_N = 30
RERANK_TOP_K = 3


def _merge_results(results_a: list[dict], results_b: list[dict], limit: int = 5, threshold: float = 0.30) -> list[dict]:
    """Iki arama sonucunu birlestir, duplikatlari kaldir, skora gore sirala ve threshold uygula."""
    seen_texts = set()
    merged = []

    for r in results_a + results_b:
        # Score threshold kontrolu (alakasiz kaynaklari filtrele)
        if r.get("score", 0) < threshold:
            continue

        # Ilk 100 karakter ile dedup
        text_key = r["text"][:100]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            merged.append(r)

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:limit]


def _merge_bm25(dense_results: list[dict], bm25_results: list[dict], limit: int) -> list[dict]:
    """
    Dense ve BM25 sonuclarini RRF (Reciprocal Rank Fusion) ile birlestir.

    RRF skor: 1 / (k + rank), k=60 (standart).
    Aynı doc her iki kanalda da varsa skoru toplanir (rank uyumu).
    Dedup ilk 100 char ile.

    NOT: Chunk'in orijinal "score" field'i degistirilmez (dense cosine veya BM25 raw).
    RRF skoru "_rrf_score" altinda saklanir, SADECE siralama icin kullanilir.
    Bu sayede eval/generator chunk["score"]'u okudugunda dogal degerini gorur.
    """
    K = 60
    seen_keys: dict[str, dict] = {}

    for rank, r in enumerate(dense_results):
        key = r["text"][:100]
        rrf = 1.0 / (K + rank + 1)
        seen_keys[key] = {**r, "_rrf_score": rrf}

    for rank, r in enumerate(bm25_results):
        key = r["text"][:100]
        rrf = 1.0 / (K + rank + 1)
        if key in seen_keys:
            seen_keys[key]["_rrf_score"] += rrf
        else:
            # BM25-only chunk: raw BM25 skor 5-30 araliginda olur.
            # Eval threshold (0.45) ve confidence gate (0.60) cosine'a kalibre.
            # Normalize: clip(raw / 15, 0, 1). 15 ortalama-iyi BM25 skoru.
            raw = float(r.get("score") or 0.0)
            normalized = min(max(raw / 15.0, 0.0), 1.0)
            seen_keys[key] = {**r, "_rrf_score": rrf, "score": normalized}

    merged = list(seen_keys.values())
    merged.sort(key=lambda x: x.get("_rrf_score", 0.0), reverse=True)
    return merged[:limit]


def retriever_node(state: dict) -> dict:
    """
    Retriever node — hybrid multi-channel retrieval.
    """
    t0 = time.perf_counter()
    messages = state.get("messages", [])
    if not messages:
        return state

    # Multi-turn destek: clarification akisinda son user mesajini ONCEKI
    # ilgili user mesajlariyla birleştir. Boylece embed/HyDE/BM25 hepsi
    # birlesik bağlami görür ve takip cevabi yalniz başina genel kalmaz.
    last_user_msg = compose_user_query(messages)
    if not last_user_msg:
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
            elif hasattr(msg, "type") and msg.type == "human":
                last_user_msg = msg.content
                break

    if not last_user_msg:
        return state

    # Rol bazli filtreleme — ileride aktiflestirilecek
    user_role = state.get("user_role", "producer")
    filters = None

    # --- 1. Dense retrieval (top-N geniş ağ) — orijinal sorgu ---
    original_vector = embed_single(last_user_msg)
    original_results = search(
        query_vector=original_vector,
        limit=DENSE_TOP_N,
        score_threshold=0.25,
        filters=filters,
    )

    # --- 2 + 3. Multi-HyDE + Enriched keywords scope_check_node icinde TEK call ile uretildi.
    # State'ten oku, ekstra LLM cagri yapma.
    analysis = state.get("query_analysis") or {}
    enriched_query = analysis.get("enriched_keywords", "") or ""
    hyde_variants = analysis.get("hyde_variants", []) or []
    # CROSS-LINGUAL: kullanici sorgusunun Ingilizce cevirisi — EN pool'unu kendi
    # natif dilinde rerank etmek icin (LAURA paper bias mitigation + BGE-reranker
    # en guclu olarak ayni dildeki sorgu-belge ciftlerinde calisiyor).
    en_translated_query = analysis.get("en_translated_query", "") or ""
    # MEDICAL REWRITE (v7) — analyzer'in ADIM 5/6'da urettiği reranker icin
    # ozel TEK CUMLE tibbi formulasyon. composed user query uzun ve konusma
    # dilinde olunca BGE-reranker chunk'larla zayif eslesiyordu. Bu cumleler
    # ders kitabı diliyle yazildigi icin chunk'larla daha guclu pair'lesir.
    tr_rerank_query_rewrite = analysis.get("tr_rerank_query", "") or ""
    en_rerank_query_rewrite = analysis.get("en_rerank_query", "") or ""

    translated_results = []
    if enriched_query:
        enriched_vector = embed_single(enriched_query)
        translated_results = search(
            query_vector=enriched_vector,
            limit=DENSE_TOP_N,
            score_threshold=0.25,
            filters=filters,
        )

    hyde_results_all: list[dict] = []
    for variant in hyde_variants:
        vec = embed_single(variant)
        hyde_results_all.extend(search(
            query_vector=vec,
            limit=DENSE_TOP_N,
            score_threshold=0.25,
            filters=filters,
        ))

    # --- 4. BM25 sparse retrieval — spesifik isim/jargon eslemesi (Mortellaro vb) ---
    bm25_results = []
    try:
        bm25_results = bm25_search(last_user_msg, limit=BM25_TOP_N)
    except Exception as e:
        print(f"[Retriever] BM25 atlandi: {e}")

    # --- 5. Tum kanallari birlestir (dedup, threshold, sirala) ---
    # Dense skorlarin (0-1 cosine) ve BM25 (raw skor) ayni listeye girince
    # _merge_results threshold (0.30) sadece dense'e uygulanir; BM25 her zaman gecer.
    # Cross-encoder rerank zaten final precision'i saglar.
    merged = _merge_results(original_results, translated_results, limit=DENSE_TOP_N)
    merged = _merge_results(merged, hyde_results_all, limit=DENSE_TOP_N)

    # Confidence gate icin ORIJINAL dense top skor (cosine) — RRF'den ONCE
    all_dense = original_results + translated_results + hyde_results_all
    dense_top_cosine = max(
        (float(r.get("score") or 0.0) for r in all_dense),
        default=0.0,
    )

    # BM25 sonuclarini threshold uygulamadan ekle (skor scale farkli)
    candidates = _merge_bm25(merged, bm25_results, limit=DENSE_TOP_N + BM25_TOP_N)

    # --- 6. LANGUAGE-BALANCED RERANK (v4 — LAURA paper bias mitigation) ---
    # Eski: tek bir rerank cagrisi, TR sorgu + EN keyword stuffing, butun karisik pool.
    # Sorun: BGE-reranker-v2-m3 TR query + EN chunk pair'inde sistematik bias →
    #        EN chunk'lar (Rebhuns) top-3'e giremiyor.
    # Cozum: candidates'i dile gore ikiye bol, her pool kendi NATIF dilindeki sorgu
    #        ile rerank et. TR pool TR query gorur, EN pool en_translated_query gorur.
    #        Sonuc concatenated (re-sort yok) → generator her dilden top-K gorur.
    # Kaynak: arxiv 2604.20199 (LAURA), arxiv 2311.09175 (no keyword stuffing in rerank).
    tr_candidates = [c for c in candidates if (c.get("metadata") or {}).get("language") == "tr"]
    en_candidates = [c for c in candidates if (c.get("metadata") or {}).get("language") == "en"]

    # TR pool rerank query — oncelik fallback chain:
    #   1) Analyzer'in TR tibbi rewrite'i (ADIM 5) — ders kitabi diliyle pair'lesme
    #   2) Composed user msg (multi-turn ham metin) — eski davranis
    tr_rerank_query = tr_rerank_query_rewrite or last_user_msg
    tr_top = rerank(tr_rerank_query, tr_candidates, top_k=RERANK_TOP_K) if tr_candidates else []

    # EN pool rerank query — oncelik fallback chain:
    #   1) Analyzer'in EN tibbi rewrite'i (ADIM 6) — tibbi tek cumle
    #   2) Analyzer'in dogal EN_QUERY cevirisi (ADIM 4)
    #   3) Composed user msg (en kotu durum)
    en_rerank_query = en_rerank_query_rewrite or en_translated_query or last_user_msg
    en_top = rerank(en_rerank_query, en_candidates, top_k=RERANK_TOP_K) if en_candidates else []

    # Generator'a giden final sira: TR top-K ardindan EN top-K, RE-SORT YOK.
    # (Cross-encoder logit scale'i diller arasi karsilastirilabilir degil —
    #  TR-TR ciftleri her zaman daha yuksek logit; merge sort bias geri getirir.)
    final_docs = tr_top + en_top

    state["retrieved_docs"] = final_docs

    # Skorlama:
    #   retrieval_similarity_score = DENSE COSINE top score (confidence gate icin)
    #     - Reranker skoru sigmoid output (0-1), cosine'dan farkli — gate threshold
    #       (0.60) cosine'a kalibre. Reranker skorunu buraya yazarsan gate bozulur.
    #   rerank_top_score = reranker output (audit/log icin)
    if final_docs:
        rerank_top = float(final_docs[0].get("rerank_score") or 0.0)

        # Confidence gate: ORIJINAL dense cosine skoru (RRF degil)
        # RRF skoru 0.01-0.03 araliginda — gate threshold (0.60 cosine) ile uyumsuz
        state["retrieval_similarity_score"] = dense_top_cosine
        state["rerank_top_score"] = rerank_top  # yeni alan, audit/log icin

        if len(final_docs) >= 2:
            rerank_second = float(final_docs[1].get("rerank_score") or 0.0)
            state["source_agreement"] = abs(rerank_top - rerank_second) < 0.15
        else:
            state["source_agreement"] = False
    else:
        state["retrieval_similarity_score"] = 0.0
        state["rerank_top_score"] = 0.0
        state["source_agreement"] = False

    audit_log(
        state,
        "retrieval_done",
        reason=(
            f"candidates={len(candidates)} "
            f"(orig={len(original_results)}, enriched={len(translated_results)}, "
            f"hyde_variants={len(hyde_variants)} [{len(hyde_results_all)} chunks], "
            f"bm25={len(bm25_results)}), "
            f"reranked_top_k={len(final_docs)}, "
            f"dense_top={state['retrieval_similarity_score']:.4f}, "
            f"rerank_top={state.get('rerank_top_score', 0.0):.4f}"
        ),
        source_ids=[r["metadata"].get("source_title", "") for r in final_docs],
    )

    # Debug trace — KANAL kanal cikti + pre/post rerank
    latency_ms = (time.perf_counter() - t0) * 1000
    final_snapshot = []
    for d in final_docs:
        meta = d.get("metadata", {}) or {}
        final_snapshot.append({
            "title": meta.get("source_title", "?"),
            "language": meta.get("language", "?"),
            "dense_score": round(float(d.get("score") or 0.0), 4),
            "rerank_logit": round(float(d.get("rerank_logit") or 0.0), 4),
            "rerank_sigmoid": round(float(d.get("rerank_score") or 0.0), 4),
            "text_full": d.get("text", "") or "",
            "text_len": len(d.get("text", "") or ""),
        })

    # TR ve EN pool'larin ayri snapshot'lari (UI ayri ayri gostermek icin)
    def _snapshot_reranked(docs: list[dict]) -> list[dict]:
        out = []
        for d in docs:
            meta = d.get("metadata", {}) or {}
            out.append({
                "title": meta.get("source_title", "?"),
                "language": meta.get("language", "?"),
                "dense_score": round(float(d.get("score") or 0.0), 4),
                "rerank_logit": round(float(d.get("rerank_logit") or 0.0), 4),
                "rerank_sigmoid": round(float(d.get("rerank_score") or 0.0), 4),
                "text_full": d.get("text", "") or "",
                "text_len": len(d.get("text", "") or ""),
            })
        return out

    trace_node(
        state,
        "retriever",
        input={
            "user_query": last_user_msg,
            "enriched_keywords": enriched_query,
            "hyde_variants": hyde_variants,
            "en_translated_query": en_translated_query,
            # Analyzer'in ADIM 5/6 rewrite'lari — debug panelinde gorulebilsin diye
            "tr_rerank_rewrite": tr_rerank_query_rewrite,
            "en_rerank_rewrite": en_rerank_query_rewrite,
            # Reranker'a fiilen GIDEN sorgu (fallback chain sonucu)
            "tr_rerank_query": tr_rerank_query,
            "en_rerank_query": en_rerank_query,
        },
        output={
            "channels": {
                "original_dense":  _snapshot_chunks(original_results, top_n=10),
                "enriched_dense":  _snapshot_chunks(translated_results, top_n=10),
                "hyde_dense":      _snapshot_chunks(hyde_results_all, top_n=10),
                "bm25_sparse":     _snapshot_chunks(bm25_results, top_n=10),
            },
            "candidates_count": len(candidates),
            "candidates_top10": _snapshot_chunks(candidates, top_n=10),
            "language_pools": {
                "tr_pool_size": len(tr_candidates),
                "en_pool_size": len(en_candidates),
                "tr_reranked": _snapshot_reranked(tr_top),
                "en_reranked": _snapshot_reranked(en_top),
            },
            "reranked_top_k": final_snapshot,
            "scores": {
                "dense_top": round(dense_top_cosine, 4),
                "rerank_top": round(state.get("rerank_top_score", 0.0), 4),
            },
        },
        latency_ms=latency_ms,
    )

    return state
