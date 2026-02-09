"""FastAPI Application Factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ti_radar.api.data import router as data_router
from ti_radar.api.radar import router as radar_router


def create_app() -> FastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung."""
    app = FastAPI(
        title="Technology Radar API",
        description="Technology Intelligence Radar — Alle 4 Use Cases auf einen Blick.",
        version="0.1.0",
    )

    # CORS fuer Frontend-Entwicklung (Vite dev server auf :3000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(radar_router)
    app.include_router(data_router)

    return app
