"""
PaytarAI — BGE-M3 Embeddings (Phase 1)

Multilingual cross-lingual embedder.
Model: BAAI/bge-m3 (1024 boyut, Apache-2.0)

ONEMLI: Bu modulun langgraph'tan ONCE import edilmesi gerekir, aksi halde
native lib (OMP/MKL) cakismasi nedeniyle segfault olusur.
run_eval.py vb. giris noktalari bunu basinda zorlar.
"""

import os
# OMP/MKL native conflict onleyici — torch import'undan ONCE set edilmeli
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from FlagEmbedding import BGEM3FlagModel
import torch


EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIMENSION = 1024
DEFAULT_BATCH_SIZE = 12
DEFAULT_MAX_LENGTH = 512

_model: BGEM3FlagModel | None = None


def _device_info() -> str:
    if torch.cuda.is_available():
        return f"cuda:0 ({torch.cuda.get_device_name(0)})"
    return "cpu"


def get_model() -> BGEM3FlagModel:
    """BGE-M3 singleton (lazy load)."""
    global _model
    if _model is None:
        use_cuda = torch.cuda.is_available()
        print(f"[Embeddings] BGE-M3 yukleniyor (device={_device_info()}, fp16={use_cuda})...")
        _model = BGEM3FlagModel(
            EMBEDDING_MODEL,
            use_fp16=use_cuda,
        )
        print(f"[Embeddings] BGE-M3 hazir.")
    return _model


def embed_texts(texts: list[str], batch_size: int = DEFAULT_BATCH_SIZE) -> list[list[float]]:
    """Metin listesini dense embedding vektorlerine donusturur."""
    if not texts:
        return []
    model = get_model()
    output = model.encode(
        texts,
        batch_size=batch_size,
        max_length=DEFAULT_MAX_LENGTH,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return [[float(x) for x in v] for v in output["dense_vecs"]]


def embed_single(text: str) -> list[float]:
    """Tek metni embedding vektorune donusturur."""
    result = embed_texts([text], batch_size=1)
    return result[0] if result else []
