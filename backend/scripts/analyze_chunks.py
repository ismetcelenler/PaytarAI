"""
Qdrant koleksiyonundaki chunk yapisini analiz et.

Olculen:
  1. Child text uzunluk dagilimi
  2. Parent text uzunluk dagilimi
  3. Unique parent sayisi (parent başına kac child)
  4. PDF parse artifact'lari (?, garbled chars, page headers)
  5. Bos / cok kisa chunk var mi
  6. Source dagilimi (kac dosya, kac chunk)
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import re
import sys
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from qdrant_client import QdrantClient


def percentiles(values, ps=(0, 25, 50, 75, 95, 100)):
    s = sorted(values)
    n = len(s)
    return {p: s[min(int(n * p / 100), n - 1)] for p in ps}


def main():
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30)
    coll = settings.qdrant_collection_name
    info = client.get_collection(coll)
    total = info.points_count
    print(f"=== Koleksiyon: {coll} ===")
    print(f"Toplam point: {total}")
    print()

    # Tüm payload'lari cek (vektörsuz, hizli)
    print("Tum chunk'lar cekiliyor (payload only)...")
    child_lens = []
    parent_lens = []
    parent_hashes = []  # benzersiz parent sayimi icin
    sources = Counter()
    languages = Counter()
    garbled = 0
    very_short = 0
    very_long = 0
    artifact_chars = Counter()  # ? karakter sayisi
    suspicious_examples = []

    next_off = None
    fetched = 0
    while True:
        points, next_off = client.scroll(
            collection_name=coll,
            limit=500,
            with_payload=True,
            with_vectors=False,
            offset=next_off,
        )
        if not points:
            break
        for p in points:
            payload = p.payload
            child = payload.get("text", "")
            parent = payload.get("parent_text", "")

            child_lens.append(len(child))
            parent_lens.append(len(parent))
            parent_hashes.append(hash(parent[:200]))  # ilk 200 char ile hash
            sources[payload.get("source_title", "?")] += 1
            languages[payload.get("language", "?")] += 1

            # Quality issues
            if len(child) < 30:
                very_short += 1
                if len(suspicious_examples) < 5:
                    suspicious_examples.append(("VERY_SHORT", child[:100]))
            if len(child) > 800:
                very_long += 1
            # ? karakter (OCR artifact)
            qmark = child.count("?")
            if qmark > 10 and qmark / max(len(child), 1) > 0.05:
                garbled += 1
                if len(suspicious_examples) < 10:
                    suspicious_examples.append(("GARBLED", child[:120]))
            artifact_chars["?"] += qmark
            artifact_chars["�"] += child.count("�")  # replacement char

        fetched += len(points)
        if fetched % 2000 == 0:
            print(f"  ... {fetched}/{total}")
        if next_off is None:
            break

    print(f"Fetched: {fetched}\n")

    print("=== Child text uzunlugu (karakter) ===")
    p = percentiles(child_lens)
    print(f"  min={p[0]}  p25={p[25]}  median={p[50]}  p75={p[75]}  p95={p[95]}  max={p[100]}")
    print(f"  Avg: {sum(child_lens)/len(child_lens):.0f}")
    print(f"  Cok kisa (<30 char): {very_short} ({100*very_short/len(child_lens):.1f}%)")
    print(f"  Cok uzun (>800 char): {very_long} ({100*very_long/len(child_lens):.1f}%)")
    print()

    print("=== Parent text uzunlugu (karakter) ===")
    p = percentiles(parent_lens)
    print(f"  min={p[0]}  p25={p[25]}  median={p[50]}  p75={p[75]}  p95={p[95]}  max={p[100]}")
    print(f"  Avg: {sum(parent_lens)/len(parent_lens):.0f}")
    print()

    print("=== Parent uniqueness (parent basina kac child) ===")
    unique_parents = len(set(parent_hashes))
    print(f"  Toplam child: {len(parent_hashes)}")
    print(f"  Benzersiz parent: {unique_parents}")
    print(f"  Parent basina ortalama child: {len(parent_hashes)/unique_parents:.1f}")
    print()

    print("=== Source dagilimi ===")
    for src, cnt in sources.most_common():
        s = str(src).encode("ascii", "replace").decode()
        print(f"  {s}: {cnt}")
    print()

    print("=== Dil dagilimi ===")
    for lang, cnt in languages.most_common():
        print(f"  {lang}: {cnt}")
    print()

    print("=== OCR/Parse artifact'lari ===")
    print(f"  ? karakter (kucuk yontemli) toplam: {artifact_chars['?']}")
    print(f"  Replacement char (U+FFFD) toplam: {artifact_chars['�']}")
    print(f"  Garbled chunk (>10 ?, oran >%5): {garbled} ({100*garbled/len(child_lens):.2f}%)")
    print()

    print("=== SUSPICIOUS ORNEKLER ===")
    for kind, text in suspicious_examples[:8]:
        t = text.encode("ascii", "replace").decode()
        print(f"  [{kind}] {t}")


if __name__ == "__main__":
    main()
