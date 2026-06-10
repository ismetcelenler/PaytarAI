"""
PaytarAI — RAG Pipeline Orchestrator

PDF parse -> Chunk -> Embed -> Qdrant upsert
Tam pipeline'i tek cagriyla calistirir.
"""

from pathlib import Path

from app.rag.ingestion import parse_pdf, parse_pdf_pymupdf, parse_all_documents
from app.rag.chunking import semantic_chunk, simple_chunk, parent_child_chunk
from app.rag.embeddings import embed_texts
from app.rag.qdrant_store import ensure_collection, upsert_chunks, get_collection_info
from app.rag.query_translator import detect_language


def ingest_pdf(
    pdf_path: str | Path,
    source_title: str | None = None,
    use_semantic: bool = True,
    use_parent_child: bool = False,
    parser: str = "docling",
) -> dict:
    """
    Tek bir PDF'i parse edip Qdrant'a yukler.

    Args:
        pdf_path: PDF dosya yolu
        source_title: Kaynak adi (None ise dosya adindan alinir)
        use_semantic: True ise semantic chunking, False ise simple chunking
        parser: "docling" (default, EN icin) veya "pymupdf" (TR icin, Docling
                Turkce karakterleri kelimeden ayiriyor bug'i)

    Returns:
        Islem sonucu istatistikleri
    """
    pdf_path = Path(pdf_path)

    # 1. Parse
    print(f"\n{'='*60}")
    print(f"[Pipeline] PDF parse ediliyor: {pdf_path.name} (parser={parser})")
    print(f"{'='*60}")
    if parser == "pymupdf":
        parsed = parse_pdf_pymupdf(pdf_path)
    elif parser == "docling":
        parsed = parse_pdf(pdf_path)
    else:
        raise ValueError(f"Bilinmeyen parser: {parser}. Kullan: 'docling' veya 'pymupdf'")
    print(f"  Sayfa: {parsed['pages']}, Karakter: {parsed['char_count']}, Tablo: {parsed['tables']}")

    # 2. Metin temizleme (gorsel placeholder, fazla bosluk vs.)
    raw_text = parsed["markdown"]
    cleaned_text = _clean_parsed_text(raw_text)
    removed = len(raw_text) - len(cleaned_text)
    print(f"\n[Pipeline] Metin temizlendi ({removed} karakter cikarildi)")

    # 3. Chunk
    print(f"\n[Pipeline] Chunking basladi (mod: {'parent-child' if use_parent_child else ('semantic' if use_semantic else 'simple')})...")
    pc_chunks = []
    if use_parent_child:
        pc_chunks = parent_child_chunk(
            text=cleaned_text,
            parent_words=400,
            parent_overlap=50,
            child_words=50,
            child_overlap=10
        )
        chunks = [item["child_text"] for item in pc_chunks]
    elif use_semantic:
        chunks = semantic_chunk(
            text=cleaned_text,
            embed_fn=embed_texts,
            min_chunk_tokens=300,
            max_chunk_tokens=2500,
        )
    else:
        chunks = simple_chunk(
            text=cleaned_text,
            target_tokens=1500,
            overlap_tokens=200,
        )
    print(f"  {len(chunks)} chunk olusturuldu")

    # Chunk istatistikleri
    chunk_sizes = [len(c.split()) for c in chunks]
    avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
    print(f"  Ortalama chunk boyutu: {avg_size:.0f} kelime")
    print(f"  Min: {min(chunk_sizes) if chunk_sizes else 0}, Max: {max(chunk_sizes) if chunk_sizes else 0}")

    # 3. Embed
    print(f"\n[Pipeline] Embedding olusturuluyor ({len(chunks)} chunk)...")
    embeddings = embed_texts(chunks)
    print(f"  {len(embeddings)} embedding olusturuldu")

    # 4. Metadata (dil tespiti dahil)
    title = source_title or parsed["name"]
    doc_lang = detect_language(chunks[0] if chunks else "")
    metadata_list = []
    for i, _ in enumerate(chunks):
        meta = {
            "source_title": title,
            "source_file": pdf_path.name,
            "total_pages": parsed["pages"],
            "chunk_total": len(chunks),
            "language": doc_lang,
        }
        if use_parent_child and pc_chunks:
            meta["parent_text"] = pc_chunks[i]["parent_text"]
        metadata_list.append(meta)

    # 5. Qdrant upsert
    print(f"\n[Pipeline] Qdrant'a yukleniyor...")
    collection_name = ensure_collection()
    count = upsert_chunks(chunks, embeddings, metadata_list, collection_name)

    # 6. Sonuc
    info = get_collection_info(collection_name)
    result = {
        "source": title,
        "file": pdf_path.name,
        "pages": parsed["pages"],
        "tables": parsed["tables"],
        "chunks": len(chunks),
        "avg_chunk_words": round(avg_size),
        "embeddings": len(embeddings),
        "upserted": count,
        "collection": info,
    }

    print(f"\n{'='*60}")
    print(f"[Pipeline] TAMAMLANDI: {title}")
    print(f"  {count} chunk -> {collection_name} ({info['points_count']} toplam)")
    print(f"{'='*60}\n")

    return result


def ingest_all(
    documents_dir: str = "data/documents",
    use_semantic: bool = True,
) -> list[dict]:
    """Klasordeki tum PDF'leri isle."""
    doc_path = Path(documents_dir)
    pdfs = list(doc_path.glob("*.pdf"))

    results = []
    for pdf in pdfs:
        result = ingest_pdf(pdf, use_semantic=use_semantic)
        results.append(result)

    return results


def _clean_parsed_text(text: str) -> str:
    """
    Docling ciktisini temizler:
    - <!-- image --> taglarini kaldirir
    - Fazla bos satirlari (3+) 2'ye dusurur
    - Bos markdown linklerini temizler
    """
    import re

    # Gorsel placeholder'lari kaldir
    text = text.replace("<!-- image -->", "")

    # Bos markdown linklerini kaldir: [](...)
    text = re.sub(r'\[]\([^)]*\)', '', text)

    # 3+ ust uste bos satiri 2'ye dusur
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Satir basi/sonu gereksiz bosluklar
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()
