"""Arama kalitesi testi."""
from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search

queries = [
    "milk fever hypocalcemia treatment calcium borogluconate",
    "fatty liver hepatic lipidosis fresh cow",
    "displaced abomasum surgery left side",
    "hypomagnesemia grass tetany magnesium",
    "downer cow syndrome treatment prognosis",
    "ketosis propylene glycol dosage",
]

for q in queries:
    vec = embed_single(q)
    results = search(vec, limit=2, score_threshold=0.3)
    print("SORGU:", q)
    for r in results:
        snippet = r["text"][:180].replace("\n", " ")
        print(f"  Skor: {r['score']:.4f} | {snippet}")
    print()
