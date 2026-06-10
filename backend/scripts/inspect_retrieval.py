"""
Kullanici sorgusuna gelen retrieved_docs'u incele.
Yanitlarin kaynaktan gercekten alinip alinmadigini gormek icin.
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag import embeddings  # noqa: F401  — langgraph'tan once yuklenmeli
from app.graph.workflow import get_workflow


def make_state(query: str, role: str = "producer") -> dict:
    return {
        "messages": [{"role": "user", "content": query}],
        "retrieved_docs": [],
        "tool_outputs": {},
        "thread_memory": {},
        "critic_attempts": 0,
        "compression_summary": "",
        "response_status": "",
        "user_role": role,
        "input_source": "text",
        "evidence_confidence": "insufficient",
        "audit_log": [],
        "draft_response": "",
        "critic_rejection_reasons": [],
        "final_response": "",
        "request_id": "inspect-test",
        "active_model": "",
        "retrieval_similarity_score": 0.0,
        "source_agreement": False,
        "dosage_triplet_validated": False,
        "source_trust_level": 5,
    }


def main():
    if len(sys.argv) < 2:
        query = "inegim yem yemiyor ne yapayim"
    else:
        query = " ".join(sys.argv[1:])

    print(f"=== SORGU: {query} ===\n")
    wf = get_workflow()
    result = wf.invoke(make_state(query))

    print(f"Top sim score: {result.get('retrieval_similarity_score', 0):.3f}")
    print(f"Response status: {result.get('response_status', '')}")
    print(f"Evidence confidence: {result.get('evidence_confidence', '')}")
    print(f"Toplam chunk gelen: {len(result.get('retrieved_docs', []))}\n")

    for i, doc in enumerate(result.get("retrieved_docs", []), 1):
        score = doc.get("score", 0)
        meta = doc.get("metadata", {})
        text = doc.get("text", "")
        src = meta.get("source_title", "?")
        lang = meta.get("language", "?")
        print(f"=== CHUNK {i} — score={score:.3f} | source={src} | lang={lang} ===")
        # parent_text uzun olabilir, ilk 1500 kar goster
        print(text[:1500].encode("ascii", "replace").decode("ascii"))
        print(f"... [toplam {len(text)} karakter]")
        print()

    print("=" * 60)
    print("FINAL RESPONSE (yanıt):")
    print("=" * 60)
    print(result.get("final_response", "")[:1200].encode("ascii", "replace").decode("ascii"))


if __name__ == "__main__":
    main()
