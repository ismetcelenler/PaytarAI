"""E2E test — Groq generator + dual query + birim donusumu."""
import httpx
import sys
sys.stdout.reconfigure(encoding='utf-8')

queries = [
    ("sut hummasi tedavisi nasil yapilir", "veterinarian"),
    ("ketozis tedavisi icin ne yapmaliyim", "veterinarian"),
    ("inegim yere yatti kalkamıyor", "producer"),
]

for q, role in queries:
    print(f"\n{'='*60}")
    print(f"SORGU: {q} (rol: {role})")
    print(f"{'='*60}")
    
    r = httpx.post('http://127.0.0.1:8000/api/v1/chat', json={
        'message': q,
        'user_role': role,
        'input_source': 'text'
    }, timeout=60)
    
    data = r.json()
    print(f"STATUS: {r.status_code}")
    print(f"CONFIDENCE: {data.get('evidence_confidence')}")
    print(f"CRITIC: {data.get('critic_attempts')} retry")
    print(f"SOURCES: {len(data.get('sources', []))}")
    
    response = data.get('response', '')
    print(f"\n--- YANIT (ilk 600 kar) ---")
    print(response[:600])
    
    # Birim kontrolu
    bad_units = ['gallon', 'lb ', 'lb)', 'oz ', ' F ', 'fahrenheit']
    found = [u for u in bad_units if u.lower() in response.lower()]
    if found:
        print(f"\n⚠️ YANLIS BIRIM BULUNDU: {found}")
    else:
        print(f"\n✅ Birim kontrolu gecti")
