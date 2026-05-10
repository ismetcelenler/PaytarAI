"""
PaytarAI — Retriever Node

Dual-language search: Sorguyu hem orijinal dilde hem cevrilmis dilde arar.
Sonuclari birlestirip en yuksek skorlu olanlari alir.
"""

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
from app.rag.query_translator import translate_query, detect_language
from app.graph.audit import audit_log


def _merge_results(results_a: list[dict], results_b: list[dict], limit: int = 5) -> list[dict]:
    """Iki arama sonucunu birlestir, duplikatlari kaldir, skora gore sirala."""
    seen_texts = set()
    merged = []

    for r in results_a + results_b:
        # Ilk 100 karakter ile dedup
        text_key = r["text"][:100]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            merged.append(r)

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:limit]


def retriever_node(state: dict) -> dict:
    """
    Retriever node — dual language search.

    1. Orijinal sorguyla arar
    2. Sorguyu diger dile cevirir (Groq, ucretsiz)
    3. Cevrilmis sorguyla tekrar arar
    4. Sonuclari birlestirip en iyi 5'i alir
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    # Son kullanici mesajini al
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    if not last_user_msg:
        return state

    # Rol bazli filtreleme — ileride aktiflestirilecek
    user_role = state.get("user_role", "producer")
    filters = None

    # --- 1. Orijinal dilde arama ---
    original_vector = embed_single(last_user_msg)
    original_results = search(
        query_vector=original_vector,
        limit=5,
        score_threshold=0.25,
        filters=filters,
    )

    # --- 2. Diger dilde arama (Groq ile ceviri, ucretsiz) ---
    lang = detect_language(last_user_msg)
    target_lang = "English" if lang == "tr" else "Turkish"

    translated_query = translate_query(last_user_msg, target_lang)
    translated_results = []

    if translated_query:
        translated_vector = embed_single(translated_query)
        translated_results = search(
            query_vector=translated_vector,
            limit=5,
            score_threshold=0.25,
            filters=filters,
        )

    # --- 3. Sonuclari birlestir ---
    merged = _merge_results(original_results, translated_results, limit=5)

    state["retrieved_docs"] = merged

    # En yuksek similarity score'u kaydet
    if merged:
        state["retrieval_similarity_score"] = merged[0]["score"]
        if len(merged) >= 2:
            score_diff = abs(merged[0]["score"] - merged[1]["score"])
            state["source_agreement"] = score_diff < 0.15
        else:
            state["source_agreement"] = False
    else:
        state["retrieval_similarity_score"] = 0.0
        state["source_agreement"] = False

    audit_log(
        state,
        "retrieval_done",
        reason=(
            f"{len(merged)} docs (orig={len(original_results)}, "
            f"translated={len(translated_results)}), "
            f"top_score={state['retrieval_similarity_score']:.4f}, "
            f"query_lang={lang}, translated={'yes' if translated_query else 'no'}"
        ),
        source_ids=[r["metadata"].get("source_title", "") for r in merged[:3]],
    )

    return state
