"""
PaytarAI — Generator Node

Groq Llama 3.3 70B ile rol bazli yanit uretir (ucretsiz).
Retrieved docs'u context olarak kullanir.
"""

import time

from langchain_openai import ChatOpenAI
from app.config import settings
from app.graph.prompts import get_system_prompt
from app.graph.audit import audit_log
from app.graph.debug_trace import trace_node, trim_text


CONTEXT_TEMPLATE_VET = """SEN BIR KAYNAK-BAGLI YANIT URETICISIN.

═══════════════════════════════════════════════════════════════════
KAYNAK BAGLILIK KURALI:
═══════════════════════════════════════════════════════════════════

Yanitindaki HER SPESIFIK IDDIA (sayi, isim, dozaj, protokol, tani kriteri,
patogenez detayi) ASAGIDAKI KAYNAKLAR'da dogrudan veya yakin paraphrase
olarak GECMELI. Hafizandan ders kitabi bilgisi EKLEME — bu sistem TEZ
calismasi icin gelistirildi, sadece RAG kaynaklari muhasebe edilir.

NASIL CALIS:
• Soruya odakli oku → kaynaklarda hangi cumleler/paragraflar ilgili?
• Sadece KAYNAKLARDAN cikan bilgileri kullan
• Yanitini KAYNAKLARDA OLAN seyler kadar uzun yap; chunk az bilgi veriyorsa
  yanit kisa olsun (1-2 paragraf). Cok varsa daha detayli (4-5 paragraf).
• KAYNAKLARDA OLMAYAN spesifik iddialar (yas araligi, ilac adi, doz, sure)
  ASLA YAZMA — bu yanit grounding filter'dan gecemez, silinir
• Genel sevk uyarisi ("veteriner cagirin", "vakti acil"), gozlem talimati
  ("ates olc", "dışkıya bak"), takip sorusu — bunlar kaynak gerektirmez

--- KAYNAKLAR ---
{sources}
--- KAYNAKLAR SONU ---

═══════════════════════════════════════════════════════════════════
PARAFRAZ YASAGI — Tip terimi, prosedur adi, sayisal iddia
═══════════════════════════════════════════════════════════════════

PRENSIP:
Kaynakta gecen ANATOMIK ORGAN, PROSEDUR ADI ve SAYISAL IDDIA'larda
SADECE kaynaktaki KELIMENIN KENDISINI kullan. Esanlamli sandigin terimi
KOYMA — tipta kelime degisikligi anlam degisikligidir.

OLCU (kendine sor):
Bir cumle yazdiktan sonra: "Bu cumledeki organ/prosedur/sayi kelimeleri,
kaynakta TAM olarak geciyor mu? Yoksa ben mi 'ayni sey' diye degistirdim?"
Supheli durumda ASLA degistirme, kaynaktaki kelimeyi kopyala.

ORNEK (dogru cevap):
Kaynak: "transpariyetal ponksiyon (karindan igne) ile pH olcumu"
DOGRU:  "transpariyetal ponksiyon ile pH olcumu"
YANLIS: "rektal ponksiyon ile pH olcumu"   ← prosedur terimi DEGISTI
YANLIS: "igne ile pH olcumu (transpariyetal yontem)"  ← yeniden cerceveleme

ESANLAMLI PARANTEZ YASAGI:
"sirden (iskembe)" veya "rumen (iskembe)" tipi parantezler — bunlar
FARKLI organlardir, parantez icinde "ayniymis gibi" gostermek YASAK.
Kaynakta hangisi geciyorsa SADECE onu yaz.

SAYISAL IDDIANIN ANLAMI:
Bir sayi kullanacaksan, sayinin NEYE AIT oldugunu chunk'tan kelimesi
kelimesine kopyala.
ORNEK: Kaynakta "vakalarin %90'i sol kayma seklindedir" yaziyorsa,
DOGRU yazim:  "vakalarin %90'i sol kayma seklindedir"
YANLIS yazim: "%90 cerrahi basari saglanir"  ← sayinin anlami CARPITILDI

═══════════════════════════════════════════════════════════════════
KESIN YASAK:
═══════════════════════════════════════════════════════════════════
✗ Kaynaklarda gecmeyen ASI/ILAC ADI (Brucella S19, Theileria, IBR vb.)
✗ Kaynaklarda gecmeyen YAS ARALIGI, SURE, DOZ
✗ Egitiminden "standart bilgi" ekleme
✗ Inline [Kaynak N] etiketleri
✗ Esanlamli parantez "sirden (iskembe)"
✗ Sayi anlam carpitmasi (%90 cerrahi basari vb.)

═══════════════════════════════════════════════════════════════════
GUVENLIK ZORUNLULUKLARI (her yanitta uy):
═══════════════════════════════════════════════════════════════════
✓ Yanitin SONUNDA mutlaka iki satir bulunmali:
  - "Kaynak: [Kitap Adi], ilgili bolum"
  - "⚠️ Bu bilgi karar destegidir; klinik karar yetkisi sizdedir."
✓ Eger soruda "exitus", "ölüm", "akut kollaps", "soluyamiyor", "ciddi
  hemoraji" tipi ACIL belirtiler varsa, yaniti "ACIL SEVK GEREKLI"
  uyarisiyla basla, sonra protokolu ver

YAZIM KURALLARI:
• Birim donusumu: lb→kg, gallon→litre, oz→mL, F→C
• Turkce yaz, yanit 6 paragrafi gecmesin

KULLANICI SORUSU:
{question}"""


CONTEXT_TEMPLATE_PRODUCER = """SEN BIR KAYNAK-BAGLI YANIT URETICISIN.

═══════════════════════════════════════════════════════════════════
KAYNAK BAGLILIK KURALI:
═══════════════════════════════════════════════════════════════════

Yanitindaki HER SPESIFIK IDDIA (miktar, sure, sicaklik, urun adi, protokol
adimi) ASAGIDAKI KAYNAKLAR'da dogrudan veya yakin paraphrase olarak GECMELI.
Hafizandan "standart halk bilgisi" EKLEME.

NASIL CALIS:
• Soruya odakli oku → kaynaklarda hangi paragraflar ilgili?
• Sade Turkce ile, ciftciye anlasilir sekilde anlat
• Yanitini KAYNAKLARDA OLAN seyler kadar uzun yap (1-5 madde)
• KAYNAKLARDA OLMAYAN spesifik miktar/sure UYDURMA — grounding filter siler
• Genel sevk ("veterinere git"), tehlike isareti ("ates 40'i gecerse"),
  gozlem ("dışkıyı izle"), disclaimer — bunlar kaynak gerektirmez

--- KAYNAKLAR (ciftciye gostermeyeceksin, arka plan bilgisi) ---
{sources}
--- KAYNAKLAR SONU ---

═══════════════════════════════════════════════════════════════════
PARAFRAZ YASAGI — Tip terimi, prosedur adi, sayisal iddia
═══════════════════════════════════════════════════════════════════

PRENSIP:
Kaynakta gecen ANATOMIK ORGAN, PROSEDUR ADI ve SAYISAL IDDIA'larda
SADECE kaynaktaki KELIMENIN KENDISINI kullan. Esanlamli sandigin terimi
KOYMA — tipta kelime degisikligi anlam degisikligidir.

OLCU (kendine sor):
Bir cumle yazdiktan sonra: "Bu cumledeki organ/prosedur/sayi kelimeleri,
kaynakta TAM olarak geciyor mu? Yoksa ben mi 'ayni sey' diye degistirdim?"
Supheli durumda ASLA degistirme, kaynaktaki kelimeyi kopyala.

ORNEK (dogru cevap):
Kaynak: "transpariyetal ponksiyon (karindan igne) ile pH olcumu"
DOGRU:  "transpariyetal ponksiyon ile pH olcumu"
YANLIS: "rektal ponksiyon ile pH olcumu"   ← prosedur terimi DEGISTI

ESANLAMLI PARANTEZ YASAGI:
"sirden (iskembe)" veya "rumen (iskembe)" tipi parantezler — bunlar
FARKLI organlardir, parantez icinde "ayniymis gibi" gostermek YASAK.
Kaynakta hangisi geciyorsa SADECE onu yaz.

NOT (ciftci modu istisnasi):
Latince/bilimsel terimleri (mesela "ketozis", "hipokalsemi") ciftciye
aciklamak icin parantez kullanmak SERBESTTIR — bu paraphrase degil,
ceviridir:
ORNEK: "ketozis (kan sekerinin dusmesi)" — OK
ORNEK: "hipokalsemi (kalsiyum eksikligi)" — OK
ORNEK: "sirden (iskembe)" — YASAK, farkli organlar

SAYISAL IDDIANIN ANLAMI:
Bir sayi kullanacaksan, sayinin NEYE AIT oldugunu chunk'tan kelimesi
kelimesine al. Sayinin anlamini cevirme/yorumlamaya KALKMA.

═══════════════════════════════════════════════════════════════════
KESIN YASAK:
═══════════════════════════════════════════════════════════════════
✗ Kaynaklarda gecmeyen miktar/sure/sicaklik
✗ Kaynaklarda gecmeyen urun/marka ismi
✗ Egitim verisinden "halk dilinde boyle yapilir" ekleme
✗ "Kaynak", "[Kaynak 1]" etiketleri
✗ Receteli ilac adi + doz (vet karari)
✗ Markdown tablo
✗ Esanlamli organ parantezi "sirden (iskembe)"
✗ Sayi anlam carpitmasi

═══════════════════════════════════════════════════════════════════
GUVENLIK ZORUNLULUKLARI (her yanitta uy):
═══════════════════════════════════════════════════════════════════
✓ Yanitin SONUNA mutlaka "⚠️ Bu bilgi karar destegidir." satirini ekle
✓ Sade Turkce yaz — yabanci/Latince terim varsa parantez icinde acikla
✓ Eger kullanici "olum tehlikesi", "kan", "soluyamiyor", "hareketsiz",
  "yere yatti kalkmiyor" tipi ACIL belirtiler bildirmisse, yaniti
  "DERHAL VETERINER HEKIMINIZE BASVURUN" ile basla
✓ 3-5 maddeli liste + tehlike isaretleri

YAZIM KURALLARI:
• Birim donusumu: lb→kg, gallon→litre, oz→mL, F→C

CIFTCININ SORUSU:
{question}"""


def generator_node(state: dict) -> dict:
    """
    Generator node — Cerebras gpt-oss-120b ile yanit uretir.

    Retrieved docs'u context olarak kullanir.
    Critic reddettiyse, red gerekceleriyle birlikte yeniden uretir.
    """
    t0 = time.perf_counter()
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

    # Context prompt — rol bazli sablon (yeni yumusatilmis pattern; B karari
    # ve _INSUFFICIENT_* sablonlari kaldirildi cunku sentence_grounding_node
    # cumle-cumle filtreleme yapacak; generator B'ye dusup yanit kestirmesin).
    template = CONTEXT_TEMPLATE_VET if user_role == "veterinarian" else CONTEXT_TEMPLATE_PRODUCER

    context_msg = template.format(
        sources=sources_text,
        question=last_user_msg + rejection_context,
    )

    # System prompt
    system_prompt = get_system_prompt(user_role)

    try:
        # GROUNDING-FIRST KONFIGURASYONU:
        # - temperature=0: deterministik
        # - top_p=0.05: nucleus sampling cok dar — egitim hafizasindan rastgele
        #   "ders kitabi" bilgisi sizmasini onler
        # - reasoning_effort="medium": ADIM 1/2 checklist'i isletmek icin
        # OpenRouter gpt-oss-120b (paid tier — $5 credit aktif).
        llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="openai/gpt-oss-120b",
            temperature=0,
            top_p=0.05,
            max_tokens=3000,
            reasoning_effort="medium",  # type: ignore[call-arg]
            default_headers={
                "HTTP-Referer": "https://github.com/paytar-ai",
                "X-Title": "PaytarAI",
            },
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
        state["active_model"] = "gpt-oss-120b @ OpenRouter (medium reasoning)"
        state["response_status"] = "ok"

        attempt_num = state.get("critic_attempts", 0) + 1
        audit_log(
            state,
            "generator_done",
            reason=f"role={user_role}, sources={len(retrieved_docs)}, attempt={attempt_num}",
        )

        trace_node(
            state, "generator",
            input={
                "user_role": user_role,
                "user_message": last_user_msg,
                "system_prompt": trim_text(system_prompt, 1500),
                "context_msg": trim_text(context_msg, 3000),
                "sources_count": len(retrieved_docs),
                "attempt": attempt_num,
                "rejection_reasons": rejection_reasons,
            },
            output={
                "raw_response": trim_text(draft, 4000),
                "char_count": len(draft),
                "model": "gpt-oss-120b @ Cerebras",
                "temperature": 0,
                "top_p": 0.05,
                "reasoning_effort": "medium",
            },
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        state["draft_response"] = _build_fallback(retrieved_docs, user_role)
        state["response_status"] = "fallback"
        state["active_model"] = "fallback"
        audit_log(state, "generator_error", reason=str(e))

        trace_node(
            state, "generator",
            input={
                "user_role": user_role,
                "user_message": last_user_msg,
                "context_msg": trim_text(context_msg, 1500),
                "sources_count": len(retrieved_docs),
            },
            output={"error": str(e)[:300], "fallback_used": True},
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

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
