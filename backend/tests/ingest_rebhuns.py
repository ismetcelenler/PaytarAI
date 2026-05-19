"""Buyuk Rebhuns PDF'ini parcalara bolup Qdrant'a ekle (Mevcut veriyi silmeden)."""
import sys, os, math
sys.stdout.reconfigure(encoding='utf-8')

from pypdf import PdfReader, PdfWriter
from app.rag.pipeline import ingest_pdf

SOURCE_PDF = "data/documents/RebhunsDiseasesDairyCattle.pdf"
SOURCE_TITLE = "Rebhun's Diseases of Dairy Cattle"
CHUNK_SIZE = 5  # Sayfa/parca sayisi 5'e dusuruldu (std::bad_alloc onlemek icin)
TEMP_DIR = "data/documents/_temp_parts_rebhuns"

# 1. Temp klasor olustur
os.makedirs(TEMP_DIR, exist_ok=True)

# 2. PDF'i parcala
reader = PdfReader(SOURCE_PDF)
total_pages = len(reader.pages)
num_parts = math.ceil(total_pages / CHUNK_SIZE)

print(f"PDF: {total_pages} sayfa, {num_parts} parcaya bolunecek ({CHUNK_SIZE} sayfa/parca)\n")

part_files = []
for i in range(num_parts):
    start = i * CHUNK_SIZE
    end = min((i + 1) * CHUNK_SIZE, total_pages)
    
    writer = PdfWriter()
    for page_num in range(start, end):
        writer.add_page(reader.pages[page_num])
    
    part_path = os.path.join(TEMP_DIR, f"rebhuns_part{i+1}_{start+1}-{end}.pdf")
    with open(part_path, "wb") as f:
        writer.write(f)
    
    part_files.append((part_path, start+1, end))
    # print(f"  Parca {i+1}: sayfa {start+1}-{end} -> {part_path}")

# 3. Her parcayi yukle
print(f"\n{'='*60}")
total_chunks = 0

for idx, (part_path, start, end) in enumerate(part_files):
    print(f"\n[{idx+1}/{num_parts}] Sayfa {start}-{end} yukleniyor...")
    try:
        result = ingest_pdf(
            pdf_path=part_path,
            source_title=SOURCE_TITLE,
            use_semantic=False,
            use_parent_child=True  # 50 kelimelik cocuklar + parent baglami
        )
        total_chunks += result.get('chunks_inserted', 0)
        print(f"  -> {result.get('chunks_inserted', 0)} chunk eklendi")
    except Exception as e:
        print(f"  HATA: {part_path} yuklenirken sorun olustu: {e}")

print(f"\n{'='*60}")
print(f"TAMAMLANDI: Toplam {total_chunks} chunk eklendi ({SOURCE_TITLE})")
