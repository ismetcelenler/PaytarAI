"""
PaytarAI Backend — FastAPI Entry Point

CORS, lifecycle hooks, ve router mount'larını içerir.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
