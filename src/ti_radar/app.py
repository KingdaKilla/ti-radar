"""FastAPI Application Factory."""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ti_radar.api.data import router as data_router
from ti_radar.api.radar import router as radar_router
from ti_radar.config import Settings

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Strukturiertes Logging mit Zeitstempel, Level und Modul-Name."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    root = logging.getLogger("ti_radar")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # Verhindert doppelte Log-Eintraege bei uvicorn
    root.propagate = False


def create_app() -> FastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung."""
    _configure_logging()
    settings = Settings()

    app = FastAPI(
        title="Technology Radar API",
        description="Technology Intelligence Radar — Alle 8 Use Cases auf einen Blick.",
        version="0.1.0",
    )

    # CORS (konfigurierbar via CORS_ORIGINS env variable)
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(radar_router)
    app.include_router(data_router)

    # Startup: DB- und API-Verfuegbarkeit pruefen
    @app.on_event("startup")
    async def _check_data_sources() -> None:
        if settings.patents_db_available:
            logger.info("Patents DB: %s", settings.patents_db_path)
        else:
            logger.warning("Patents DB not found: %s", settings.patents_db_path)

        if settings.cordis_db_available:
            logger.info("CORDIS DB: %s", settings.cordis_db_path)
        else:
            logger.warning("CORDIS DB not found: %s", settings.cordis_db_path)

        # API-Key-Status (maskiert, nie den echten Key loggen)
        oa_status = "Token konfiguriert" if settings.openaire_access_token else "Public Access"
        logger.info("OpenAIRE: %s", oa_status)
        ss_status = "API Key konfiguriert" if settings.semantic_scholar_api_key else "Public Access"
        logger.info("Semantic Scholar: %s", ss_status)
        logger.info(
            "EPO OPS: %s",
            "API Key konfiguriert" if settings.epo_ops_consumer_key else "nicht konfiguriert",
        )
        logger.info(
            "CORDIS API: %s",
            "Key konfiguriert" if settings.cordis_api_key else "nicht konfiguriert",
        )
        logger.info("GLEIF LEI: oeffentlich (kein Key noetig)")

    return app
