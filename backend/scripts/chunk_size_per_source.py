"""
Source bazinda child/parent chunk boyut istatistigi.

Hedef:
  - parent_text: ~2600 char (~400 kelime)
  - child text:  ~300 char (~50 kelime)

Olculen:
  Her kaynak icin child + parent boyut min/p25/p50/p75/p95/max + avg
  Hedef'ten sapma yuzdesi
  Outlier sayisi (cok kisa / cok uzun)
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


TARGET_CHILD = 300  # char (~50 kelime)
TARGET_PARENT = 2600  # char (~400 kelime)


def percentiles(values, ps=(0, 25, 50, 75, 95, 100)):
    s = sorted(values)
    if not s:
        return {p: 0 for p in ps}
    n = len(s)
    return {p: s[min(int(n * p / 100), n - 1)] for p in ps}


def main():
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=60)
    total = client.get_collection(settings.qdrant_collection_name).points_count
    print(f"TOPLAM: {total} chunk\n")
    print(f"Hedef boyutlar: parent ~{TARGET_PARENT} char, child ~{TARGET_CHILD} char\n")

    by_source = defaultdict(lambda: {"child": [], "parent": []})
    by_source_unique_parents = defaultdict(set)
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
            child = p.payload.get("text", "")
            parent = p.payload.get("parent_text", "")
            by_source[src]["child"].append(len(child))
            by_source[src]["parent"].append(len(parent))
            by_source_unique_parents[src].add(parent[:200])
        if next_off is None:
            break

    print(f"{'='*120}")
    print(f"CHILD BOYUT ISTATISTIGI (hedef ~{TARGET_CHILD} char)")
    print(f"{'='*120}")
    print(f"{'Kaynak':<42} {'N':>5} {'min':>4} {'p25':>4} {'p50':>4} {'p75':>4} {'p95':>4} {'max':>4} {'avg':>4} {'sapma':>6} {'<30':>4}")
    print(f"{'-'*120}")
    for src in sorted(by_source.keys()):
        vals = by_source[src]["child"]
        n = len(vals)
        p = percentiles(vals)
        avg = sum(vals) // max(n, 1)
        sapma = (avg - TARGET_CHILD) / TARGET_CHILD * 100
        short = sum(1 for v in vals if v < 30)
        src_short = src[:40]
        print(f"{src_short:<42} {n:>5} {p[0]:>4} {p[25]:>4} {p[50]:>4} {p[75]:>4} {p[95]:>4} {p[100]:>4} {avg:>4} {sapma:>+5.0f}% {short:>4}")

    print()
    print(f"{'='*120}")
    print(f"PARENT BOYUT ISTATISTIGI (hedef ~{TARGET_PARENT} char)")
    print(f"{'='*120}")
    print(f"{'Kaynak':<42} {'N':>5} {'UNIK':>5} {'min':>5} {'p25':>5} {'p50':>5} {'p75':>5} {'p95':>5} {'max':>5} {'avg':>5} {'sapma':>6} {'c/p':>4}")
    print(f"{'-'*120}")
    for src in sorted(by_source.keys()):
        vals = by_source[src]["parent"]
        n = len(vals)
        unique_p = len(by_source_unique_parents[src])
        p = percentiles(vals)
        avg = sum(vals) // max(n, 1)
        sapma = (avg - TARGET_PARENT) / TARGET_PARENT * 100
        child_per_parent = n / max(unique_p, 1)
        src_short = src[:40]
        print(f"{src_short:<42} {n:>5} {unique_p:>5} {p[0]:>5} {p[25]:>5} {p[50]:>5} {p[75]:>5} {p[95]:>5} {p[100]:>5} {avg:>5} {sapma:>+5.0f}% {child_per_parent:>4.1f}")

    print()
    print(f"{'='*120}")
    print(f"OZET")
    print(f"{'='*120}")
    all_child = []
    all_parent = []
    for src in by_source:
        all_child.extend(by_source[src]["child"])
        all_parent.extend(by_source[src]["parent"])

    print(f"GENEL CHILD:  N={len(all_child)}, avg={sum(all_child)//len(all_child)}, "
          f"p50={sorted(all_child)[len(all_child)//2]}, "
          f"p95={sorted(all_child)[int(len(all_child)*0.95)]}")
    print(f"GENEL PARENT: N={len(all_parent)}, avg={sum(all_parent)//len(all_parent)}, "
          f"p50={sorted(all_parent)[len(all_parent)//2]}, "
          f"p95={sorted(all_parent)[int(len(all_parent)*0.95)]}")


if __name__ == "__main__":
    main()
