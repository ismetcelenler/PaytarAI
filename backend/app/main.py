"""
PaytarAI Backend — FastAPI Entry Point

CORS, lifecycle hooks, ve router mount'larını içerir.
"""

# OMP/MKL native conflict fix — BGE-M3 (FlagEmbedding) ile langgraph birlikte
# yuklendiginde Intel MKL/libomp cakismasini onler. Diger import'lardan ONCE.
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Embeddings (BGE-M3) langgraph'tan ONCE yuklenmeli — segfault onler
from app.rag import embeddings  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import pathlib

dotenv_path = pathlib.Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

from app.config import settings
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle — startup & shutdown hooks."""
    # --- Startup ---
    print("[PaytarAI] Backend baslatiliyor...")
    print(f"   Qdrant: {settings.qdrant_url or 'YAPıLANDıRıLMADI'}")
    print(f"   CORS Origins: {settings.cors_origin_list}")
    yield
    # --- Shutdown ---
    print("[PaytarAI] Backend kapatiliyor...")


app = FastAPI(
    title="PaytarAI — Veteriner Karar Destek Asistanı",
    description=(
        "Büyükbaş hayvan sağlığına özel, kanıt tabanlı veteriner karar destek API'si. "
        "Dual-role mimari: Veteriner Hekim ve Üretici."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router Mount ---
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — API bilgi mesajı."""
    return {
        "name": "PaytarAI",
        "version": "0.1.0",
        "description": "Veteriner Karar Destek Asistanı API",
        "docs": "/docs",
    }
