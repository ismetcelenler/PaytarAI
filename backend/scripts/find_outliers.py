"""Devasa chunk'lari bul ve incele."""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.rag.qdrant_store import get_qdrant_client

client = get_qdrant_client()
coll = settings.qdrant_collection_name

next_offset = None
outliers = []  # (point_id, child_len, parent_len, source, child_preview)
LARGE = 5000  # 5000 karakterden buyuk chunk'lar

while True:
    points, next_offset = client.scroll(
        collection_name=coll, limit=256, offset=next_offset,
        with_payload=True, with_vectors=False,
    )
    if not points:
        break
    for p in points:
        payload = p.payload or {}
        child = payload.get("text", "")
        parent = payload.get("parent_text", "")
        if len(child) > LARGE:
            outliers.append({
                "id": str(p.id),
                "child_len": len(child),
                "parent_len": len(parent),
                "source": payload.get("source_title", "?"),
                "child_preview": child[:300].replace("\n", " "),
            })
    if next_offset is None:
        break

print(f"\n{LARGE}+ karakter child chunk sayisi: {len(outliers)}")
print()

# Boyuta gore sirala
outliers.sort(key=lambda x: -x["child_len"])

for i, o in enumerate(outliers[:10], 1):
    print(f"--- {i}. Outlier ---")
    print(f"  Kaynak: {o['source']}")
    print(f"  Child len: {o['child_len']} kar")
    print(f"  Parent len: {o['parent_len']} kar")
    print(f"  Child == Parent? {o['child_len'] == o['parent_len']}")
    print(f"  Ilk 300 kar: {o['child_preview']}")
    print()

# Boyut dagilimi
print("=== TUM CHUNK BOYUT DAGILIMI ===")
buckets = {
    "<100 kar": 0,
    "100-500 kar": 0,
    "500-1000 kar": 0,
    "1000-5000 kar": 0,
    "5000-20000 kar": 0,
    ">20000 kar": 0,
}

next_offset = None
while True:
    points, next_offset = client.scroll(
        collection_name=coll, limit=512, offset=next_offset,
        with_payload=True, with_vectors=False,
    )
    if not points:
        break
    for p in points:
        c = len((p.payload or {}).get("text", ""))
        if c < 100: buckets["<100 kar"] += 1
        elif c < 500: buckets["100-500 kar"] += 1
        elif c < 1000: buckets["500-1000 kar"] += 1
        elif c < 5000: buckets["1000-5000 kar"] += 1
        elif c < 20000: buckets["5000-20000 kar"] += 1
        else: buckets[">20000 kar"] += 1
    if next_offset is None:
        break

total = sum(buckets.values())
for k, v in buckets.items():
    pct = v * 100 / total if total else 0
    print(f"  {k:18s} {v:>6d} ({pct:.1f}%)")
