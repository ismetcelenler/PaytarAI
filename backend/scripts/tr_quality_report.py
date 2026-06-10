"""
TR kaynak kalite raporu — ingest sonrasi tum chunk'lari analiz et.

Olculen:
  1. Kaynak bazinda chunk sayisi + boyut istatistigi
  2. Turkce karakter dogrulugu (bozuk separator pattern)
  3. Cok kisa chunk (<30 char) yuzdesi
  4. Icindekiler kirliligi (sayfa numarali baslik tablosu)
  5. Bibliyografya kirliligi
  6. Toplam dagılım (TR/EN)
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import re
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from qdrant_client import QdrantClient


# Noise patterns
TOC_PATTERN = re.compile(r"\.{3,}\s*\d+|\.\s*\.\s*\.\s*\d+")  # "... 142" tipi içindekiler
PAGE_NO_PATTERN = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)  # tek satirda sayfa no
BIB_PATTERN = re.compile(r"\b\d{4}\s*\.\s*[A-Z][a-z]+", re.IGNORECASE)  # "2014. Author" tipi atıf
BAD_SEP_PATTERNS = [" ğ ", " ş ", " ı ", " ü ", " ö ", " ç ", " Ğ ", " Ş ", " İ "]


def percentile(values, p):
    s = sorted(values)
    return s[min(int(len(s) * p / 100), len(s) - 1)]


def analyze():
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=60)
    total = client.get_collection(settings.qdrant_collection_name).points_count
    print(f"\nTOPLAM COLLECTION: {total} chunk\n")

    # Hepsini cek
    by_source = defaultdict(list)
    next_off = None
    while True:
        points, next_off = client.scroll(
            collection_name=settings.qdrant_collection_name,
            limit=500,
            with_payload=True,
            with_vectors=False,
            offset=next_off,
        )
        if not points:
            break
        for p in points:
            src = p.payload.get("source_title", "?")
            by_source[src].append(p)
        if next_off is None:
            break

    # Tum kaynakları gruplara ayir
    rebhuns = ["RebhunsDiseasesDairyCattle"]
    amasya = ["Amasya_DSYB_kaynak"]
    new_tr = [k for k in by_source if k not in rebhuns + amasya]

    print(f"{'='*80}")
    print(f"KAYNAK BAZINDA RAPOR")
    print(f"{'='*80}")
    print(f"{'Kaynak':<45} {'Chunk':>7} {'Avg':>5} {'Bozuk':>6} {'<30':>5} {'TOC':>5}")
    print(f"{'-'*80}")

    total_tr_chunks = 0
    total_en_chunks = 0
    quality_summary = []

    for src in sorted(by_source.keys()):
        chunks = by_source[src]
        n = len(chunks)
        text_lens = [len(p.payload.get("text", "")) for p in chunks]
        avg = sum(text_lens) // max(n, 1)
        short = sum(1 for L in text_lens if L < 30)

        # Bozuk Turkce separator
        bad_sep = 0
        toc_hits = 0
        bib_hits = 0
        page_no_hits = 0
        for p in chunks:
            t = p.payload.get("text", "")
            for pat in BAD_SEP_PATTERNS:
                bad_sep += t.count(pat)
            if TOC_PATTERN.search(t):
                toc_hits += 1
            if BIB_PATTERN.search(t):
                bib_hits += 1
            if PAGE_NO_PATTERN.match(t.strip()):
                page_no_hits += 1

        lang = chunks[0].payload.get("language", "?")
        if lang == "tr":
            total_tr_chunks += n
        else:
            total_en_chunks += n

        src_short = src[:43] + ".." if len(src) > 43 else src
        print(f"{src_short:<45} {n:>7} {avg:>5} {bad_sep:>6} {short:>5} {toc_hits:>5}")

        quality_summary.append({
            "src": src,
            "n": n,
            "avg_len": avg,
            "bad_sep": bad_sep,
            "short_pct": 100 * short / max(n, 1),
            "toc_hits": toc_hits,
            "bib_hits": bib_hits,
            "page_no_hits": page_no_hits,
            "lang": lang,
        })

    print()
    print(f"{'='*80}")
    print(f"DIL DAGILIMI")
    print(f"{'='*80}")
    total = total_tr_chunks + total_en_chunks
    print(f"TR: {total_tr_chunks:>6} chunk  ({100*total_tr_chunks/total:.1f}%)")
    print(f"EN: {total_en_chunks:>6} chunk  ({100*total_en_chunks/total:.1f}%)")

    print()
    print(f"{'='*80}")
    print(f"DETAYLI NOISE ANALIZI (TR kaynaklar)")
    print(f"{'='*80}")
    for q in quality_summary:
        if q["lang"] != "tr":
            continue
        print(f"\n--- {q['src'][:70]} ---")
        print(f"  Chunk sayisi:        {q['n']}")
        print(f"  Ortalama uzunluk:    {q['avg_len']} char")
        print(f"  Bozuk Turkce char:   {q['bad_sep']}")
        print(f"  Cok kisa (<30 char): {q['short_pct']:.1f}%")
        print(f"  Icindekiler pattern: {q['toc_hits']} chunk")
        print(f"  Bibliyografya patt.: {q['bib_hits']} chunk")
        print(f"  Sayfa numarasi only: {q['page_no_hits']} chunk")


if __name__ == "__main__":
    analyze()
