"""Producer_02 retrieval'i incele — parent mi child mi geliyor."""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search

q = "dogumdan 3 gun gecti sutum dusuk hayvan da halsiz gozukuyor normal mi"
print(f"QUERY: {q}\n")
vec = embed_single(q)
results = search(query_vector=vec, limit=3, score_threshold=0.25)

for i, r in enumerate(results, 1):
    print(f"=== Chunk {i} ===")
    print(f"Score: {r['score']:.4f}")
    print(f"Source: {r['metadata'].get('source_title', '?')}")
    print(f"Text length: {len(r['text'])} char")
    print(f"Preview (first 300): {r['text'][:300]!r}")
    print()
