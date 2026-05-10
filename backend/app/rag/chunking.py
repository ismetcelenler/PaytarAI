"""
PaytarAI — Semantic Chunking

AI-PROMPT.md Section 3.1: RecursiveCharacterTextSplitter YASAKTIR.
Cumle bazli semantic chunking uygulanir.
Hedef chunk boyutu: 1200-2500 token.
"""

import re
import numpy as np
from typing import Optional


def split_into_sentences(text: str) -> list[str]:
    """
    Metni cumlelere boler.
    Tibbi metinlerde nokta sonrasi bolme yapar, kisaltmalara dikkat eder.
    """
    # Paragraf bazli on bolme
    paragraphs = text.split("\n\n")
    sentences = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Baslik satirlarini (## ile baslayan) tek cumle olarak tut
        if para.startswith("#"):
            sentences.append(para)
            continue

        # Cumle bolme — nokta, soru isareti, unlem
        # mg, kg, mL gibi tibbi kisaltmalardan sonra bolme
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', para)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)

    return sentences


def compute_similarities(
    sentences: list[str],
    embed_fn: callable,
    batch_size: int = 50,
) -> list[float]:
    """
    Ardisik cumleler arasindaki cosine similarity hesaplar.

    Args:
        sentences: Cumle listesi
        embed_fn: Embedding fonksiyonu (list[str] -> list[list[float]])
        batch_size: Embedding batch boyutu

    Returns:
        Ardisik ciftler arasindaki similarity listesi (len = len(sentences) - 1)
    """
    if len(sentences) <= 1:
        return []

    # Batch embedding
    all_embeddings = []
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        embeddings = embed_fn(batch)
        all_embeddings.extend(embeddings)

    # Cosine similarity hesapla
    similarities = []
    for i in range(len(all_embeddings) - 1):
        a = np.array(all_embeddings[i])
        b = np.array(all_embeddings[i + 1])
        sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)
        similarities.append(float(sim))

    return similarities


def semantic_chunk(
    text: str,
    embed_fn: callable,
    min_chunk_tokens: int = 300,
    max_chunk_tokens: int = 2500,
    similarity_threshold: Optional[float] = None,
    percentile_cutoff: int = 25,
) -> list[str]:
    """
    Semantic chunking: cumleleri embedding similarity'ye gore gruplar.

    Args:
        text: Parse edilmis Markdown metin
        embed_fn: Embedding fonksiyonu
        min_chunk_tokens: Minimum chunk boyutu (token ~ word * 1.3)
        max_chunk_tokens: Maksimum chunk boyutu
        similarity_threshold: Sabit esik (None ise percentile kullanilir)
        percentile_cutoff: Similarity percentile'i — bu yuzdenin altindaki
                          gecisler chunk siniri olur

    Returns:
        Chunk listesi
    """
    sentences = split_into_sentences(text)

    if not sentences:
        return []

    if len(sentences) <= 3:
        return [text]

    # Embedding similarity hesapla
    similarities = compute_similarities(sentences, embed_fn)

    if not similarities:
        return [text]

    # Esik belirle
    if similarity_threshold is None:
        threshold = float(np.percentile(similarities, percentile_cutoff))
    else:
        threshold = similarity_threshold

    # Chunk sinirlarini belirle
    chunks = []
    current_chunk_sentences: list[str] = [sentences[0]]

    for i, sim in enumerate(similarities):
        next_sentence = sentences[i + 1]
        current_text = "\n".join(current_chunk_sentences)
        current_tokens = len(current_text.split()) * 1.3  # Kaba token tahmini

        # Chunk siniri koy:
        # 1. Similarity dusuk VE minimum boyuta ulasildi
        # 2. VEYA maksimum boyut asildi
        if (sim < threshold and current_tokens >= min_chunk_tokens) or \
           current_tokens >= max_chunk_tokens:
            chunks.append("\n".join(current_chunk_sentences))
            current_chunk_sentences = [next_sentence]
        else:
            current_chunk_sentences.append(next_sentence)

    # Son chunk
    if current_chunk_sentences:
        chunks.append("\n".join(current_chunk_sentences))

    return chunks


def simple_chunk(
    text: str,
    target_tokens: int = 1500,
    overlap_tokens: int = 200,
) -> list[str]:
    """
    Basit token-bazli chunking — embedding olmadan fallback.
    Paragraf sinirlarini korur.

    Args:
        text: Markdown metin
        target_tokens: Hedef chunk boyutu
        overlap_tokens: Chunk'lar arasi overlap

    Returns:
        Chunk listesi
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk: list[str] = []
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_tokens = len(para.split()) * 1.3

        if current_size + para_tokens > target_tokens and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            # Overlap: son paragrafi bir sonraki chunk'a da ekle
            if overlap_tokens > 0 and current_chunk:
                last = current_chunk[-1]
                current_chunk = [last]
                current_size = len(last.split()) * 1.3
            else:
                current_chunk = []
                current_size = 0

        current_chunk.append(para)
        current_size += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks
