"""
Reranker debug — dense top-30 vs reranker top-3 yan yana.

Generator/critic calistirilmaz, sadece retrieval ayagi:
  1. Dense (BGE-M3) top-30 ile aday havuz
  2. Cross-encoder (BGE-reranker-v2-m3) ile yeniden sirala
  3. Dense top-3 ve reranker top-3'u karsilastir

Kullanim:
  python scripts/inspect_reranker.py "sut hummasi patogenezi"
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
from app.rag.query_translator import enrich_query
from app.rag.reranker import rerank


def _short(text: str, n: int = 140) -> str:
    t = text.replace("\n", " ").strip()
    return (t[:n] + "...") if len(t) > n else t


def _ascii(s: str) -> str:
    return s.encode("ascii", "replace").decode("ascii")


def main():
    if len(sys.argv) < 2:
        query = "süt humması patogenezi kalsiyum homeostazı"
    else:
        query = " ".join(sys.argv[1:])

    print(f"=== SORGU: {_ascii(query)} ===\n")

    # 1) Enrich
    enriched = enrich_query(query)
    print(f"Enriched query: {_ascii(enriched) if enriched else '(yok)'}\n")

    # 2) Dense top-30 (orijinal)
    v_orig = embed_single(query)
    dense_orig = search(query_vector=v_orig, limit=30, score_threshold=0.25)

    # 3) Dense top-30 (enriched)
    dense_enr = []
    if enriched:
        v_enr = embed_single(enriched)
        dense_enr = search(query_vector=v_enr, limit=30, score_threshold=0.25)

    # 4) Birlestir (dedup ilk 100 char)
    seen = set()
    candidates = []
    for r in dense_orig + dense_enr:
        if r.get("score", 0) < 0.30:
            continue
        k = r["text"][:100]
        if k not in seen:
            seen.add(k)
            candidates.append(r)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    candidates = candidates[:30]

    print(f"Dense candidates: {len(candidates)} (orig={len(dense_orig)}, enr={len(dense_enr)})\n")

    # 5) Dense top-3 (reranker oncesi)
    dense_top3 = candidates[:3]
    print("=" * 70)
    print("DENSE TOP-3 (reranker ONCESI):")
    print("=" * 70)
    for i, d in enumerate(dense_top3, 1):
        meta = d.get("metadata", {})
        print(f"\n[D{i}] dense_score={d['score']:.4f} | source={meta.get('source_title', '?')}")
        print(f"     {_ascii(_short(d.get('text', '')))}")

    # 6) Reranker calistir
    rerank_query = f"{query} | {enriched}" if enriched else query
    print(f"\n\nRerank query: {_ascii(rerank_query)}\n")

    reranked = rerank(rerank_query, list(candidates), top_k=3)

    # 7) Reranker top-3
    print("=" * 70)
    print("RERANKER TOP-3 (cross-encoder SONRASI):")
    print("=" * 70)
    for i, d in enumerate(reranked, 1):
        meta = d.get("metadata", {})
        print(f"\n[R{i}] rerank_logit={d.get('rerank_logit', 0):.4f}  "
              f"rerank_score={d.get('rerank_score', 0):.4f}  "
              f"dense={d.get('score', 0):.4f}")
        print(f"     source={meta.get('source_title', '?')}")
        print(f"     {_ascii(_short(d.get('text', '')))}")

    # 8) Logit dagilimi
    all_logits = sorted([d.get("rerank_logit", 0) for d in candidates], reverse=True)
    print("\n" + "=" * 70)
    print("LOGIT DAGILIMI (tum 30 chunk, yuksekten dusuge):")
    print("=" * 70)
    for i, lg in enumerate(all_logits, 1):
        bar = "#" * max(0, int((lg + 12) * 2))
        print(f"  #{i:2d}: logit={lg:7.3f}  sigmoid={1/(1+pow(2.71828,-lg)):.4f}  {bar}")

    # 9) Karsilastirma ozeti
    dense_texts = set(d["text"][:100] for d in dense_top3)
    rerank_texts = set(d["text"][:100] for d in reranked)
    overlap = dense_texts & rerank_texts
    print("\n" + "=" * 70)
    print("DENSE vs RERANK OVERLAP:")
    print("=" * 70)
    print(f"  Dense top-3 ile reranker top-3 ortak chunk sayisi: {len(overlap)}/3")
    if len(overlap) == 3:
        print("  -> Reranker dense ile AYNI top-3'u secti (etki yok)")
    elif len(overlap) == 0:
        print("  -> Reranker dense ile HIC ORTAK chunk secmedi (radikal degisim)")
    else:
        print(f"  -> Reranker {3 - len(overlap)} chunk'u DEGISTIRDI")


if __name__ == "__main__":
    main()
