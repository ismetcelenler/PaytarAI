"""
PaytarAI — Reranker (Phase 2, local)

Iki asamali retrieval'in ikinci asamasi: dense retrieval'dan gelen top-N
chunk'i cross-encoder ile yeniden siralayip en alakali top-K'yi secer.

Model: BAAI/bge-reranker-v2-m3 (568M, multilingual, Apache-2.0)
Direct transformers API kullanir — FlagEmbedding ve sentence-transformers
CrossEncoder ikisi de yeni transformers surumleriyle uyumsuz.
"""

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
MAX_LENGTH = 512

_model = None
_tokenizer = None
_device = None


def _ensure_model():
    """Reranker modelini ve tokenizer'i lazy yukle (singleton)."""
    global _model, _tokenizer, _device
    if _model is None:
        use_cuda = torch.cuda.is_available()
        _device = "cuda" if use_cuda else "cpu"
        device_str = (
            f"cuda:0 ({torch.cuda.get_device_name(0)})" if use_cuda else "cpu"
        )
        print(
            f"[Reranker] {RERANKER_MODEL} yukleniyor "
            f"(device={device_str}, fp16={use_cuda})..."
        )
        _tokenizer = AutoTokenizer.from_pretrained(RERANKER_MODEL)
        _model = AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL)
        _model = _model.to(_device)
        # NOT: FP16 (.half()) ile BGE-reranker-v2-m3 logit'leri tum chunk'larda
        # asiri negatif (-8 to -10) cikiyor → sigmoid hepsini 0'a düşürüyor.
        # FP32 modunda tutuyoruz; RTX 3060'ta 30 chunk yine ~800ms, kabul edilebilir.
        _model.eval()
        print(f"[Reranker] Hazir.")
    return _model, _tokenizer, _device


def rerank(
    query: str,
    documents: list[dict],
    top_k: int = 3,
    batch_size: int = 32,
) -> list[dict]:
    """
    Dense retrieval'dan gelen documents'i cross-encoder ile yeniden sirala.

    Args:
        query: Kullanici sorgusu (orijinal Turkce)
        documents: [{"text": ..., "score": ..., "metadata": ...}, ...]
        top_k: Geriye dondurulecek max chunk sayisi
        batch_size: GPU memory'ye gore ayarlanabilir (RTX 3060 6GB -> 32 OK)

    Returns:
        Top-K en alakali chunk'lar. Her chunk'a "rerank_score" alani eklenir.
    """
    if not documents:
        return []
    if not query or not query.strip():
        return documents[:top_k]

    model, tokenizer, device = _ensure_model()

    t0 = time.perf_counter()

    # RAW logits ile sırala (sigmoid alakali/alakasiz pair'lerde 0 veya 1'e
    # yapısıyor — özellikle multilingual TR-EN pair'lerinde logit'ler genelde
    # tum chunk'larda negatif oluyor → sigmoid sıralamayı kaybediyor).
    # Sirayi raw logit ile yap, sigmoid sadece kullanici-yuzu skor icin.
    all_logits: list[float] = []
    with torch.no_grad():
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            texts = [d.get("text", "") for d in batch_docs]
            queries = [query] * len(texts)

            inputs = tokenizer(
                queries,
                texts,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            ).to(device)

            outputs = model(**inputs)
            logits = outputs.logits.squeeze(-1).float()  # [batch_size]
            all_logits.extend(logits.cpu().tolist())

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Hem raw logit (sıralama icin) hem sigmoid skor (audit/UI icin) yaz
    for d, lg in zip(documents, all_logits):
        d["rerank_logit"] = float(lg)
        d["rerank_score"] = float(1.0 / (1.0 + pow(2.71828, -lg)))  # sigmoid manual

    # Sıralama: raw logit ile (mutlak deger 0'a yakin olsa bile relative dogru)
    documents.sort(key=lambda d: d.get("rerank_logit", -1e9), reverse=True)

    logit_min = min(all_logits) if all_logits else 0.0
    logit_max = max(all_logits) if all_logits else 0.0
    print(
        f"[Reranker] {len(documents)} chunk reranked in {elapsed_ms:.0f}ms "
        f"-> top {top_k} (logit range: {logit_min:.2f}..{logit_max:.2f})"
    )

    print(
        f"[Reranker] {len(documents)} chunk reranked in {elapsed_ms:.0f}ms "
        f"-> top {top_k} (best score: {documents[0]['rerank_score']:.3f})"
    )

    return documents[:top_k]
