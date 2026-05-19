"""
PaytarAI — Chunk verification script

Yeni paytar_veterinary_bge koleksiyonundaki chunk'larin saglikli olup olmadigini
kontrol eder:
1. Toplam point sayisi
2. Kaynak bazinda dagilim (source_title)
3. Dil tespiti (language)
4. parent_text alaninin varligi ve boyutu
5. Bos veya kisa chunk taramasi (potansiyel sorun)
6. Her kaynaktan ornek 2 chunk gosterimi (gozle dogrulama)
"""

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.rag.qdrant_store import get_qdrant_client


def main():
    client = get_qdrant_client()
    coll = settings.qdrant_collection_name

    # 1. Genel bilgi
    info = client.get_collection(coll)
    total = info.points_count or 0
    print(f"=== Koleksiyon: {coll} ===")
    print(f"Toplam point: {total}")
    print(f"Vector dim: {info.config.params.vectors.size}")
    print(f"Distance: {info.config.params.vectors.distance}")
    print()

    # 2. Tum point'leri scroll ederek metadata istatistigi al
    source_counts = Counter()
    language_counts = Counter()
    parent_text_present = 0
    parent_text_lens = []
    child_text_lens = []
    empty_text = 0
    very_short_text = 0  # <20 karakter
    samples_per_source = {}  # source_title -> [chunks]

    next_offset = None
    seen = 0
    batch_size = 256
    while True:
        points, next_offset = client.scroll(
            collection_name=coll,
            limit=batch_size,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            break
        for p in points:
            payload = p.payload or {}
            src = payload.get("source_title", "?")
            lang = payload.get("language", "?")
            source_counts[src] += 1
            language_counts[lang] += 1

            text = payload.get("text", "")
            parent = payload.get("parent_text", "")

            child_text_lens.append(len(text))
            if not text or not text.strip():
                empty_text += 1
            elif len(text) < 20:
                very_short_text += 1

            if parent:
                parent_text_present += 1
                parent_text_lens.append(len(parent))

            # Her kaynaktan 2 ornek topla
            if src not in samples_per_source:
                samples_per_source[src] = []
            if len(samples_per_source[src]) < 2:
                samples_per_source[src].append((text[:150], parent[:200]))
            seen += 1
        if next_offset is None:
            break

    # 3. Sonuc raporu
    print("=== KAYNAK DAGILIMI ===")
    for src, cnt in source_counts.most_common():
        pct = cnt * 100 / total if total else 0
        print(f"  {src:50s} {cnt:>6d} ({pct:.1f}%)")
    print()

    print("=== DIL DAGILIMI ===")
    for lang, cnt in language_counts.most_common():
        pct = cnt * 100 / total if total else 0
        print(f"  {lang:10s} {cnt:>6d} ({pct:.1f}%)")
    print()

    print("=== METIN ALANLARI ===")
    print(f"  parent_text dolu : {parent_text_present:>6d} / {total} ({parent_text_present*100/total:.1f}%)")
    if child_text_lens:
        avg_c = sum(child_text_lens) / len(child_text_lens)
        print(f"  child text  : avg {avg_c:.0f} kar, min {min(child_text_lens)}, max {max(child_text_lens)}")
    if parent_text_lens:
        avg_p = sum(parent_text_lens) / len(parent_text_lens)
        print(f"  parent text : avg {avg_p:.0f} kar, min {min(parent_text_lens)}, max {max(parent_text_lens)}")
    print(f"  bos child text   : {empty_text}")
    print(f"  cok kisa (<20kar): {very_short_text}")
    print()

    print("=== KAYNAK BASINA ORNEKLER ===")
    for src, samples in samples_per_source.items():
        print(f"\n--- {src} ---")
        for i, (child, parent) in enumerate(samples, 1):
            print(f"  [Ornek {i}] CHILD ({len(child)} kar):")
            print(f"    {child}")
            print(f"  [Ornek {i}] PARENT ({len(parent)} kar) ilk 200 kar:")
            print(f"    {parent}")
    print()

    # 4. Saglik degerlendirmesi
    print("=== SAGLIK DEGERLENDIRMESI ===")
    issues = []
    if parent_text_present < total:
        issues.append(f"❌ {total - parent_text_present} point'te parent_text eksik")
    if empty_text > 0:
        issues.append(f"❌ {empty_text} point'te child text bos")
    if very_short_text > total * 0.05:
        issues.append(f"⚠️  {very_short_text} cok kisa chunk (>5% — kalite riski)")

    if not issues:
        print("  ✓ Hicbir sorun tespit edilmedi")
    else:
        for i in issues:
            print(f"  {i}")


if __name__ == "__main__":
    main()
