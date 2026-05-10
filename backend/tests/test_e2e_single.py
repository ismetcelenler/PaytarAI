"""Tek sorgu E2E test — Groq."""
import httpx
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("Sorgu gonderiliyor...")
r = httpx.post('http://127.0.0.1:8000/api/v1/chat', json={
    'message': 'sut hummasi tedavisi nasil yapilir',
    'user_role': 'veterinarian',
    'input_source': 'text'
}, timeout=180)

data = r.json()
print(f"STATUS: {r.status_code}")
print(f"CONFIDENCE: {data.get('evidence_confidence')}")
print(f"CRITIC: {data.get('critic_attempts')} retry")
print(f"SOURCES: {len(data.get('sources', []))}")

response = data.get('response', '')
print(f"\n--- YANIT ---")
print(response[:1200])

# Birim kontrolu
bad_units = ['gallon', ' lb', ' oz', 'fahrenheit']
found = [u for u in bad_units if u.lower() in response.lower()]
print(f"\nBirim kontrolu: {'YANLIS BIRIM: ' + str(found) if found else 'GECTI'}")

# Kaynak
for s in data.get('sources', []):
    print(f"  [{s.get('score', 0):.4f}] {s.get('title', '')}")
