import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from app.graph.workflow import get_workflow
app_graph = get_workflow()
from langchain_core.messages import HumanMessage

queries = [
    "hayvanım yere düştü kalkamıyor"
]

for q in queries:
    print(f"\n{'='*80}")
    print(f"Sorgu: {q}")
    print(f"{'='*80}")
    
    state = {
        "messages": [{"role": "user", "content": q}],
        "user_role": "veterinarian",
        "input_source": "text",
        "evidence_confidence": 0.0,
        "retrieved_context": "",
        "critic_attempts": 0,
        "is_valid": False,
        "final_response": ""
    }
    
    final_state = app_graph.invoke(state)
    
    try:
        conf = float(final_state.get('evidence_confidence', 0))
    except (ValueError, TypeError):
        conf = 0.0
    print(f"\n[Güvenilirlik Skoru]: {conf:.2f}")
    print(f"[Arama Sayısı (Critic)]: {final_state.get('critic_attempts', 0)}")
    
    response = final_state.get('final_response', '')
    if not response:
        # Sometimes the final response is the last AI message
        messages = final_state.get("messages", [])
        if messages:
            response = messages[-1].content

    print(f"\n[Yapay Zeka Yanıtı]:\n{response}\n")

