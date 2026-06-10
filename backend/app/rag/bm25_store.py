"""
PaytarAI — BM25 Sparse Retrieval Store

Production medical RAG'larda standart pratik: dense (BGE-M3) + sparse (BM25)
hybrid retrieval. Cross-encoder reranker ikisini birlestirir.

Neden BM25:
- Spesifik isim/jargon eslemesi (Mortellaro, Treponema, vet_09 gibi)
- Dense (semantik) genel konsept eslemesi yapar; spesifik kelime varligini
  garanti etmez. BM25 tam tersi: kelime eslemesi yapar.
- Tipik production setup: dense top-30 + BM25 top-30 -> RRF -> rerank

Implementasyon:
- rank-bm25 (Python, in-memory)
- Index Qdrant'tan ilk yuklenir, pickle olarak cache'lenir
- Cache 100MB civari (21K chunk x ortalama 300 token)

Reference: MEGA-RAG (PMC 2026), Hybrid Search BM25 + Vector 2026 production guide
"""
from __future__ import annotations

import pickle
import re
import time
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from app.config import settings


_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_CACHE_DIR = _BACKEND_DIR / "data" / "cache"
_CACHE_FILE = _CACHE_DIR / "bm25_index.pkl"


# Turkish-aware basit tokenizer
# Lowercase + diacritic-insensitive + punct strip + min length 2
_DIACRITIC_MAP = str.maketrans("çğıöşüâîû", "cgiosuaiu")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Turkish-aware tokenize: lower, diacritic-strip, punct-strip, split."""
    if not text:
        return []
    s = text.lower().translate(_DIACRITIC_MAP)
    s = _PUNCT_RE.sub(" ", s)
    return [t for t in s.split() if len(t) >= 2]


class BM25Store:
    """In-memory BM25 index over all Qdrant chunks."""

    def __init__(self):
        self._bm25: Optional[BM25Okapi] = None
        # Her dokuman icin meta (id, source_title, text, parent_text, language)
        self._docs: list[dict] = []

    def is_loaded(self) -> bool:
        return self._bm25 is not None

    def build_from_qdrant(self) -> int:
        """Tum chunklari Qdrant'tan cek, tokenize et, index olustur."""
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=120,
        )

        print("[BM25] Qdrant'tan chunk'lar cekiliyor...")
        t0 = time.time()
        docs: list[dict] = []
        next_off = None
        while True:
            points, next_off = client.scroll(
                collection_name=settings.qdrant_collection_name,
                limit=500,
                with_payload=True,
                with_vectors=False,
                offset=next_off,
            )
            if not points:
                break
            for p in points:
                payload = p.payload or {}
                child = payload.get("text", "") or ""
                parent = payload.get("parent_text", "") or child
                docs.append({
                    "id": str(p.id),
                    "child_text": child,
                    "parent_text": parent,
                    "source_title": payload.get("source_title", "?"),
                    "language": payload.get("language", "?"),
                    "original_title": payload.get("original_title", ""),
                })
            if next_off is None:
                break
        t_fetch = time.time() - t0
        print(f"[BM25] {len(docs)} chunk cekildi ({t_fetch:.1f}s)")

        # Child text tokenize (precision)
        print("[BM25] Tokenize ediliyor...")
        t1 = time.time()
        tokenized = [_tokenize(d["child_text"]) for d in docs]

        print(f"[BM25] BM25Okapi index olusturuluyor...")
        t2 = time.time()
        self._bm25 = BM25Okapi(tokenized)
        self._docs = docs
        t_index = time.time() - t2
        print(f"[BM25] Index hazir (tokenize {t2-t1:.1f}s, index {t_index:.1f}s)")
        return len(docs)

    def save_cache(self) -> None:
        """Pickle olarak diske kaydet."""
        if self._bm25 is None:
            return
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with _CACHE_FILE.open("wb") as f:
            pickle.dump({"bm25": self._bm25, "docs": self._docs}, f)
        print(f"[BM25] Cache yazildi: {_CACHE_FILE}")

    def load_cache(self) -> bool:
        """Pickle'dan yukle. Basariliysa True."""
        if not _CACHE_FILE.exists():
            return False
        try:
            with _CACHE_FILE.open("rb") as f:
                data = pickle.load(f)
            self._bm25 = data["bm25"]
            self._docs = data["docs"]
            print(f"[BM25] Cache yuklendi: {len(self._docs)} chunk")
            return True
        except Exception as e:
            print(f"[BM25] Cache yukleme hatasi: {e}")
            return False

    def search(self, query: str, limit: int = 30) -> list[dict]:
        """
        BM25 ile top-N chunk dondur.
        Format: {score, text (parent), child_text, metadata}
        """
        if self._bm25 is None or not self._docs:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        # Top-N indeks
        import numpy as np
        top_idx = np.argsort(scores)[::-1][:limit]
        results = []
        for i in top_idx:
            score = float(scores[i])
            if score <= 0:
                continue
            d = self._docs[i]
            results.append({
                "score": score,
                # qdrant_store ile uyumlu: text = parent_text (generator/rerank icin)
                "text": d["parent_text"],
                "metadata": {
                    "source_title": d["source_title"],
                    "language": d["language"],
                    "original_title": d["original_title"],
                },
            })
        return results


# Singleton
_store: Optional[BM25Store] = None


def get_bm25_store(lazy: bool = True) -> BM25Store:
    """Singleton. lazy=True ise build/load yapmaz (warmup gerekiyor)."""
    global _store
    if _store is None:
        _store = BM25Store()
    if not lazy and not _store.is_loaded():
        if not _store.load_cache():
            _store.build_from_qdrant()
            _store.save_cache()
    return _store


def warmup_bm25() -> None:
    """Uygulama baslangicinda cagrilir. Cache yoksa olusturur."""
    get_bm25_store(lazy=False)


def bm25_search(query: str, limit: int = 30) -> list[dict]:
    """Public API — retriever_node bunu cagirir."""
    store = get_bm25_store(lazy=False)
    return store.search(query, limit=limit)
