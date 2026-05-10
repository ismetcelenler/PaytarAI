"""
PaytarAI Backend — Pydantic Settings Configuration

.env dosyasından tüm konfigürasyon değerlerini okur.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Anthropic (Claude Sonnet / Haiku) -----
    anthropic_api_key: str = ""

    # ----- OpenAI (Whisper + Embeddings) -----
    openai_api_key: str = ""

    # ----- Groq (Llama 3.3 70B) -----
    groq_api_key: str = ""

    # ----- Qdrant Cloud -----
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "paytar_veterinary"

    # ----- Database -----
    database_url: str = "sqlite:///./paytar.db"

    # ----- Server -----
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Singleton instance
settings = Settings()
