import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.rag.query_translator import enrich_query
from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search

queries = [
    'hayvanim yere dustu kalkamıyor',
    'ineğimin sütü azaldı ne yapayım',
    'hayvanın karnı şişti geviş getiremiyor',
    'buzağım ishal oluyor',
    'ineğim doğum yaptı plasenta atmadı',
]

for q in queries:
    print(f'--- SORGU: {q}')
    enriched = enrich_query(q)
    if enriched:
        print(f'  ZENGIN ({len(enriched)} karakter): {enriched[:120]}...')
        # Enriched query ile arama
        vec = embed_single(enriched)
        results = search(vec, limit=3, score_threshold=0.2)
        print('  ENRICHED ARAMA SONUCLARI:')
        for r in results:
            src = r['metadata'].get('source_title', '?')[:25]
            lang = r['metadata'].get('language', '?')
            text = r['text'][:80].replace('\n', ' ').strip()
            print(f'    {r["score"]:.3f} [{lang}] {src} | {text}')
    else:
        print('  ZENGIN: None (enrichment basarisiz)')
    print()
