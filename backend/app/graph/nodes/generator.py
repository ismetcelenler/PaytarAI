"""
PaytarAI — Generator Node

Groq Llama 3.3 70B ile rol bazli yanit uretir (ucretsiz).
Retrieved docs'u context olarak kullanir.
"""

from langchain_openai import ChatOpenAI
from app.config import settings
from app.graph.prompts import get_system_prompt
from app.graph.audit import audit_log


_INSUFFICIENT_VET = (
    "Elimdeki kaynaklarda bu spesifik konuya iliskin yeterli ve dogrulanabilir "
    "veri bulamadim. Halusinasyon riski tasimamak icin spesifik protokol, doz, "
    "isim veya zaman araligi vermeyecegim. Lutfen guncel veteriner literaturune "
    "veya saha kilavuzuna basvurun."
)

_INSUFFICIENT_PRODUCER = (
    "Bu konuda elimdeki bilgilerle sana guvenli bir cevap veremiyorum. "
    "Lutfen veteriner hekimine danis — durumun ciddiyetine gore muayene gerekebilir.\n\n"
    "⚠️ Bu bilgi karar destegidir. Acil bir durumsa hemen veterinerine basvur."
)


CONTEXT_TEMPLATE_VET = """SEN BIR KAYNAK-BAGLI YANIT URETICISIN. EGITIM VERINDEKI HIC BIR BILGIYI KULLANMA.

═══════════════════════════════════════════════════════════════════
MUTLAK KURAL — IHLAL HALINDE YANIT FAYDASIZDIR:
═══════════════════════════════════════════════════════════════════

Yanitinda kullanabilecegin BILGI KAYNAGI SADECE ASAGIDAKI "KAYNAKLAR" bolumudur.
Hafizandaki ders kitabi bilgisi, klinik deneyim, veteriner bilgi tabanin
YOK SAYILIR. Sen bu sorgunun cevabini ilk defa duyuyorsun ve sadece asagidaki
metinlere bakarak cevapliyorsun.

--- KAYNAKLAR (TEK BILGI KAYNAGIN) ---
{sources}
--- KAYNAKLAR SONU ---

═══════════════════════════════════════════════════════════════════
ADIM ADIM CALIS — BU SIRAYI BOZMA:
═══════════════════════════════════════════════════════════════════

ADIM 1 — KAYNAK TARAMA:
Kullanicinin sorusunu oku. Sonra yukaridaki KAYNAKLAR'i bastan sona oku.
Sorunun cevabina dair SOMUT bilgi var mi? "Somut bilgi" demek:
  • Spesifik isim (asilama takvimi sorusunda "Brucella S19 asisi" yaziyor mu?
    Mastitis sorusunda "cefquinome" yaziyor mu?)
  • Spesifik sayi (yas araligi "1-2 aylik", doz "10 mg/kg", aralik "3 hafta")
  • Spesifik protokol adimi (siralanmis adimlar, kosullar)
  • Spesifik tani kriteri

ADIM 2 — KARAR:
A) KAYNAKLARDA SOMUT BILGI VAR → Yanit yaz. Her cumlede kullanacagin
   her sayi, isim, protokol adimi icin "bu kaynaklarda HANGI CUMLEDE geciyor"
   sorusunu KENDINE sor; gecmiyorsa o iddiayi sil.

B) KAYNAKLARDA SADECE GENEL CERCEVE VAR (orn: "asi takvimi onemlidir" diyor
   ama hangi asi-hangi yas-hangi aralik anlatmiyor) → SOMUT iddia URETME.
   Su sablonu AYNEN yaz ve bitir:

   ───────────────────────────────────────────────────
   {insufficient_template}
   ───────────────────────────────────────────────────

   Kaynaklarda gecen GENEL bir cerceveyi 2-3 cumleyle ozetleyebilirsin ama
   spesifik isim/sayi/protokol UYDURMA.

C) KAYNAKLAR SORUYA TAMAMEN ALAKASIZ → B sablonunu kullan.

═══════════════════════════════════════════════════════════════════
KESIN YASAK — IHLAL HALINDE CRITIC REDDEDER:
═══════════════════════════════════════════════════════════════════

✗ Kaynaklarda gecmeyen ASI/ILAC ADI yazma (Brucella S19, Theileria, IBR, PI3,
  BVD, BRSV, J-5, Pasteurella, Mannheimia, klostridial vb. — KAYNAK METNINDE
  bu kelimeyi GORMUYORSAN YAZMA)
✗ Kaynaklarda gecmeyen YAS ARALIGI yazma (1-2 aylik, 3-6 aylik, 9-12 aylik vb.)
✗ Kaynaklarda gecmeyen SURE/ARALIK yazma (3 hafta arayla, 6 ayda bir, yilda 1 doz vb.)
✗ Kaynaklarda gecmeyen DOZ yazma (mg/kg, ml/kg, IV/IM/SC enjeksiyon)
✗ Kaynaklarda gecmeyen TARIH/MEVSIM yazma (Mart-Nisan, kene mevsimi vb.)
✗ Egitim verisinden "standart bilgi" ekleme — bu sistem TEZ icin gelistirildi,
  egitim verisi degil sadece RAG kaynaklari muhasebe edilir.

═══════════════════════════════════════════════════════════════════
KAYNAK KULLANIRKEN:
═══════════════════════════════════════════════════════════════════

• Birim donusumu: lb→kg, gallon→litre, oz→mL, F→C
• Yanitin SONUNDA tek satir: "Kaynak: [Kitap Adi], ilgili bolum"
• Inline [Kaynak N] etiketleri YASAK
• Turkce yaz
• Yanit 6 paragrafi gecmesin

KULLANICI SORUSU:
{question}

SIMDI ADIM 1'i UYGULA: Once KAYNAKLAR'i tara, sonra ADIM 2'deki A/B/C karari ver."""


CONTEXT_TEMPLATE_PRODUCER = """SEN BIR KAYNAK-BAGLI YANIT URETICISIN. EGITIM VERINDEKI HIC BIR BILGIYI KULLANMA.

═══════════════════════════════════════════════════════════════════
MUTLAK KURAL — IHLAL HALINDE YANIT FAYDASIZDIR:
═══════════════════════════════════════════════════════════════════

Yanitinda kullanabilecegin BILGI KAYNAGI SADECE ASAGIDAKI "KAYNAKLAR" bolumudur.
Bunlar ARKA PLAN bilgisi — ciftciye kaynaklardan, kitap adlarindan,
"[Kaynak N]" etiketlerinden BAHSETME, ama yanitin bu metinlere dayanmali.

--- KAYNAKLAR (TEK BILGI KAYNAGIN, ciftciye gostermeyeceksin) ---
{sources}
--- KAYNAKLAR SONU ---

═══════════════════════════════════════════════════════════════════
ADIM ADIM CALIS:
═══════════════════════════════════════════════════════════════════

ADIM 1 — KAYNAK TARAMA: Soruyu oku. KAYNAKLAR'da SOMUT bilgi var mi?
  • Spesifik miktar/sure/sicaklik
  • Spesifik urun/marka/ilac kategorisi
  • Spesifik protokol adimi

ADIM 2 — KARAR:
A) SOMUT BILGI VAR → Sade Turkce ile aktar.
B) SADECE GENEL CERCEVE VAR (somut detay yok) → SOMUT iddia URETME. Su sablonu
   AYNEN yaz ve bitir:

   ───────────────────────────────────────────────────
   {insufficient_template}
   ───────────────────────────────────────────────────

C) KAYNAK SORUYA ALAKASIZ → B sablonunu kullan.

═══════════════════════════════════════════════════════════════════
KESIN YASAK:
═══════════════════════════════════════════════════════════════════

✗ Kaynaklarda gecmeyen miktar/sure/sicaklik UYDURMA
  (orn: "2 saatte bir 500 mL" — kaynakta yoksa YAZMA)
✗ Kaynaklarda gecmeyen urun/marka ismi UYDURMA
✗ Egitim verisinden "halk dilinde boyle yapilir" diye standart ekleme
✗ "Kaynak", "kitap", "[Kaynak 1]" gibi etiketler YAZMA
✗ Receteli ilac adi + doz YAZMA (vet karari)
✗ Markdown tablo KULLANMA

═══════════════════════════════════════════════════════════════════
KAYNAK YETERLIYSE:
═══════════════════════════════════════════════════════════════════

• Birim donusumu: lb→kg, gallon→litre, oz→mL, F→C
• Sade Turkce, Latince/teknik terim yok
• 3-5 maddeli numarali liste + tehlike isaretleri + disclaimer

CIFTCININ SORUSU:
{question}

SIMDI ADIM 1'i UYGULA: Once KAYNAKLAR'i tara, sonra ADIM 2'deki A/B/C karari ver."""


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
