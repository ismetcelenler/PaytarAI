"""PyMuPDF ile PDF'i oku ve Qdrant'a yukle (Docling olmadan)."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import fitz  # PyMuPDF
from app.rag.chunking import parent_child_chunk
from app.rag.embeddings import embed_texts
from app.rag.qdrant_store import ensure_collection, upsert_chunks, get_qdrant_client
from app.config import settings

PDF_PATH = "data/documents/Amasya_DSYB_kaynak.pdf"
SOURCE_TITLE = "Amasya DSYB - Sigir Hastaliklari Kilavuzu"

print(f"[{SOURCE_TITLE}] PyMuPDF ile okunuyor...")

# 1. Metni cikar
doc = fitz.open(PDF_PATH)
full_text = ""
for page in doc:
    full_text += page.get_text() + "\n\n"

print(f"Toplam {len(doc)} sayfa okundu, metin uzunlugu: {len(full_text)} karakter.")

# 2. Parent-Child Chunking
print("Parent-Child chunking yapiliyor...")
pc_results = parent_child_chunk(
    full_text,
    parent_words=400,
    parent_overlap=50,
    child_words=50,
    child_overlap=10
)
print(f"Olusturulan Cocuk (Child) chunk sayisi: {len(pc_results)}")

# Cocuk metinleri embedding'e gonderecegiz
child_chunks = [item["child_text"] for item in pc_results]

# 3. Embedding
print("Embedding'ler uretiliyor...")
embeddings = embed_texts(child_chunks)

# 4. Metadata
metadata_list = [
    {
        "source_title": SOURCE_TITLE,
        "source_file": "Amasya_DSYB_kaynak.pdf",
        "total_pages": len(doc),
        "chunk_total": len(pc_results),
        "language": "tr",
        "parent_text": item["parent_text"],  # Ebeveyn metni payload'da saklaniyor
    }
    for item in pc_results
]

# 5. Qdrant
print("Qdrant koleksiyonu temizleniyor...")
client = get_qdrant_client()
try:
    client.delete_collection(settings.qdrant_collection_name)
    print("Eski koleksiyon basariyla silindi.")
except Exception as e:
    print(f"Silme hatasi (ilk calistirma olabilir): {e}")

print("Qdrant'a yukleniyor...")
collection_name = ensure_collection()
upserted = upsert_chunks(child_chunks, embeddings, metadata_list, collection_name)

print(f"ISLEM TAMAM: {upserted} child chunk basariyla veritabanina eklendi.")
