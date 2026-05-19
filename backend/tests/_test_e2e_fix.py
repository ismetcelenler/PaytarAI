import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.graph.workflow import get_workflow

workflow = get_workflow()

test_cases = [
    ('hayvanim yere dustu kalkamıyor', 'veterinarian'),
    ('buzağım ishal oluyor', 'producer'),
    ('plasenta atmama nasıl tedavi edilir', 'veterinarian'),
]

for query, role in test_cases:
    print(f'\n{"="*70}')
    print(f'ROL: {role} | SORGU: {query}')
    print('='*70)

    state = {
        'messages': [{'role': 'user', 'content': query}],
        'retrieved_docs': [],
        'tool_outputs': {},
        'thread_memory': {},
        'critic_attempts': 0,
        'compression_summary': '',
        'response_status': '',
        'user_role': role,
        'input_source': 'text',
        'evidence_confidence': 'insufficient',
        'audit_log': [],
        'draft_response': '',
        'critic_rejection_reasons': [],
        'final_response': '',
        'request_id': 'test-01',
        'active_model': '',
        'retrieval_similarity_score': 0.0,
        'source_agreement': False,
        'dosage_triplet_validated': False,
        'source_trust_level': 5,
    }

    result = workflow.invoke(state)

    print(f'Guven: {result.get("evidence_confidence")} | Critic: {result.get("critic_attempts")} | Status: {result.get("response_status")}')
    docs = result.get('retrieved_docs', [])
    print(f'Kaynaklar ({len(docs)}):')
    for d in docs:
        src = d['metadata'].get('source_title', '?')[:30]
        print(f'  {d["score"]:.3f} | {src}')
    print(f'\nYANIT:\n{result.get("final_response", "YOK")[:600]}')
