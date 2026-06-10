"""
Turkce kaynaklari Qdrant'a ingest et.

Mevcut paytar_veterinary_bge collection'a ekleme yapar (parent-child + Docling).
ASCII dosya adi ile path-safe islem, source_title metadata'da orijinal Turkce.

Kullanim:
  # Tek dosya test:
  python scripts/ingest_tr_sources.py tr01

  # Hepsi:
  python scripts/ingest_tr_sources.py all
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.pipeline import ingest_pdf
from app.rag.qdrant_store import get_collection_info


# Mapping: ASCII dosya adi -> (orijinal Turkce baslik, ASCII baslik, kategori)
# Orijinal Turkce isim retrieval citation icin de kullanilabilir.
SOURCES = {
    "tr01": {
        "file": "tr01_buzagi_sagligi.pdf",
        "title": "Buzagi Sagligi",
        "original_title": "Buzağı Sağlığı",
        "original_file": "buzağı sağlığı.pdf",
        "category": "producer_practical",
    },
    "tr02": {
        "file": "tr02_buyukbas_hastaliklari_el_kitabi.pdf",
        "title": "Buyukbas Hastaliklari El Kitabi",
        "original_title": "Büyükbaş Hastalıkları El Kitabı",
        "original_file": "büyükbaş hastalıkları el kitabı.pdf",
        "category": "vet_practical",
    },
    "tr03": {
        "file": "tr03_buyukbas_hayvan_yetistiriciligi.pdf",
        "title": "Buyukbas Hayvan Yetistiriciligi",
        "original_title": "Büyükbaş Hayvan Yetiştiriciliği",
        "original_file": "Büyükbaş Hayvan Yetiştiriciliği.pdf",
        "category": "producer_practical",
    },
    "tr04": {
        "file": "tr04_sigir_besiciligi_ciftci_egitim_serisi.pdf",
        "title": "Sigir Besiciligi - Ciftci Egitim Serisi",
        "original_title": "Sığır Besiciliği — Çiftçi Eğitim Serisi",
        "original_file": "sığır besiciliği-çiftçi eğitim serisi.pdf",
        "category": "producer_practical",
    },
    "tr05": {
        "file": "tr05_sut_sigirlarinin_bakimi.pdf",
        "title": "Sut Sigirlarinin Bakimi - Aziz Ozturk",
        "original_title": "Süt Sığırlarının Bakımı — Aziz Öztürk",
        "original_file": "süt sığırlarının bakımı - aziz öztürk.pdf",
        "category": "producer_practical",
    },
    "tr06": {
        "file": "tr06_pratik_sigircilik.pdf",
        "title": "Pratik Sigircilik",
        "original_title": "Pratik Sığırcılık",
        "original_file": "pratik sığırcılık.pdf",
        "category": "producer_practical",
    },
    "tr07": {
        "file": "tr_amasya_DSYB.pdf",
        "title": "Amasya DSYB Yayini",
        "original_title": "Amasya DSYB Yayını (014)",
        "original_file": "Amasya_DSYB_Yayin_014.pdf",
        "category": "producer_practical",
    },
}


SOURCES_DIR = BACKEND_DIR / "data" / "sources" / "tr"


def ingest_one(key: str) -> dict:
    if key not in SOURCES:
        raise ValueError(f"Unknown key: {key}. Available: {list(SOURCES.keys())}")

    info = SOURCES[key]
    pdf_path = SOURCES_DIR / info["file"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"\n{'='*70}")
    print(f"INGEST: {key} -- {info['title']}")
    print(f"File:   {info['file']}  ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"{'='*70}")

    t0 = time.time()
    # use_parent_child=True (mevcut Rebhuns ile ayni strateji)
    # parser="pymupdf" — Docling Turkce karakterleri bozuyor (ı, ş, ğ kelimeden ayriliyor)
    result = ingest_pdf(
        pdf_path=pdf_path,
        source_title=info["title"],
        use_semantic=False,
        use_parent_child=True,
        parser="pymupdf",
    )
    dt = time.time() - t0
    result["duration_sec"] = round(dt, 1)
    result["key"] = key
    result["category"] = info["category"]
    return result


def main():
    if len(sys.argv) < 2:
        print("Kullanim: python scripts/ingest_tr_sources.py <key|all>")
        print(f"Available keys: {list(SOURCES.keys())}")
        sys.exit(1)

    arg = sys.argv[1].lower()

    if arg == "all":
        keys = list(SOURCES.keys())
    elif arg in SOURCES:
        keys = [arg]
    else:
        print(f"Bilinmeyen key: {arg}")
        sys.exit(1)

    # Baslangic durumu
    info_before = get_collection_info()
    print(f"\nBaslangic collection durumu: {info_before['points_count']} chunk")

    results = []
    total_chunks = 0
    for key in keys:
        try:
            r = ingest_one(key)
            results.append(r)
            total_chunks += r.get("chunks", 0)
            print(f"\n[OK] {key}: {r.get('chunks', 0)} chunk, {r.get('duration_sec', 0)}s")
        except Exception as e:
            print(f"\n[FAIL] {key}: {e}")
            results.append({"key": key, "error": str(e)})

    # Bitis durumu
    info_after = get_collection_info()
    print(f"\n{'='*70}")
    print("OZET")
    print(f"{'='*70}")
    print(f"Onceki chunk:  {info_before['points_count']}")
    print(f"Yeni chunk:    {info_after['points_count']}")
    print(f"Eklenen:       {info_after['points_count'] - info_before['points_count']}")
    print(f"\nDetay:")
    for r in results:
        if "error" in r:
            print(f"  [FAIL] {r['key']}: {r['error']}")
        else:
            print(f"  [OK] {r['key']}: {r.get('chunks', 0)} chunk, {r.get('duration_sec', 0)}s")


if __name__ == "__main__":
    main()
