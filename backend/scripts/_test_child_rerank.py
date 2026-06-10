"""
Child rerank vs Parent rerank karsilastirma.

Hipotez: Cross-encoder PARENT (2600 char) icerisinde yuzeysel konsept
eslemesi yapip yuksek false-positive skor veriyor. Daha kisa CHILD
(300 char) ile reranklasak, spesifik hastalik/terim adi yoksa cross-encoder
dusuk skor verir → daha precise.

Test: producer_02, vet_03, vet_09 (basarisiz case'ler) icin
- Top-100 dense aday cek
- Hem CHILD hem PARENT ile rerank et
- TOP-10 skorlari karsilastir

Beklenen:
- Eger child rerank dusurursek (parent yanilgisini eler) -> child rerank cozum
- Eger child rerank de yuksek false-positive verirse -> grounding gate sart
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.rag.embeddings import embed_single
from app.rag.query_translator import enrich_query
from app.rag.reranker import rerank
from qdrant_client import QdrantClient


CASES = [
    {
        "id": "producer_02",
        "query": "dogumdan 3 gun gecti sutum dusuk hayvan da halsiz gozukuyor normal mi",
    },
    {
        "id": "vet_03",
        "query": "Akut puerperal metritis ile kronik endometritis ayirici tani kriterleri nelerdir, tedavi nasil farklilasiyor?",
    },
    {
        "id": "vet_09",
        "query": "Mortellaro hastaligi kronik vakada uzun donem prognoz nasil? Suru duzeyinde kontrol protokolu onerisi var mi?",
    },
]


def fetch_top_n_with_both_texts(query_vec, top_n=100):
    """Qdrant'tan top-N getir, hem child hem parent text'i tut."""
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=60)
    results = client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_vec,
        limit=top_n,
        score_threshold=0.25,
    )
    docs = []
    for p in results.points:
        child = p.payload.get("text", "") or ""
        parent = p.payload.get("parent_text", "") or child
        docs.append({
            "score": p.score,
            "child_text": child,
            "parent_text": parent,
            "metadata": {
                "source_title": p.payload.get("source_title", "?"),
                "language": p.payload.get("language", "?"),
            },
        })
    return docs


def run_one(case):
    print(f"\n{'='*100}")
    print(f"CASE: {case['id']}")
    print(f"Query: {case['query']}")
    print(f"{'='*100}\n")

    vec_orig = embed_single(case["query"])
    enriched = enrich_query(case["query"])
    print(f"[Enrich] {enriched[:120] if enriched else '(none)'}\n")

    # Dense top-100 (orijinal + enriched)
    docs_orig = fetch_top_n_with_both_texts(vec_orig, top_n=100)
    if enriched:
        vec_en = embed_single(enriched)
        docs_en = fetch_top_n_with_both_texts(vec_en, top_n=100)
    else:
        docs_en = []

    # Dedup by child text first 100 chars
    seen = set()
    combined = []
    for d in docs_orig + docs_en:
        key = d["child_text"][:100]
        if key not in seen:
            seen.add(key)
            combined.append(d)
    combined.sort(key=lambda x: x["score"], reverse=True)
    combined = combined[:100]

    print(f"Toplam {len(combined)} unique aday\n")

    rerank_query = f"{case['query']} | {enriched}" if enriched else case["query"]

    # PARENT ile rerank
    parent_docs = [{"text": d["parent_text"], "score": d["score"], "metadata": d["metadata"]} for d in combined]
    parent_reranked = rerank(rerank_query, parent_docs, top_k=100)

    # CHILD ile rerank
    child_docs = [{"text": d["child_text"], "score": d["score"], "metadata": d["metadata"]} for d in combined]
    child_reranked = rerank(rerank_query, child_docs, top_k=100)

    # Skorlari karsilastir: ayni siralama indeksleri varsa eslestir
    # Asagidaki ayni sirayla geliyor zaten (combined order)

    # Skor karsilastirmasi icin: text'lerin ilk 60 char'i ile match
    def key_of(d):
        return d["text"][:60]

    parent_score_by_idx = {i: (d.get("rerank_score") or 0, key_of(d)) for i, d in enumerate(parent_reranked)}
    child_score_by_idx = {i: (d.get("rerank_score") or 0, key_of(d)) for i, d in enumerate(child_reranked)}

    # TOP-10 PARENT
    parent_sorted = sorted(parent_reranked, key=lambda x: x.get("rerank_score") or 0, reverse=True)
    child_sorted = sorted(child_reranked, key=lambda x: x.get("rerank_score") or 0, reverse=True)

    print(f"--- TOP-10 (PARENT ile rerank) ---")
    print(f"{'Rank':<5}{'Rerank':>7}  {'Source':<32} Preview")
    print("-" * 130)
    for i, d in enumerate(parent_sorted[:10], 1):
        src = d["metadata"].get("source_title", "?")[:30]
        preview = d["text"].replace("\n", " ").strip()[:75]
        print(f"{i:<5}{d.get('rerank_score', 0):>7.3f}  {src:<32} {preview}")

    print(f"\n--- TOP-10 (CHILD ile rerank) ---")
    print(f"{'Rank':<5}{'Rerank':>7}  {'Source':<32} Preview")
    print("-" * 130)
    for i, d in enumerate(child_sorted[:10], 1):
        src = d["metadata"].get("source_title", "?")[:30]
        preview = d["text"].replace("\n", " ").strip()[:75]
        print(f"{i:<5}{d.get('rerank_score', 0):>7.3f}  {src:<32} {preview}")

    # Ozet karsilastirma
    parent_max = max((d.get("rerank_score") or 0) for d in parent_reranked)
    child_max = max((d.get("rerank_score") or 0) for d in child_reranked)
    parent_above_07 = sum(1 for d in parent_reranked if (d.get("rerank_score") or 0) > 0.7)
    child_above_07 = sum(1 for d in child_reranked if (d.get("rerank_score") or 0) > 0.7)
    parent_above_05 = sum(1 for d in parent_reranked if (d.get("rerank_score") or 0) > 0.5)
    child_above_05 = sum(1 for d in child_reranked if (d.get("rerank_score") or 0) > 0.5)

    print(f"\n--- OZET ---")
    print(f"PARENT rerank: max={parent_max:.3f}, >0.7 chunk={parent_above_07}, >0.5 chunk={parent_above_05}")
    print(f"CHILD  rerank: max={child_max:.3f}, >0.7 chunk={child_above_07}, >0.5 chunk={child_above_05}")
    if child_max < parent_max - 0.1:
        print("  -> CHILD rerank dusuk skor verdi (yuzeysel eslesme elenmis olabilir).")
    elif child_max > parent_max:
        print("  -> CHILD rerank PARENT'tan yuksek skor verdi (beklenmedik).")
    else:
        print("  -> CHILD ve PARENT benzer skor (false-positive child'ta da var).")


def main():
    for case in CASES:
        run_one(case)


if __name__ == "__main__":
    main()
