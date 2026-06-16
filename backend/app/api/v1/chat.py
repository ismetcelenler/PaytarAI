"""
PaytarAI — Chat Endpoints

İki endpoint:
  - POST /chat        → eski blocking endpoint, tek seferde tam yanit doner.
  - POST /chat/stream → SSE stream, LangGraph node geciglerini canli yayinlar.

LangGraph workflow'u akista (astream) calistirilir; her node bittiginde "step"
event'i, son adimda "result" event'i yayilir.

Multi-turn:
  Frontend `messages` listesini her requestte gonderir (history dahil). Backend
  AgentState["messages"] olarak bunu kullanir → retriever ve scope_check
  birlesik baglami gorur (clarification cevabini onceki sorguyla beraber
  arama icin).

Spam koruma:
  Cok kisa mesajlar (< 12 char veya < 3 kelime) 400 ile reddedilir.
  Bu sayede clarification turunda "evet" / "tamam" / "..." gibi yararsiz
  cevaplar pipeline'i tetiklemez. Backend = source of truth; frontend ayrica
  client-side ipucu gosterir.
"""

import asyncio
import json
import re
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.graph.workflow import get_workflow

router = APIRouter(tags=["Chat"])


# ─────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELLERI
# ─────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Chat istegi modeli."""
    message: str
    user_role: str  # "veterinarian" | "producer"
    thread_id: str | None = None
    animal_weight_kg: float | None = None
    input_source: str = "text"
    debug: bool = False
    response_length: str = "medium"
    # Multi-turn history: frontend her requestte tam mesaj dizisini gonderir.
    # Backend retriever ve scope_check'e birlesik baglam icin verir.
    # Format: [{"role": "user"|"assistant", "content": str, "kind"?: str}, ...]
    messages: list[dict] | None = None


class ChatResponse(BaseModel):
    """Chat yanit modeli."""
    response: str
    thread_id: str
    evidence_confidence: str
    sources: list[dict] = []
    chunks: list[dict] = []
    sentence_citations: list[dict] = []
    # clarification_node aktifse strukturli payload — frontend ozel UI render eder.
    # {"intro": str, "differentials": [str], "follow_up_questions": [str]}
    clarification: dict | None = None
    # response_status: "ok" | "clarification_needed" | "clarification_exhausted"
    # | "insufficient_evidence" | "out_of_scope" | "fallback" | "error"
    response_status: str | None = None
    critic_attempts: int = 0
    audit_entry_count: int = 0
    audit_log: list[dict] = []
    debug_trace: list[dict] = []
    grounding_action: str | None = None
    retrieval_similarity_score: float = 0.0
    rerank_top_score: float = 0.0


# ─────────────────────────────────────────────────────────────────
# SPAM KORUMASI
# ─────────────────────────────────────────────────────────────────

# Mesaj minimum: 12 karakter VE 3 anlamli kelime (>=2 harfli).
# "evet", "tamam", "ok", "bilmiyorum", "...", "?" tipi yararsiz cevaplar
# tek tur clarification'i bosa harcamasin diye pipeline ONCE engellenir.
MIN_MESSAGE_CHARS = 12
MIN_MESSAGE_WORDS = 3
_WORD_RE = re.compile(r"[A-Za-zĞÜŞİÖÇğüşıöç0-9]{2,}")


def _validate_message_length(text: str) -> tuple[bool, str]:
    """(ok, hata_mesaji) doner. ok=True ise hata yok."""
    stripped = (text or "").strip()
    if len(stripped) < MIN_MESSAGE_CHARS:
        return False, (
            f"Mesaj çok kısa (en az {MIN_MESSAGE_CHARS} karakter). "
            "Lütfen sorununu biraz daha detaylı yaz; "
            "belirtileri, yaşı, süreyi de ekle."
        )
    words = _WORD_RE.findall(stripped)
    if len(words) < MIN_MESSAGE_WORDS:
        return False, (
            f"Mesaj çok kısa (en az {MIN_MESSAGE_WORDS} kelime). "
            "Sorunu daha tarif edici yaz: ne gördün, ne zamandan beri, "
            "hangi hayvanlarda."
        )
    return True, ""


# ─────────────────────────────────────────────────────────────────
# YARDIMCILAR
# ─────────────────────────────────────────────────────────────────

def _build_initial_state(request: ChatRequest) -> tuple[str, str, dict]:
    """ChatRequest'ten AgentState seedi olustur, (request_id, thread_id, state) doner.

    `messages` history varsa onu kullanir, yoksa sadece son mesaji koyar.
    Bu sayede multi-turn clarification akisinda backend birlesik baglami gorur."""
    request_id = str(uuid.uuid4())[:8]
    thread_id = request.thread_id or str(uuid.uuid4())[:12]

    # Multi-turn history: frontend gönderdiyse onu kullan, yoksa sadece son msg.
    # Her durumda son mesajin user rolu olmasi beklenir.
    if request.messages and isinstance(request.messages, list):
        msgs: list[dict] = []
        for m in request.messages:
            if not isinstance(m, dict) or not m.get("content"):
                continue
            item: dict = {
                "role": m.get("role", "user"),
                "content": str(m["content"]),
            }
            # kind alanini koru (clarification sayaci icin gerekli)
            if isinstance(m.get("kind"), str):
                item["kind"] = m["kind"]
            msgs.append(item)
        # Son mesaj user degilse veya history bossa request.message'i ekle
        if not msgs or msgs[-1].get("role") != "user":
            msgs.append({"role": "user", "content": request.message})
    else:
        msgs = [{"role": "user", "content": request.message}]

    # Multi-turn clarification: state'te onceki clarification_attempts sayisini
    # geri hesapla (assistant mesajlarinda kac tanesi clarification idi sayilir).
    prior_clarification = 0
    for m in msgs:
        if m.get("role") == "assistant" and isinstance(m.get("kind"), str):
            if m["kind"] == "clarification":
                prior_clarification += 1

    state = {
        "messages": msgs,
        "retrieved_docs": [],
        "tool_outputs": {},
        "thread_memory": {},
        "critic_attempts": 0,
        "compression_summary": "",
        "response_status": "",
        "user_role": request.user_role,
        "input_source": request.input_source,
        "response_length": request.response_length if request.response_length in ("short", "medium", "long") else "medium",
        "evidence_confidence": "insufficient",
        "audit_log": [],
        "debug_trace": [],
        "draft_response": "",
        "critic_rejection_reasons": [],
        "final_response": "",
        "request_id": request_id,
        "active_model": "",
        "retrieval_similarity_score": 0.0,
        "source_agreement": False,
        "dosage_triplet_validated": False,
        "source_trust_level": 5,
        "clarification_attempts": prior_clarification,
        "clarification_payload": {},
    }
    return request_id, thread_id, state


def _build_response_payload(result: dict, thread_id: str, debug: bool) -> dict:
    """workflow ciktisindan ChatResponse-shaped dict olustur."""
    # GORUNEN SKOR = reranker sigmoid skoru (cross-encoder ince elek sonucu),
    # dense cosine DEGIL. retrieved_docs zaten reranker sirasinda (TR pool +
    # EN pool, her biri rerank-desc); UI'da gosterilen skorun da bu siralamayi
    # yansitmasi icin rerank_score kullanilir. Dense cosine ayri alanda korunur.
    # NOT: Sira DEGISTIRILMEZ — chunk_id pozisyonel (claim_attribution
    # retrieved_docs[:5] index'ini kullanir), reorder atif hizalamasini bozar.
    def _display_score(doc: dict) -> float:
        rerank = doc.get("rerank_score")
        if rerank is not None:
            return round(float(rerank), 4)
        return round(float(doc.get("score", 0.0)), 4)

    sources = []
    snippet_len = 800 if debug else 200
    for doc in result.get("retrieved_docs", [])[:5]:
        sources.append({
            "title": doc["metadata"].get("source_title", ""),
            "score": _display_score(doc),
            "dense_score": round(float(doc.get("score", 0.0)), 4),
            "snippet": doc["text"][:snippet_len],
        })

    chunks = []
    for doc in result.get("retrieved_docs", [])[:5]:
        chunks.append({
            "title": doc["metadata"].get("source_title", ""),
            "language": doc["metadata"].get("language"),
            "score": _display_score(doc),
            "dense_score": round(float(doc.get("score", 0.0)), 4),
            "text": doc["text"],
        })

    sentence_citations: list[dict] = []
    for entry in result.get("debug_trace", []):
        if entry.get("node") == "claim_attribution":
            out = entry.get("output") or {}
            if not out.get("skipped") and isinstance(out.get("sentences"), list):
                sentence_citations = out["sentences"]
            break

    debug_trace = result.get("debug_trace", []) if debug else []
    response_text = (
        result.get("final_response")
        or result.get("draft_response")
        or "Yanit uretilemedi."
    )

    clarification_payload = result.get("clarification_payload") or None
    if not isinstance(clarification_payload, dict) or not clarification_payload:
        clarification_payload = None

    return {
        "response": response_text,
        "thread_id": thread_id,
        "evidence_confidence": result.get("evidence_confidence", "insufficient"),
        "sources": sources,
        "chunks": chunks,
        "sentence_citations": sentence_citations,
        "clarification": clarification_payload,
        "response_status": result.get("response_status"),
        "critic_attempts": result.get("critic_attempts", 0),
        "audit_entry_count": len(result.get("audit_log", [])),
        "audit_log": result.get("audit_log", []),
        "debug_trace": debug_trace,
        "grounding_action": result.get("grounding_action"),
        "retrieval_similarity_score": result.get("retrieval_similarity_score", 0.0),
        "rerank_top_score": result.get("rerank_top_score", 0.0),
    }


# ─────────────────────────────────────────────────────────────────
# /chat — eski blocking endpoint
# ─────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint — LangGraph workflow'unu sync calistirir."""
    ok, err = _validate_message_length(request.message)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    _, thread_id, initial_state = _build_initial_state(request)
    try:
        workflow = get_workflow()
        result = workflow.invoke(initial_state)
        payload = _build_response_payload(result, thread_id, debug=request.debug)
        return ChatResponse(**payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow hatasi: {str(e)}")


# ─────────────────────────────────────────────────────────────────
# /chat/stream — SSE
# ─────────────────────────────────────────────────────────────────

def _sse_format(event_name: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_name}\ndata: {payload}\n\n"


async def _workflow_event_stream(
    request: ChatRequest,
    http_request: Request,
) -> AsyncGenerator[str, None]:
    request_id, thread_id, initial_state = _build_initial_state(request)
    t0 = time.perf_counter()

    yield _sse_format("start", {
        "thread_id": thread_id,
        "request_id": request_id,
        "ts": int(time.time() * 1000),
    })

    workflow = get_workflow()
    final_state: dict | None = None
    seen_nodes: list[str] = []

    try:
        async for chunk in workflow.astream(initial_state, stream_mode="updates"):
            if await http_request.is_disconnected():
                return

            if not isinstance(chunk, dict):
                continue

            for node_name, partial_state in chunk.items():
                ms_elapsed = int((time.perf_counter() - t0) * 1000)
                seen_nodes.append(node_name)
                yield _sse_format("step", {
                    "node": node_name,
                    "ms_since_start": ms_elapsed,
                    "step_index": len(seen_nodes),
                })

                if final_state is None:
                    final_state = dict(initial_state)
                if isinstance(partial_state, dict):
                    final_state.update(partial_state)

        if final_state is None:
            final_state = initial_state

        payload = _build_response_payload(final_state, thread_id, debug=request.debug)
        total_ms = int((time.perf_counter() - t0) * 1000)
        payload["_total_ms"] = total_ms
        payload["_nodes_visited"] = seen_nodes

        yield _sse_format("result", payload)

    except asyncio.CancelledError:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield _sse_format("error", {"detail": str(e)[:500]})


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, http_request: Request):
    """SSE stream endpoint. Cok kisa mesaj 422 ile reddedilir."""
    ok, err = _validate_message_length(request.message)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    return StreamingResponse(
        _workflow_event_stream(request, http_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
