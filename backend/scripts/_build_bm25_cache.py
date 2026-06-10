"""BM25 index olustur ve cache'le. Tek seferlik."""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.rag.bm25_store import warmup_bm25

if __name__ == "__main__":
    print("[BM25] Cache build basliyor...")
    warmup_bm25()
    print("[BM25] DONE")
