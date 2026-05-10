"""Dual query skor karsilastirmasi."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
from app.rag.query_translator import translate_query, detect_language

query_tr = "500kg simental duveye ketosis icin hangi ilaci yapmaliyim"
print(f"TR sorgu: {query_tr}")
print(f"Dil: {detect_language(query_tr)}")

# Turkce ile ara
vec_tr = embed_single(query_tr)
results_tr = search(vec_tr, limit=3, score_threshold=0.3)
print(f"\nTR ile arama — top skor: {results_tr[0]['score']:.4f}" if results_tr else "\nTR: sonuc yok")

# Ingilizceye cevir
query_en = translate_query(query_tr, "English")
print(f"\nEN ceviri: {query_en}")

# Ingilizce ile ara
if query_en:
    vec_en = embed_single(query_en)
    results_en = search(vec_en, limit=3, score_threshold=0.3)
    print(f"EN ile arama — top skor: {results_en[0]['score']:.4f}" if results_en else "EN: sonuc yok")
    
    print(f"\nSKOR FARKI: {results_en[0]['score'] - results_tr[0]['score']:.4f} (EN daha yuksek)")
