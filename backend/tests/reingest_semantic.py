"""Qdrant koleksiyonunu sil ve semantic chunking ile yeniden yukle."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from qdrant_client import QdrantClient
from app.config import settings
from app.rag.pipeline import ingest_pdf

# 1. Mevcut koleksiyonu sil
print("Mevcut koleksiyon siliniyor...")
client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
client.delete_collection("paytar_veterinary")
print("  Silindi.")

# 2. Semantic chunking ile yeniden yukle
print("\nSemantic chunking ile yeniden yukleniyor...\n")
result = ingest_pdf(
    pdf_path="data/documents/RebhunsDiseasesDairyCattle_chapter15.pdf",
    source_title="Rebhuns Diseases of Dairy Cattle - Chapter 15 Metabolic Diseases",
    use_semantic=True,
)

print(f"\nSonuc: {result['chunks']} chunk, {result['upserted']} upserted")
