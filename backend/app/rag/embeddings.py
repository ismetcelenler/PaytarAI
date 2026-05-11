"""
PaytarAI — OpenAI Embeddings Wrapper

text-embedding-3-small modeli ile vektör olusturma.
"""

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


def get_openai_client() -> OpenAI:
    """OpenAI client singleton."""
    global _client
    if _client is None:
        key = settings.openai_api_key
        if not key:
            import os
            key = os.environ.get("OPENAI_API_KEY", "")
        _client = OpenAI(api_key=key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Metin listesini embedding vektorlerine donusturur.

    Args:
        texts: Metin listesi

    Returns:
        Her metin icin embedding vektoru listesi
    """
    if not texts:
        return []

    client = get_openai_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def embed_single(text: str) -> list[float]:
    """Tek bir metni embedding vektorune donusturur."""
    result = embed_texts([text])
    return result[0] if result else []
