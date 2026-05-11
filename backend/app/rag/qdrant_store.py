"""
PaytarAI — Qdrant Collection Manager

Qdrant Cloud'da koleksiyon olusturma, vektör yukleme ve arama.
AI-PROMPT.md Section 3.3: Hybrid search (dense + sparse).
"""

import uuid
from qdrant_client import QdrantClient, models

from app.config import settings
from app.rag.embeddings import EMBEDDING_DIMENSION

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Qdrant client singleton."""
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    return _client


def ensure_collection(collection_name: str | None = None) -> str:
    """
    Koleksiyonun var oldugundan emin ol, yoksa olustur.

    Returns:
        Koleksiyon adi
    """
    name = collection_name or settings.qdrant_collection_name
    client = get_qdrant_client()

    existing = [c.name for c in client.get_collections().collections]
    if name in existing:
        print(f"[Qdrant] Koleksiyon mevcut: {name}")
        return name

    client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(
            size=EMBEDDING_DIMENSION,
            distance=models.Distance.COSINE,
        ),
    )
    print(f"[Qdrant] Koleksiyon olusturuldu: {name}")
    return name


def upsert_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    metadata_list: list[dict],
    collection_name: str | None = None,
) -> int:
    """
    Chunk'lari embedding ve metadata ile Qdrant'a yukler.

    Args:
        chunks: Metin chunk listesi
        embeddings: Her chunk icin embedding vektoru
        metadata_list: Her chunk icin metadata dict'i
        collection_name: Koleksiyon adi

    Returns:
        Yuklenen nokta sayisi
    """
    name = collection_name or settings.qdrant_collection_name
    client = get_qdrant_client()

    points = []
    for i, (chunk, embedding, meta) in enumerate(zip(chunks, embeddings, metadata_list)):
        payload = {
            **meta,
            "text": chunk,
            "chunk_index": i,
        }
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload,
            )
        )

    # Batch upsert (100'lu gruplar halinde)
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=name, points=batch)

    print(f"[Qdrant] {len(points)} chunk yuklendi -> {name}")
    return len(points)


def search(
    query_vector: list[float],
    limit: int = 5,
    score_threshold: float = 0.5,
    filters: dict | None = None,
    collection_name: str | None = None,
) -> list[dict]:
    """
    Vektör arama yapar.

    Args:
        query_vector: Sorgu embedding vektoru
        limit: Maksimum sonuc sayisi
        score_threshold: Minimum skor
        filters: Qdrant payload filtreleri
        collection_name: Koleksiyon adi

    Returns:
        Sonuc listesi [{score, text, metadata}]
    """
    name = collection_name or settings.qdrant_collection_name
    client = get_qdrant_client()

    # Filtre olustur
    qdrant_filter = None
    if filters:
        must_conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=value),
                    )
                )
            elif isinstance(value, bool):
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )
            else:
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )
        qdrant_filter = models.Filter(must=must_conditions)

    results = client.query_points(
        collection_name=name,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=limit,
        score_threshold=score_threshold,
    )

    return [
        {
            "score": point.score,
            "text": point.payload.get("parent_text", point.payload.get("text", "")),
            "metadata": {
                k: v for k, v in point.payload.items() if k not in ("text", "parent_text")
            },
        }
        for point in results.points
    ]


def get_collection_info(collection_name: str | None = None) -> dict:
    """Koleksiyon bilgilerini dondurur."""
    name = collection_name or settings.qdrant_collection_name
    client = get_qdrant_client()
    info = client.get_collection(name)
    return {
        "name": name,
        "points_count": info.points_count,
        "status": info.status.value,
    }
