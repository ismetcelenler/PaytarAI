"""
PaytarAI — Document Ingestion Endpoint

Veteriner PDF dokumanlarini Docling ile parse edip Qdrant'a yukler.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Query, HTTPException

from app.rag.pipeline import ingest_pdf, ingest_all
from app.rag.qdrant_store import get_collection_info, ensure_collection

router = APIRouter(tags=["Ingestion"])


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    source_title: str = Query(None, description="Kaynak adi (opsiyonel)"),
    use_semantic: bool = Query(True, description="Semantic chunking kullan"),
):
    """
    PDF dokumani yukle ve RAG pipeline'dan gecir.

    1. Docling ile parse (TableFormer aktif)
    2. Semantic chunking
    3. Embedding uretimi (OpenAI text-embedding-3-small)
    4. Qdrant'a upsert
    """
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyalari kabul edilir")

    # Gecici dosyaya kaydet
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = ingest_pdf(
            pdf_path=tmp_path,
            source_title=source_title or file.filename,
            use_semantic=use_semantic,
        )
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/ingest/all")
async def ingest_all_documents(
    use_semantic: bool = Query(True, description="Semantic chunking kullan"),
):
    """
    backend/data/documents/ klasorundeki tum PDF'leri isle.
    """
    try:
        results = ingest_all(use_semantic=use_semantic)
        return {"status": "ok", "documents": results}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/status")
async def ingestion_status():
    """Qdrant koleksiyon durumunu dondurur."""
    try:
        ensure_collection()
        info = get_collection_info()
        return {"status": "ok", **info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
