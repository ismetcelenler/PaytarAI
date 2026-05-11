"""
PaytarAI — Query Translation (Dual Language Search)

Kullanici sorgusunu hem Turkce hem Ingilizce olarak arar.
Groq (ucretsiz) ile ceviri yapar.
"""

from langchain_groq import ChatGroq
from app.config import settings


ENRICHMENT_PROMPT = """Sen uzman bir veteriner hekimsin. Aşağıdaki kullanıcı sorusunu analiz et ve bu durumla ilgili olası hastalıkları, semptomları ve klinik tedavi terimlerini anahtar kelimeler halinde yaz.
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
    source_lang = "Turkish" if detect_language(query) == "tr" else "English"

    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model="openai/gpt-oss-120b",
            temperature=0,
            max_tokens=200,
        )

        prompt = ENRICHMENT_PROMPT.format(query=query)
        response = llm.invoke(prompt)
        translated = response.content.strip()

        # Cok kisa veya bos donerse None
        if len(translated) < 5:
            return None

        return translated

    except Exception:
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
