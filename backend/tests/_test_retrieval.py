import sys
sys.stdout.reconfigure(encoding='utf-8')
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
    vec = embed_single(q)
    results = search(vec, limit=3, score_threshold=0.2)
    print(f'SORGU: {q}')
    if results:
        for r in results:
            src = r['metadata'].get('source_title', '?')[:30]
            lang = r['metadata'].get('language', '?')
            text = r['text'][:100].replace('\n', ' ').strip()
            print(f'  {r["score"]:.3f} [{lang}] {src} | {text}')
    else:
        print('  Sonuc yok')
    print()
