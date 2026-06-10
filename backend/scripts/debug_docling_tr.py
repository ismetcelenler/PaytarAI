"""
Docling'in Turkce karakter bozma sebebini izole et.

3 farkli config dene:
  1. Docling default (hicbir option yok)
  2. Docling do_table_structure=False (tablo islemeyi kapat)
  3. Docling TableFormerMode.FAST (accurate yerine fast)
  4. Bonus: result.document.export_to_text() (markdown yerine plain)

Her config icin Sayfa 51'in ilk 800 char'ini yazdir + Turkce kalite kontrol.
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PDF = BACKEND_DIR / "data" / "sources" / "tr" / "tr03_buyukbas_hayvan_yetistiriciligi.pdf"


def check_quality(text: str) -> dict:
    """Bozuk Turkce pattern'lerini ara."""
    bad_patterns = [" ğ ", " ş ", " ı ", " ü ", " ö ", " ç "]
    bad_count = sum(text.count(p) for p in bad_patterns)
    good_words = ["gelişme", "olmasının", "yağışlı", "elverişli", "topraktaki", "şartları"]
    good_count = sum(1 for w in good_words if w in text)
    return {"bad_separator_count": bad_count, "good_word_found": good_count}


def extract_page(markdown: str, target_page: int = 50) -> str:
    """Markdown'dan Sayfa X civarini yaklasik al."""
    # Basit: tum text uzunlugunu bol, target_page'e karsilik gelen kismi al
    parts = markdown.split("\n\n")
    if len(parts) > target_page:
        # Sayfa 50 civari icerik
        return "\n\n".join(parts[max(0, target_page-2):target_page+3])
    return markdown[5000:7000]  # fallback


def test_config(name: str, parse_fn):
    print(f"\n{'='*70}\nCONFIG: {name}\n{'='*70}")
    try:
        text = parse_fn()
        excerpt = extract_page(text, 50)[:800]
        print(f"--- Excerpt (ilk 800 char) ---")
        # Console-safe print
        print(excerpt.encode("utf-8", "replace").decode("utf-8", "replace"))
        q = check_quality(excerpt)
        print(f"\n--- Kalite ---")
        print(f"  Bozuk separator pattern sayisi: {q['bad_separator_count']}")
        print(f"  Dogru Turkce kelime bulundu: {q['good_word_found']}/6")
    except Exception as e:
        print(f"HATA: {e}")


# CONFIG 1: PyMuPDF baseline (reference)
def cfg_pymupdf():
    import fitz
    doc = fitz.open(str(PDF))
    out = []
    for i in range(min(70, len(doc))):
        out.append(doc[i].get_text())
    doc.close()
    return "\n\n".join(out)


# CONFIG 2: Docling default (do_table_structure=False, ocr=False)
def cfg_docling_minimal():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    opts = PdfPipelineOptions(do_table_structure=False, do_ocr=False)
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    result = conv.convert(str(PDF))
    return result.document.export_to_markdown()


# CONFIG 3: Docling TableFormer ACCURATE (mevcut prod config)
def cfg_docling_accurate():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.datamodel.base_models import InputFormat
    opts = PdfPipelineOptions(do_table_structure=True, do_ocr=False)
    opts.table_structure_options.mode = TableFormerMode.ACCURATE
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    result = conv.convert(str(PDF))
    return result.document.export_to_markdown()


# CONFIG 4: Docling TableFormer FAST
def cfg_docling_fast():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.datamodel.base_models import InputFormat
    opts = PdfPipelineOptions(do_table_structure=True, do_ocr=False)
    opts.table_structure_options.mode = TableFormerMode.FAST
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    result = conv.convert(str(PDF))
    return result.document.export_to_markdown()


# CONFIG 5: Docling export_to_text() yerine markdown
def cfg_docling_minimal_text():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    opts = PdfPipelineOptions(do_table_structure=False, do_ocr=False)
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    result = conv.convert(str(PDF))
    # Try export_to_text if exists, else fall back
    if hasattr(result.document, "export_to_text"):
        return result.document.export_to_text()
    return result.document.export_to_markdown()


if __name__ == "__main__":
    test_config("1. PyMuPDF (reference)", cfg_pymupdf)
    test_config("2. Docling DEFAULT (no table, no OCR)", cfg_docling_minimal)
    test_config("3. Docling TableFormer ACCURATE (mevcut prod)", cfg_docling_accurate)
    test_config("4. Docling TableFormer FAST", cfg_docling_fast)
    test_config("5. Docling MINIMAL + export_to_text", cfg_docling_minimal_text)
