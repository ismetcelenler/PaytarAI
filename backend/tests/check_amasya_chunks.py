"""Amasya PDF'inden Qdrant'a eklenen chunklarin kalitesini kontrol eder."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client import QdrantClient
from app.config import settings

client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

print("Amasya DSYB kilavuzundan rastgele 3 chunk getiriliyor...\n")

# Qdrant'tan son eklenenleri alip python icinde filtreleyecegiz
results, _ = client.scroll(
    collection_name=settings.qdrant_collection_name,
    limit=2000,  # 1500+ chunk oldugu icin limiti artirdik
    with_payload=True,
    with_vectors=False
)

amasya_chunks = [p for p in results if p.payload.get("source_title") == "Amasya DSYB - Sigir Hastaliklari Kilavuzu"]

for i, point in enumerate(amasya_chunks[:3], 1):
    child_text = point.payload.get('text', '')
    parent_text = point.payload.get('parent_text', 'Parent Yok')
    
    print(f"--- CHUNK {i} ---")
    print(f"[ÇOCUK (Vektöre Gömülen)] Kelime Sayisi: {len(child_text.split())}")
    print(f"{child_text[:200]}...")
    print(f"\n[EBEVEYN (LLM'e Gidecek)] Kelime Sayisi: {len(parent_text.split())}")
    print(f"{parent_text[:300]}...\n")
    print("-" * 50)

print(f"\nToplam Amasya chunk sayisi: {len(amasya_chunks)}")
