import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.graph.workflow import get_workflow
from app.graph.state import AgentState
import pprint

graph = get_workflow()

state = {
    "messages": [
        {"role": "user", "content": "öksüren hayvana ne yapılır"}
    ],
    "user_role": "producer",
    "retrieved_docs": [],
    "critic_feedback": [],
    "retry_count": 0,
    "confidence": "unknown"
}

try:
    print("Graph baslatiliyor...")
    final_state = graph.invoke(state)
    print("BASARILI!")
    print(final_state.get("draft_response", "YOK"))
except Exception as e:
    import traceback
    print("HATA OLUSTU:")
    traceback.print_exc()
