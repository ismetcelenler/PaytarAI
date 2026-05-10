"""Chunk kalite denetimi — Qdrant'taki tum chunklari cekip analiz eder."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from qdrant_client import QdrantClient
from app.config import settings

client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)

# Tum chunklari cek
results = client.scroll(
    collection_name="paytar_veterinary",
    limit=100,
    with_payload=True,
    with_vectors=False,
)

chunks = results[0]
print(f"Toplam chunk: {len(chunks)}\n")

issues = []

for i, point in enumerate(chunks):
    text = point.payload.get("text", "")
    meta = {k: v for k, v in point.payload.items() if k != "text"}
    
    word_count = len(text.split())
    char_count = len(text)
    
    # Sorun tespiti
    chunk_issues = []
    
    # 1. Cok kisa chunk (anlamli bilgi icermeyebilir)
    if word_count < 50:
        chunk_issues.append(f"COK KISA ({word_count} kelime)")
    
    # 2. Cok uzun chunk (embedding kalitesi duser)
    if word_count > 1500:
        chunk_issues.append(f"COK UZUN ({word_count} kelime)")
    
    # 3. Cumle ortasinda kesilmis mi
    if text.strip() and not text.strip()[-1] in '.!?:"\n':
        last_30 = text.strip()[-30:]
        chunk_issues.append(f"CUMLE ORTASINDA KESILMIS (son: ...{last_30})")
    
    # 4. Gorsel placeholder
    if "<!-- image -->" in text:
        img_count = text.count("<!-- image -->")
        chunk_issues.append(f"GORSEL PLACEHOLDER ({img_count} adet)")
    
    # 5. Bos satirlarla baslama
    if text.startswith("\n\n\n"):
        chunk_issues.append("BOS SATIRLARLA BASLIYOR")
    
    # 6. Tablo kalintisi
    if "|" in text and text.count("|") > 10:
        chunk_issues.append("TABLO ICERIYOR (dogru parse edilmis mi?)")
    
    # Ozet
    status = "⚠️" if chunk_issues else "✅"
    print(f"[Chunk {i+1:2d}] {status} {word_count:4d} kelime | {char_count:5d} kar")
    
    if chunk_issues:
        for issue in chunk_issues:
            print(f"           -> {issue}")
        issues.append((i+1, chunk_issues))
    
    # Ilk ve son 80 karakter
    first = text[:80].replace("\n", " ").strip()
    last = text[-80:].replace("\n", " ").strip()
    print(f"           Bas: {first}")
    print(f"           Son: ...{last}")
    print()

print(f"\n{'='*60}")
print(f"SONUC: {len(chunks)} chunk, {len(issues)} sorunlu")
if issues:
    print(f"\nSORUNLU CHUNKLAR:")
    for idx, iss in issues:
        print(f"  Chunk {idx}: {', '.join(iss)}")
else:
    print("Tum chunklar temiz!")
