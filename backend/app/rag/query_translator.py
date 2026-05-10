"""
PaytarAI — Query Translation (Dual Language Search)

Kullanici sorgusunu hem Turkce hem Ingilizce olarak arar.
Groq (ucretsiz) ile ceviri yapar.
"""

from langchain_groq import ChatGroq
from app.config import settings


TRANSLATE_PROMPT = """You are a veterinary medicine translator. Translate the following
veterinary/cattle healthcare query from {source_lang} to {target_lang}.

CRITICAL RULES:
- This is about CATTLE/BOVINE veterinary medicine
- Translate medical terms accurately using standard veterinary terminology
- "süt humması" = "milk fever" or "parturient hypocalcemia" (NOT paronychia)
- "ketozis/ketosis" = "ketosis" or "acetonemia"
- "şişme/timpani" = "bloat" or "ruminal tympany"
- "meme iltihabı/mastit" = "mastitis"
- "ayak hastalığı" = "foot rot" or "digital dermatitis"
- Output ONLY the translation, nothing else

Query: {query}

Translation:"""


def translate_query(query: str, target_lang: str = "English") -> str | None:
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
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=200,
        )

        prompt = TRANSLATE_PROMPT.format(
            query=query,
            target_lang=target_lang,
            source_lang=source_lang,
        )
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
