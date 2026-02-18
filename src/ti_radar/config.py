"""Zentrale Konfiguration via Pydantic Settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Datenbank-Pfade (relativ zum Working Directory)
    patents_db_path: str = "data/patents.db"
    cordis_db_path: str = "data/cordis.db"
    api_cache_db_path: str = "data/api_cache.db"

    # EPO OPS API (Fallback)
    epo_ops_consumer_key: str = ""
    epo_ops_consumer_secret: str = ""

    # CORDIS API (optional)
    cordis_api_key: str = ""

    # OpenAIRE (optional)
    openaire_access_token: str = ""

    # Semantic Scholar (optional, erhoeht Rate Limits)
    semantic_scholar_api_key: str = ""

    # GLEIF Cache (optional)
    gleif_cache_db_path: str = "data/gleif_cache.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def patents_db_available(self) -> bool:
        return Path(self.patents_db_path).exists()

    @property
    def cordis_db_available(self) -> bool:
        return Path(self.cordis_db_path).exists()

    @property
    def openaire_available(self) -> bool:
        """OpenAIRE ist oeffentlich zugaenglich (Token optional fuer hoehere Rate-Limits)."""
        return True

    @property
    def semantic_scholar_available(self) -> bool:
        """Semantic Scholar ist oeffentlich zugaenglich (Key optional)."""
        return True
