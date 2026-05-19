"""
PaytarAI — Query Translation (Dual Language Search)

Kullanici sorgusunu hem Turkce hem Ingilizce olarak arar.
Groq (ucretsiz) ile ceviri yapar.
"""

from langchain_openai import ChatOpenAI
from app.config import settings


ENRICHMENT_PROMPT = """Sen uzman bir BÜYÜKBAŞ (Sığır / İnek / Buzağı) veteriner hekimisin. 
Kullanıcı aksi belirtmedikçe sorunun bir inek/sığır hakkında olduğunu varsay.
Aşağıdaki kullanıcı sorusunu analiz et ve bu durumla ilgili büyükbaşlarda en sık görülen hastalıkları (örneğin yere düşüp kalkamama durumunda Süt Humması/Hypocalcemia, Downer Cow Sendromu vb.), semptomları ve tıbbi terimleri anahtar kelimeler halinde yaz.
Hem Türkçe hem de İngilizce (yaygın veteriner terminolojisi) terimleri kullan.

Kullanıcı Sorusu: {query}

KURALLAR:
- Cümle kurma. Sadece anahtar kelimeleri virgülle ayırarak yaz.
- Soru çok kısaysa (örn: "öksürük"), ona eşlik edebilecek diğer hastalıkları/belirtileri de (pnömoni, ateş, solunum) ekle.

Örnek Çıktı:
öksürük, pnömoni, solunum yolu enfeksiyonu, akciğer, ateş, antibiyotik, respiratory disease, pneumonia

Anahtar Kelimeler:"""


def enrich_query(query: str) -> str | None:
    """
    Sorguyu hedef dile cevirir (Groq/Llama ile, ucretsiz).

    Args:
        query: Orijinal sorgu
        target_lang: Hedef dil ("English" veya "Turkish")

    Returns:
        Cevrilmis metin veya None (hata durumunda)
    """
    try:
        llm = ChatOpenAI(
            api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            model="gpt-oss-120b",
            temperature=0,
            max_tokens=800,
            reasoning_effort="medium",  # type: ignore[call-arg]
        )

        prompt = ENRICHMENT_PROMPT.format(query=query)

        # Rate limit retry
        import re as _re
        import time as _time
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = llm.invoke(prompt)
                break
            except Exception as rate_err:
                msg = str(rate_err)
                if "rate_limit" not in msg.lower() and "429" not in msg:
                    raise
                if attempt >= max_retries:
                    raise
                wait_match = _re.search(r"try again in ([\d.]+)s", msg)
                wait_s = float(wait_match.group(1)) + 2.0 if wait_match else 10.0
                print(f"[enrich_query] Rate limit, {wait_s:.1f}s bekle ({attempt+1}/{max_retries})")
                _time.sleep(wait_s)

        translated = str(response.content).strip()

        # Reasoning model fallback — content bos olabilir
        if len(translated) < 5:
            reasoning = response.additional_kwargs.get("reasoning_content", "")
            if reasoning and len(reasoning) > 10:
                lines = [l.strip() for l in reasoning.strip().splitlines() if l.strip()]
                translated = lines[-1] if lines else ""

        if len(translated) < 5:
            return None

        return translated

    except Exception as e:
        print("TRANSLATOR ERROR:", str(e))
        return None


def detect_language(text: str) -> str:
    """Basit dil tespiti — Turkce karakterler varsa 'tr', yoksa 'en'."""
    turkish_chars = set("çğıöşüÇĞİÖŞÜ")
    turkish_words = {"bir", "ve", "icin", "ile", "nasil", "nedir", "hayvan",
                     "inek", "tedavi", "ilac", "veteriner", "hastali",
                     "hummasi", "sut", "meme", "dogum", "ates", "ishal"}

    has_tr_chars = any(c in turkish_chars for c in text)
    words = set(text.lower().split())
    has_tr_words = len(words & turkish_words) >= 1

    if has_tr_chars or has_tr_words:
        return "tr"
    return "en"
