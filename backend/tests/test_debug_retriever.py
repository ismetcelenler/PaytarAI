"""Dual query retriever debug."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
from app.rag.query_translator import translate_query, detect_language

query = "sut hummasi tedavisi nasil yapilir"
print(f"Sorgu: {query}")
print(f"Dil: {detect_language(query)}")

# 1. Turkce arama
vec_tr = embed_single(query)
results_tr = search(vec_tr, limit=3, score_threshold=0.35)
print(f"\nTR arama: {len(results_tr)} sonuc")
for r in results_tr:
    print(f"  Skor: {r['score']:.4f}")

# 2. Ceviri
try:
    translated = translate_query(query, "English")
    print(f"\nEN ceviri: {translated}")
    
    if translated:
        vec_en = embed_single(translated)
        results_en = search(vec_en, limit=3, score_threshold=0.35)
        print(f"EN arama: {len(results_en)} sonuc")
        for r in results_en:
            print(f"  Skor: {r['score']:.4f}")
except Exception as e:
    print(f"\nCeviri HATASI: {e}")
