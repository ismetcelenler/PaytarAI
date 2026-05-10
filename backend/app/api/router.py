"""
PaytarAI — API Router

Tüm v1 endpoint'lerini birleştiren ana router.
"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.voice import router as voice_router
from app.api.v1.ingest import router as ingest_router

api_router = APIRouter()

# --- v1 endpoints ---
api_router.include_router(health_router, prefix="/v1")
api_router.include_router(chat_router, prefix="/v1")
api_router.include_router(voice_router, prefix="/v1")
api_router.include_router(ingest_router, prefix="/v1")
