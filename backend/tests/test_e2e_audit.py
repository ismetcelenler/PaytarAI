"""Detayli E2E test — audit log ile."""
import httpx, json, sys
sys.stdout.reconfigure(encoding='utf-8')

r = httpx.post('http://127.0.0.1:8000/api/v1/chat', json={
    'message': 'sut hummasi tedavisi nasil yapilir',
    'user_role': 'veterinarian',
    'input_source': 'text'
}, timeout=180)

data = r.json()
print(f"STATUS: {r.status_code}")
print(f"CONFIDENCE: {data.get('evidence_confidence')}")
print(f"CRITIC: {data.get('critic_attempts')} retry")

print(f"\n--- AUDIT LOG ---")
for entry in data.get('audit_log', []):
    print(f"  [{entry.get('action')}] {entry.get('reason', '')}")

print(f"\n--- YANIT (ilk 300 kar) ---")
print(data.get('response', '')[:300])
