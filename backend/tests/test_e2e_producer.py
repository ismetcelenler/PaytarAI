"""E2E test — Uretici modu."""
import httpx
import sys
sys.stdout.reconfigure(encoding='utf-8')

r = httpx.post('http://127.0.0.1:8000/api/v1/chat', json={
    'message': 'Inegim yere yatti kalkamıyor, ne yapmaliyim?',
    'user_role': 'producer',
    'input_source': 'text'
}, timeout=120)

data = r.json()
print(f"STATUS: {r.status_code}")
print(f"CONFIDENCE: {data.get('evidence_confidence')}")
print(f"CRITIC ATTEMPTS: {data.get('critic_attempts')}")
print()
print("--- YANIT ---")
print(data.get('response', '')[:2000])
