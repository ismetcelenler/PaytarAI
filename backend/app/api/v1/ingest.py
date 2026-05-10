"""
PaytarAI — Document Ingestion Endpoint

Veteriner PDF dokümanlarını Docling ile parse edip Qdrant'a yükler.
"""

from fastapi import APIRouter, UploadFile, File

router = APIRouter(tags=["Ingestion"])


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    source_trust_level: int = 5,
):
    """
    PDF dokümanı yükle ve RAG pipeline'dan geçir.

    1. Docling ile parse (TableFormer aktif)
    2. Semantic chunking
    3. Parse validation
    4. Embedding üretimi
    5. Qdrant'a upsert

    TODO (Faz 2): Tam RAG pipeline entegrasyonu
    """
    return {
        "status": "placeholder",
        "message": "Doküman ingestion Faz 2'de aktif olacak",
        "filename": file.filename,
        "source_trust_level": source_trust_level,
    }
