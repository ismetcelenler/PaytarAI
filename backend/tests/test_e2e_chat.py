"""E2E test — Veteriner modu."""
import httpx
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

r = httpx.post('http://127.0.0.1:8000/api/v1/chat', json={
    'message': 'Milk fever tedavisi icin kalsiyum boroglukonat dozaji nedir?',
    'user_role': 'veterinarian',
    'input_source': 'text'
}, timeout=120)

data = r.json()
print(f"STATUS: {r.status_code}")
print(f"CONFIDENCE: {data.get('evidence_confidence')}")
print(f"CRITIC ATTEMPTS: {data.get('critic_attempts')}")
print(f"SOURCES: {len(data.get('sources', []))}")
print(f"AUDIT ENTRIES: {data.get('audit_entry_count')}")
print()
print("--- YANIT ---")
print(data.get('response', '')[:2000])
print()
print("--- KAYNAKLAR ---")
for s in data.get('sources', []):
    print(f"  [{s['score']:.4f}] {s['title']}")
