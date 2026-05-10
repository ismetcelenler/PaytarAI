"""
PaytarAI — Chat Endpoint

LangGraph workflow'unu tetikler ve yanit doner.
"""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.graph.workflow import get_workflow

router = APIRouter(tags=["Chat"])


class ChatRequest(BaseModel):
    """Chat istegi modeli."""
    message: str
    user_role: str  # "veterinarian" | "producer"
    thread_id: str | None = None
    animal_weight_kg: float | None = None
    input_source: str = "text"  # "text" | "voice"


class ChatResponse(BaseModel):
    """Chat yanit modeli."""
    response: str
    thread_id: str
    evidence_confidence: str
    sources: list[dict] = []
    critic_attempts: int = 0
    audit_entry_count: int = 0
    audit_log: list[dict] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint — LangGraph workflow'unu calistirir.

    Akis: Compress -> Retriever -> Generator -> Critic -> Confidence
    """
    request_id = str(uuid.uuid4())[:8]
    thread_id = request.thread_id or str(uuid.uuid4())[:12]

    # Initial state olustur
    initial_state = {
        "messages": [
            {"role": "user", "content": request.message},
        ],
        "retrieved_docs": [],
        "tool_outputs": {},
        "thread_memory": {},
        "critic_attempts": 0,
        "compression_summary": "",
        "response_status": "",
        "user_role": request.user_role,
        "input_source": request.input_source,
        "evidence_confidence": "insufficient",
        "audit_log": [],
        "draft_response": "",
        "critic_rejection_reasons": [],
        "final_response": "",
        "request_id": request_id,
        "active_model": "",
        "retrieval_similarity_score": 0.0,
        "source_agreement": False,
        "dosage_triplet_validated": False,
        "source_trust_level": 5,
    }

    try:
        workflow = get_workflow()
        result = workflow.invoke(initial_state)

        # Kaynak bilgilerini cikart
        sources = []
        for doc in result.get("retrieved_docs", [])[:3]:
            sources.append({
                "title": doc["metadata"].get("source_title", ""),
                "score": round(doc["score"], 4),
                "snippet": doc["text"][:200],
            })

        return ChatResponse(
            response=result.get("final_response", result.get("draft_response", "Yanit uretilemedi.")),
            thread_id=thread_id,
            evidence_confidence=result.get("evidence_confidence", "insufficient"),
            sources=sources,
            critic_attempts=result.get("critic_attempts", 0),
            audit_entry_count=len(result.get("audit_log", [])),
            audit_log=result.get("audit_log", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow hatasi: {str(e)}")
