"""FastAPI Application Factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ti_radar.api.data import router as data_router
from ti_radar.api.radar import router as radar_router
from ti_radar.config import Settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung."""
    settings = Settings()

    app = FastAPI(
        title="Technology Radar API",
        description="Technology Intelligence Radar — Alle 5 Use Cases auf einen Blick.",
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

    # Startup: DB-Verfuegbarkeit pruefen
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

    return app
