"""
PaytarAI — Generator Node

Groq Llama 3.3 70B ile rol bazli yanit uretir (ucretsiz).
Retrieved docs'u context olarak kullanir.
"""

from langchain_openai import ChatOpenAI
from app.config import settings
from app.graph.prompts import get_system_prompt
from app.graph.audit import audit_log


CONTEXT_TEMPLATE_VET = """Asagida veteriner literaturunden alinan referans bilgiler bulunmaktadir.
Yanitini YALNIZCA bu kaynaklara dayanarak olustur. Kaynakta olmayan bilgiyi EKLEME.

ZORUNLU KURALLAR:
- Tum birimleri Turkiye standartlarina cevir: lb -> kg, gallon -> litre, oz -> mL, F -> C
- Kaynak referansi ekle (kitap adi, bolum)
- Turkce yaz

--- KAYNAKLAR (SADECE BU METINLERI KULLAN) ---
{sources}
--- KAYNAKLAR SONU ---

SON KONTROL: Yanit yazmadan once SPESIFIK iddia listeni (sayilar, isimler,
patogenez detaylari, protokol adimlari) yukaridaki KAYNAKLAR metinlerinden
DOGRUDAN veya yakin paraphrase olarak cikarilabildigini dogrula. Cikarilamayan
spesifik iddiayi YAZMA — yerine genel kategori ifadesi kullan veya o noktayi
atla. Genel klinik mantik, takip sorulari, sevk uyarisi kaynak gerekmez.

Kullanici sorusu: {question}"""


CONTEXT_TEMPLATE_PRODUCER = """Asagida arka planda kullanacagin referans bilgiler var. Bu kaynaklar yalnizca SENIN icin —
ciftciye bu kaynaklardan, kitap adlarindan, "[Kaynak 1]" gibi etiketlerden veya tablo numaralarindan
ASLA bahsetme. Yanitini bu kaynaklara dayandir ama metnin disardan bakildiginda
arka planda kaynak oldugunu HISSETTIRMESIN.

ZORUNLU KURALLAR:
- Tum birimleri Turkiye standartlarina cevir: lb -> kg, gallon -> litre, oz -> mL, F -> C
- Sade Turkce ile yaz, tablo kullanma
- Kaynak kelimesini bile yazma

--- KAYNAKLAR (sadece senin icin, SADECE BU METINLERI KULLAN) ---
{sources}
--- KAYNAKLAR SONU ---

SON KONTROL: Yanit yazmadan once SPESIFIK iddia listeni (sayilar, ilac/marka
adi, dozaj, satin alma yeri, belirli zaman/miktar adimlari) yukaridaki
KAYNAKLAR metinlerinden DOGRUDAN cikarilabildigini dogrula. Cikarilamayan
spesifik iddiayi YAZMA — yerine genel kategori ifadesi kullan ("veterinerin
uygun gordugu tedavi", "veterinerin onerdigi miktarda") veya o noktayi atla.
Genel oneri, kategori adi, tehlike isareti, gozlem talimati, hijyen onerisi
kaynak gerekmez.

Ciftcinin sorusu: {question}"""


def generator_node(state: dict) -> dict:
    """
    Generator node — Groq Llama 3.3 70B ile yanit uretir (ucretsiz).

    Retrieved docs'u context olarak kullanir.
    Critic reddettiyse, red gerekceleriyle birlikte yeniden uretir.
    """
    messages = state.get("messages", [])
    retrieved_docs = state.get("retrieved_docs", [])
    user_role = state.get("user_role", "producer")

    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break

    if not last_user_msg:
        state["draft_response"] = "Soru anlasilamadi."
        state["response_status"] = "error"
        return state

    # Kaynak metinleri birlestir — LLM'in kopyalamamasi icin "[Kaynak N]" etiketi YOK
    if retrieved_docs:
        sources_text = "\n\n".join(
            f"=== Referans {i+1} ===\n"
            f"Kitap: {doc['metadata'].get('source_title', 'Bilinmeyen')}\n"
            f"Iliskili Skor: {doc['score']:.2f}\n"
            f"Metin:\n{doc['text']}"
            for i, doc in enumerate(retrieved_docs[:5])
        )
    else:
        sources_text = "Hicbir kaynak bulunamadi."

    # Critic red gerekceleri varsa ekle
    rejection_context = ""
    rejection_reasons = state.get("critic_rejection_reasons", [])
    if rejection_reasons:
        rejection_context = (
            "\n\nONCEKI YANITIM REDDEDILDI. Reddi dikkate al:\n"
            + "\n".join(f"- {r}" for r in rejection_reasons)
            + "\nYukardaki sorunlari gidererek yeniden cevapla."
        )

    # Context prompt — rol bazli sablon
    template = CONTEXT_TEMPLATE_VET if user_role == "veterinarian" else CONTEXT_TEMPLATE_PRODUCER
    context_msg = template.format(
        sources=sources_text,
        question=last_user_msg + rejection_context,
    )

    # System prompt
    system_prompt = get_system_prompt(user_role)

    try:
        llm = ChatOpenAI(
            api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            model="gpt-oss-120b",
            temperature=0,
            max_tokens=3000,
            reasoning_effort="medium",  # type: ignore[call-arg]
        )

        # 429 rate-limit icin 2 deneme — Groq error message'inda "try again in Xs" yazar
        import re as _re
        import time as _time
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = llm.invoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_msg},
                ])
                break
            except Exception as rate_err:
                msg = str(rate_err)
                if "rate_limit" not in msg.lower() and "429" not in msg:
                    raise
                if attempt >= max_retries:
                    raise
                wait_match = _re.search(r"try again in ([\d.]+)s", msg)
                wait_s = float(wait_match.group(1)) + 2.0 if wait_match else 15.0
                print(f"[Generator] Rate limit, {wait_s:.1f}s bekle ve tekrar dene ({attempt+1}/{max_retries})")
                _time.sleep(wait_s)

        draft = str(response.content).strip()

        # Reasoning model bazen content bos birakar, cevabi reasoning_content'e koyar — fallback
        if len(draft) < 10:
            reasoning = response.additional_kwargs.get("reasoning_content", "")
            if reasoning and len(reasoning) > 20:
                lines = [l.strip() for l in reasoning.strip().splitlines() if l.strip()]
                draft = "\n".join(lines[-30:]) if lines else draft

        state["draft_response"] = draft
        state["active_model"] = "gpt-oss-120b (medium reasoning) @ Cerebras"
        state["response_status"] = "ok"

        audit_log(
            state,
            "generator_done",
            reason=f"role={user_role}, sources={len(retrieved_docs)}, attempt={state.get('critic_attempts', 0) + 1}",
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback — kaynak metni dogrudan sun
        state["draft_response"] = _build_fallback(retrieved_docs, user_role)
        state["response_status"] = "fallback"
        state["active_model"] = "fallback"
        audit_log(state, "generator_error", reason=str(e))

    return state


def _build_fallback(docs: list[dict], role: str) -> str:
    """
    LLM cagirisi basarisiz olursa guvenli fallback.

    GUVENLIK: Uretici icin asla raw chunk metnini dokmeyiz — orada Latince/Ingilizce
    terimler, dozajlar, recete adlari olabilir. Sadece "sistem yogun, tekrar dene" mesaji.
    """
    if role == "producer":
        return (
            "Sistemde geçici bir yoğunluk var, sorunuza şu an yanıt veremedim. "
            "Lütfen birkaç dakika sonra tekrar deneyin.\n\n"
            "⚠️ Acil bir durumsa bekleme — doğrudan veteriner hekiminize ulaşın."
        )

    # Vet icin de raw chunk vermek riskli ama daha az — yine de minimal tutalim
    if not docs:
        return "Bu konuda guvenilir literatur verisi dogrulanamadi. Lutfen baska bir kaynaga danisin."
    return (
        "Sistemde geçici bir yoğunluk nedeniyle yanıt üretilemedi. "
        f"Top retrieval skoru: {docs[0]['score']:.2f}. "
        "Lütfen birkaç dakika sonra tekrar deneyin."
    )
