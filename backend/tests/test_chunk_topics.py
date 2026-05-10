"""Semantic chunk icerikleri — anlamsal tutarlilik kontrolu."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from qdrant_client import QdrantClient
from app.config import settings

client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

results = client.scroll(
    collection_name="paytar_veterinary",
    limit=100,
    with_payload=True,
    with_vectors=False,
)

chunks = results[0]
print(f"Toplam: {len(chunks)} chunk\n")

for i, point in enumerate(chunks):
    text = point.payload.get("text", "")
    words = len(text.split())
    
    # Baslik tespiti
    lines = text.strip().split("\n")
    headings = [l.strip() for l in lines if l.strip().startswith("##")]
    heading_str = " | ".join(headings[:3]) if headings else "(baslik yok)"
    
    # Ilk cumle
    first_sentence = lines[0].strip()[:100] if lines else ""
    
    print(f"[{i+1:2d}] {words:4d} kel | Baslik: {heading_str}")
    print(f"     Ilk: {first_sentence}")
    print()
