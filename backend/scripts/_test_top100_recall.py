"""
Top-100 recall testi: producer_02, vet_03, vet_09 icin dense top-100 alip rerank yap.

Hipotez: Gercek altin chunk top-30'a girmiyor olabilir (recall problemi).
Test: top-100 icinde rerank > 0.7 olan chunk var mi?
- Varsa: top-N artirmali
- Yoksa: kaynakta yok, ya da embed kotu
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
from app.rag.reranker import rerank
from app.rag.query_translator import enrich_query


CASES = [
    {
        "id": "producer_02",
        "query": "dogumdan 3 gun gecti sutum dusuk hayvan da halsiz gozukuyor normal mi",
        "topic": "Dogum sonrasi inek halsizlik/sut dususu -> muhtemelen milk fever, ketozis, metritis",
    },
    {
        "id": "vet_03",
        "query": "Akut puerperal metritis ile kronik endometritis ayırıcı tanı kriterleri nelerdir, tedavi nasıl farklılaşıyor?",
        "topic": "Metritis vs endometritis ayirici tani",
    },
    {
        "id": "vet_09",
        "query": "Mortellaro hastalığı kronik vakada uzun dönem prognoz nasıl? Sürü düzeyinde kontrol protokolü önerisi var mı?",
        "topic": "Mortellaro / dijital dermatit kronik prognoz",

    },
]


def run_one(case: dict, top_n: int = 100):
    print(f"\n{'='*80}")
    print(f"CASE: {case['id']}")
    print(f"Topic: {case['topic']}")
    print(f"Query: {case['query']}")
    print(f"{'='*80}\n")

    # Dense (orjinal + enriched)
    vec_orig = embed_single(case["query"])
    enriched = enrich_query(case["query"])
    print(f"[Enrich] {enriched[:100] if enriched else '(none)'}\n")

    results_orig = search(query_vector=vec_orig, limit=top_n, score_threshold=0.25)

    if enriched:
        vec_en = embed_single(enriched)
        results_en = search(query_vector=vec_en, limit=top_n, score_threshold=0.25)
    else:
        results_en = []

    # Birlestir (dedup by first 100 chars)
    seen = set()
    candidates = []
    for r in results_orig + results_en:
        key = r["text"][:100]
        if key not in seen:
            seen.add(key)
            candidates.append(r)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    candidates = candidates[:top_n]

    # Rerank
    rerank_query = f"{case['query']} | {enriched}" if enriched else case["query"]
    reranked = rerank(rerank_query, candidates, top_k=top_n)

    # Rerank skoruna gore sirala (yuksek -> dusuk)
    reranked.sort(key=lambda x: x.get("rerank_score") or 0, reverse=True)

    # Top-10 goster
    print(f"Toplam {len(reranked)} chunk rerank edildi. Rerank skoruna gore TOP-10:\n")
    print(f"{'Rank':<5}{'Dense':>7}{'Rerank':>8}  {'Source':<35} Preview")
    print(f"{'-'*120}")
    for i, r in enumerate(reranked[:10], 1):
        src = r["metadata"].get("source_title", "?")[:33]
        preview = (r["text"] or "").replace("\n", " ").strip()[:80]
        print(f"{i:<5}{r['score']:>7.3f}{r.get('rerank_score', 0):>8.3f}  {src:<35} {preview}")

    # Top-30'dan SONRA rerank > 0.7 olan chunk var mi?
    print()
    high_score_after_30 = [
        (i, r) for i, r in enumerate(reranked)
        if i >= 30 and (r.get("rerank_score") or 0) > 0.7
    ]
    if high_score_after_30:
        print(f"*** {len(high_score_after_30)} adet rerank>0.7 chunk top-30 SONRASINDA bulundu (kacirilmis):")
        for idx, r in high_score_after_30[:5]:
            src = r["metadata"].get("source_title", "?")[:33]
            preview = (r["text"] or "").replace("\n", " ").strip()[:100]
            print(f"  pos={idx+1}  rerank={r.get('rerank_score', 0):.3f}  {src}: {preview}")
    else:
        print("*** Top-30 SONRASINDA rerank>0.7 olan chunk YOK. Top-N artirmak fayda etmez.")

    # En yuksek rerank skoru ne?
    top_rerank = reranked[0].get("rerank_score") or 0
    print(f"\n*** En yuksek rerank skoru: {top_rerank:.3f}")
    if top_rerank < 0.7:
        print("    -> Hicbir chunk gercekten alakali degil. Kaynakta cevap yok veya embed kotu.")
    elif top_rerank > 0.9:
        print("    -> Cok yuksek skor, gercek cevap var.")


def main():
    for case in CASES:
        run_one(case, top_n=100)


if __name__ == "__main__":
    main()
