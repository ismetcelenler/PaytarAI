"""
PaytarAI — Migration script: BGE-M3 reindex

Eski text-embedding-3-small (1536-dim) koleksiyonu (paytar_veterinary) DOKUNULMADAN
yenisini olusturur: paytar_veterinary_bge (1024-dim BGE-M3).

Adimlar:
1. Yeni collection olustur (paytar_veterinary_bge, 1024 dim, COSINE)
2. backend/data/documents/ icindeki tum PDF'leri parent-child chunking ile reindex et
3. Sonuc istatistiklerini yaz

Kullanim (backend/ dizininden):
    python scripts/migrate_to_bge_m3.py

GPU'da ~30 dk, CPU'da ~6 saat surer.
"""

import sys
import time
from pathlib import Path

# backend/ sys.path'e ekle
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.rag.pipeline import ingest_pdf
from app.rag.qdrant_store import get_qdrant_client, get_collection_info, ensure_collection
from app.rag.embeddings import EMBEDDING_DIMENSION, EMBEDDING_MODEL


def main() -> int:
    print("=" * 70)
    print("PaytarAI Phase 1 — BGE-M3 Migration")
    print("=" * 70)
    print(f"Hedef koleksiyon: {settings.qdrant_collection_name}")
    print(f"Embedding model : {EMBEDDING_MODEL}")
    print(f"Boyut           : {EMBEDDING_DIMENSION}")
    print()

    # 1. Yeni collection (eskiye dokunmaz)
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]
    print(f"Mevcut koleksiyonlar: {existing}")

    if settings.qdrant_collection_name in existing:
        info = get_collection_info()
        print(f"\n[!] '{settings.qdrant_collection_name}' zaten var ({info['points_count']} point).")
        print("    Devam edersek YENIDEN DOLDURULACAK (mevcut data silinmez ama uzerine yazilir).")
        resp = input("Devam? (yes/no): ").strip().lower()
        if resp != "yes":
            print("Iptal edildi.")
            return 1
    else:
        ensure_collection()

    # 2. PDF'leri reindex et
    docs_dir = BACKEND_DIR / "data" / "documents"
    pdfs = sorted(docs_dir.glob("*.pdf"))
    if not pdfs:
        print(f"[HATA] {docs_dir} icinde PDF yok")
        return 1

    print(f"\n{len(pdfs)} PDF islenecek:")
    for p in pdfs:
        size_mb = p.stat().st_size / 1e6
        print(f"  - {p.name} ({size_mb:.1f} MB)")
    print()

    total_chunks = 0
    start = time.time()

    for pdf in pdfs:
        t0 = time.time()
        try:
            result = ingest_pdf(
                pdf_path=pdf,
                source_title=pdf.stem,
                use_semantic=False,
                use_parent_child=True,
            )
            elapsed = time.time() - t0
            total_chunks += result["chunks"]
            print(f"[OK] {pdf.name} — {result['chunks']} chunk, {elapsed:.0f}s")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[HATA] {pdf.name}: {e}")
            return 1

    total_elapsed = time.time() - start
    print()
    print("=" * 70)
    print(f"TAMAMLANDI: {total_chunks} chunk, {total_elapsed/60:.1f} dakika")
    print("=" * 70)

    info = get_collection_info()
    print(f"Yeni koleksiyon durumu: {info}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
