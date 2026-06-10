"""
Cok kisa chunk'lari (text < 30 char) Qdrant'tan temizle.

Bu chunk'lar tipik olarak:
  - Sayfa header/footer artifact'i
  - PDF'in bos satir / numerik satir
  - Anlamsiz fragment
  - Retrieve edildiginde generator'a hicbir bilgi vermiyor

Kullanim:
  # Dry-run (sadece listele, silme):
  python scripts/clean_short_chunks.py

  # Gercek sil:
  python scripts/clean_short_chunks.py --delete
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointIdsList


MIN_CHILD_LEN = 30  # char


def main():
    do_delete = "--delete" in sys.argv

    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=60)
    total = client.get_collection(settings.qdrant_collection_name).points_count
    print(f"Toplam chunk: {total}")
    print(f"Esik: child text < {MIN_CHILD_LEN} char")
    print(f"Mod: {'DELETE' if do_delete else 'DRY-RUN'}\n")

    short_ids = []
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
            text = p.payload.get("text", "") or ""
            if len(text.strip()) < MIN_CHILD_LEN:
                short_ids.append(p.id)
                src = p.payload.get("source_title", "?")
                by_source[src].append((p.id, text.strip()[:60]))
        if next_off is None:
            break

    print(f"{'='*80}")
    print(f"KAYNAK BAZINDA KISA CHUNK SAYISI")
    print(f"{'='*80}")
    for src in sorted(by_source.keys(), key=lambda s: -len(by_source[s])):
        print(f"  {src:<50} {len(by_source[src]):>5}")

    print(f"\nTOPLAM SILINECEK: {len(short_ids)} chunk ({100*len(short_ids)/total:.2f}%)")

    # Ornek 5 chunk goster
    print(f"\n{'='*80}")
    print(f"ORNEK 5 CHUNK (silinecek)")
    print(f"{'='*80}")
    sample = []
    for src, items in by_source.items():
        for pid, txt in items[:2]:
            sample.append((src, pid, txt))
        if len(sample) >= 10:
            break
    for src, pid, txt in sample[:10]:
        print(f"  [{src[:25]:<25}] {txt!r}")

    if not do_delete:
        print(f"\n[DRY-RUN] Hicbir sey silinmedi.")
        print(f"Silmek icin: python scripts/clean_short_chunks.py --delete")
        return

    if not short_ids:
        print("\nSilinecek chunk yok.")
        return

    # Batch sil
    print(f"\n{len(short_ids)} chunk siliniyor...")
    BATCH = 500
    for i in range(0, len(short_ids), BATCH):
        batch = short_ids[i:i + BATCH]
        client.delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=PointIdsList(points=batch),
            wait=True,
        )
        print(f"  Batch {i // BATCH + 1}: {len(batch)} silindi")

    after = client.get_collection(settings.qdrant_collection_name).points_count
    print(f"\nOnce: {total}, Sonra: {after}, Silinen: {total - after}")


if __name__ == "__main__":
    main()
