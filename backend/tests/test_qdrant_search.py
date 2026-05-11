from app.rag.embeddings import embed_single
from app.rag.qdrant_store import search
import pprint

# Search for "ketozis"
query = "öksüren hayvana ne yapılır"
vector = embed_single(query)
results = search(vector, limit=5, score_threshold=0.1)

with open("tests/qdrant_output.txt", "w", encoding="utf-8") as f:
    f.write(f"\n--- Searching for: '{query}' ---\n")
    for i, r in enumerate(results):
        f.write(f"\nResult {i+1} - Score: {r['score']}\n")
        f.write(f"Snippet: {r['text'][:500]}\n")
        f.write("-" * 50 + "\n")
