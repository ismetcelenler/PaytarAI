"""
PaytarAI — Scope Check Node

Kullanici sorgusunun buyukbas hayvan (sigir/inek/buzagi/duve/dana/boga)
kapsaminda olup olmadigini LLM ile siniflandirir.

Out-of-scope ise pipeline durdurulur, sabit template ile yanit verilir.
Boylece halusinasyon onlenir + retriever/generator harcamalari yapilmaz.

LLM: gpt-oss-120b (low reasoning) @ Cerebras
- Reasoning_effort=low: basit yes/no icin reasoning bütçesi israf edilmez
- Hizli (~0.5-1s), ucuz (~50 token input + 5 token output)
"""

from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.audit import audit_log


SCOPE_PROMPT = """Asagidaki kullanici sorgusu BÜYÜKBAŞ HAYVAN (sığır, inek, buzağı, düve, dana, boğa) sağlığı, beslenmesi, üremesi veya işletme yönetimi ile ilgili mi?

ÖRNEKLER:
- "ineğim sütü düştü" → EVET
- "buzağı ishal" → EVET
- "düve kızgınlığa geldi" → EVET
- "holstein özellikleri" → EVET (büyükbaş ırk)
- "kediden hastalık ineğime bulaşır mı" → EVET (asıl konu inek)
- "kuşumun gagası kırıldı" → HAYIR (kanatlı)
- "kedi tüy döküyor" → HAYIR
- "tarlamdaki bitki" → HAYIR
- "kuş gribi" → HAYIR (kanatlı hastalığı)
- "at hastalandı" → HAYIR (tek tırnaklı)
- "köpeğim ne yer" → HAYIR

Sorgu: {query}

Tek kelime cevap ver: EVET veya HAYIR

Cevap:"""


OUT_OF_SCOPE_TEMPLATE = (
    "Bu konuda kesin bilgi veremem. "
    "Sistemimiz yalnızca büyükbaş hayvan (sığır, inek, buzağı, düve, dana) konularında "
    "bilgi sunabiliyor. Lütfen sorduğunuz konuyla ilgili uzmana ya da veteriner hekiminize danışın.\n\n"
    "⚠️ Bu bilgi karar desteğidir."
)


def _classify_scope(query: str) -> tuple[bool, str]:
    """
    Sorguyu in-scope/out-of-scope olarak siniflar.

    Returns:
        (is_in_scope, raw_classifier_output)
    """
    try:
        llm = ChatOpenAI(
            api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            model="gpt-oss-120b",
            temperature=0,
            max_tokens=50,
            reasoning_effort="low",  # type: ignore[call-arg]
        )

        prompt = SCOPE_PROMPT.format(query=query)
        response = llm.invoke(prompt)
        answer = str(response.content).strip().upper()

        # Bos icerik fallback (reasoning model nadir bug)
        if not answer:
            reasoning = response.additional_kwargs.get("reasoning_content", "")
            answer = reasoning.strip().upper() if reasoning else ""

        # "EVET" varsa in-scope, "HAYIR" varsa out-of-scope
        # Belirsizse default: in-scope (yanlis negatif daha az kotu)
        if "HAYIR" in answer or "NO" in answer:
            return False, answer
        return True, answer or "EVET (default)"

    except Exception as e:
        # Hata durumunda in-scope farzet, downstream halletsin
        print(f"[scope_check] hata: {e} — in-scope default")
        return True, f"ERROR: {e}"


def scope_check_node(state: dict) -> dict:
    """
    Kullanici sorgusunun kapsam icinde olup olmadigini kontrol eder.

    Out-of-scope ise:
    - retrieved_docs bos kalir
    - final_response = OUT_OF_SCOPE_TEMPLATE
    - response_status = "out_of_scope"
    - workflow conditional edge ile direkt confidence'a atlar (ya da END)
    """
    messages = state.get("messages", [])
    if not messages:
        state["response_status"] = "error"
        return state

    # Son kullanici mesajini al
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break

    if not last_user_msg:
        state["response_status"] = "error"
        return state

    in_scope, raw_answer = _classify_scope(last_user_msg)

    if in_scope:
        # In-scope: state'i degistirme, normal akis devam etsin
        audit_log(state, "scope_check_in_scope", reason=f"classifier: {raw_answer[:80]}")
        return state

    # Out-of-scope: sabit template don, downstream'i atla
    state["final_response"] = OUT_OF_SCOPE_TEMPLATE
    state["draft_response"] = OUT_OF_SCOPE_TEMPLATE
    state["response_status"] = "out_of_scope"
    state["retrieved_docs"] = []
    state["retrieval_similarity_score"] = 0.0
    state["source_agreement"] = False
    state["evidence_confidence"] = "insufficient"
    state["active_model"] = "scope_classifier (gpt-oss-120b low)"

    audit_log(
        state,
        "scope_check_out_of_scope",
        reason=f"classifier: {raw_answer[:80]}",
    )

    return state
