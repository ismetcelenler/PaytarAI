"""Rebhun's kitabindan Qdrant'a eklenen chunklarin kalitesini kontrol eder."""
import sys
import random
sys.stdout.reconfigure(encoding='utf-8')

from qdrant_client import QdrantClient
from app.config import settings

client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

print("Rebhun's kitabindan rastgele 5 chunk getiriliyor...\n")

# Scroll over points
points = []
next_page_offset = None
while True:
    records, next_page_offset = client.scroll(
        collection_name=settings.qdrant_collection_name,
        limit=5000,
        with_payload=True,
        with_vectors=False,
        offset=next_page_offset
    )
    points.extend(records)
    if next_page_offset is None:
        break

rebhuns_chunks = [p for p in points if "Rebhun's" in str(p.payload.get("source_title", ""))]

if not rebhuns_chunks:
    print("Rebhun's kitabina ait chunk bulunamadi.")
    sys.exit(0)

# Randomly select 5 chunks
sample_chunks = random.sample(rebhuns_chunks, min(5, len(rebhuns_chunks)))

for i, point in enumerate(sample_chunks, 1):
    child_text = point.payload.get('text', '')
    parent_text = point.payload.get('parent_text', 'Parent Yok')
    page = point.payload.get('page', 'Unknown')
    
    print(f"--- CHUNK {i} (Sayfa: {page}) ---")
    print(f"[ÇOCUK (Vektöre Gömülen)] Kelime Sayisi: {len(child_text.split())}")
    print(child_text)
    print(f"\n[EBEVEYN (LLM'e Gidecek)] Kelime Sayisi: {len(parent_text.split())}")
    print(parent_text)
    print("-" * 80)

print(f"\nToplam Rebhun's chunk sayisi: {len(rebhuns_chunks)}")
