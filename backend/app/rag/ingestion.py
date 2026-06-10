"""
PaytarAI — Docling PDF Ingestion Pipeline

Docling + TableFormer ile veteriner PDF dokumanlari parse edilir.
AI-PROMPT.md Section 3.1 ve 3.2'ye uygun.
"""

import os
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat


# Docling converter singleton — model yukleme bir kez yapilir
_converter: DocumentConverter | None = None


def get_converter() -> DocumentConverter:
    """Docling converter instance'ini dondurur (lazy singleton)."""
    global _converter
    if _converter is None:
        pipeline_options = PdfPipelineOptions(do_table_structure=True)
        pipeline_options.do_ocr = False  # OOM/std::bad_alloc onlemek icin OCR kapali
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        _converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _converter


def parse_pdf(pdf_path: str | Path) -> dict:
    """
    PDF dosyasini Docling ile parse eder.

    Args:
        pdf_path: PDF dosya yolu

    Returns:
        dict: {
            "name": dosya adi,
            "markdown": tam metin (Markdown),
            "pages": sayfa sayisi,
            "tables": tablo sayisi,
            "char_count": karakter sayisi,
        }
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF bulunamadi: {pdf_path}")

    converter = get_converter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    markdown = doc.export_to_markdown()

    return {
        "name": doc.name or pdf_path.stem,
        "markdown": markdown,
        "pages": len(doc.pages),
        "tables": len(doc.tables),
        "char_count": len(markdown),
    }


def parse_pdf_pymupdf(pdf_path: str | Path) -> dict:
    """
    PDF dosyasini PyMuPDF (fitz) ile parse eder.

    Docling Turkce karakterleri kelimeden ayiriyor (ı, ş, ğ → "Is ı" bug'i).
    Turkce kaynaklar icin PyMuPDF kullanilir; Docling EN kaynaklarda kalir.

    Tablo yapisi korunmaz (PyMuPDF duz metin verir) ama Turkce metin saglam.

    Args:
        pdf_path: PDF dosya yolu

    Returns:
        dict (parse_pdf ile ayni sema): name, markdown, pages, tables, char_count
    """
    import fitz  # PyMuPDF

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF bulunamadi: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    pages_text = []
    for i in range(len(doc)):
        page_text = doc[i].get_text()
        pages_text.append(page_text)
    page_count = len(doc)
    doc.close()

    # Markdown gibi sayfalar arasinda \n\n koy (chunking icin paragraf isareti)
    markdown = "\n\n".join(pages_text)

    return {
        "name": pdf_path.stem,
        "markdown": markdown,
        "pages": page_count,
        "tables": 0,  # PyMuPDF tablo yapisi tutmaz
        "char_count": len(markdown),
    }


def parse_all_documents(documents_dir: str = "data/documents") -> list[dict]:
    """
    Belirtilen klasordeki tum PDF'leri parse eder.

    Args:
        documents_dir: PDF klasor yolu

    Returns:
        list[dict]: Her PDF icin parse sonucu
    """
    doc_path = Path(documents_dir)
    if not doc_path.exists():
        raise FileNotFoundError(f"Dokuman klasoru bulunamadi: {doc_path}")

    pdfs = list(doc_path.glob("*.pdf"))
    if not pdfs:
        raise ValueError(f"Klasorde PDF bulunamadi: {doc_path}")

    results = []
    for pdf in pdfs:
        print(f"[Ingestion] Parse ediliyor: {pdf.name}")
        parsed = parse_pdf(pdf)
        print(f"  -> {parsed['pages']} sayfa, {parsed['char_count']} karakter, {parsed['tables']} tablo")
        results.append(parsed)

    return results
