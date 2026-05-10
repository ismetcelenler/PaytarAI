"""
PaytarAI — Health Check Endpoint

Sistem durumu kontrolü ve bağımlılık sağlık kontrolleri.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Sistem sağlık kontrolü."""
    return {
        "status": "healthy",
        "service": "PaytarAI Backend",
        "version": "0.1.0",
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detaylı sağlık kontrolü — tüm bağımlılıkların durumu."""
    checks = {
        "api": "ok",
        "qdrant": "unchecked",
        "anthropic": "unchecked",
        "openai": "unchecked",
        "groq": "unchecked",
    }

    # TODO: Faz 2-3'te bağımlılık kontrolleri eklenecek
    # - Qdrant bağlantı testi
    # - LLM provider erişilebilirlik kontrolleri

    return {
        "status": "healthy",
        "checks": checks,
    }
