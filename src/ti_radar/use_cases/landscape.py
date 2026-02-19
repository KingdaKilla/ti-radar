"""UC1: Technology Landscape — Ueberblick ueber Patente, Projekte, Publikationen."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from ti_radar.config import Settings
from ti_radar.domain.analysis_text import generate_landscape_text
from ti_radar.domain.metrics import (  # noqa: F401
    _merge_time_series,
    _yoy_growth,
    merge_country_data,
)
from ti_radar.domain.models import LandscapePanel
from ti_radar.infrastructure.adapters.openaire_adapter import OpenAIREAdapter
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository
from ti_radar.use_cases._helpers import effective_patent_end_year as _effective_patent_end_year

logger = logging.getLogger(__name__)


async def analyze_landscape(
    technology: str,
    start_year: int,
    end_year: int,
    *,
    settings: Settings | None = None,
    patent_repo: PatentRepository | None = None,
    cordis_repo: CordisRepository | None = None,
    openaire_adapter: OpenAIREAdapter | None = None,
) -> tuple[LandscapePanel, list[str], list[str], list[str]]:
    """
    UC1: Technology Landscape analysieren.

    Args:
        technology: Suchbegriff
        start_year: Startjahr
        end_year: Endjahr
        settings: Optional — Settings-Instanz (Default: neu erzeugt)
        patent_repo: Optional — PatentRepository (Default: aus Settings)
        cordis_repo: Optional — CordisRepository (Default: aus Settings)
        openaire_adapter: Optional — OpenAIREAdapter (Default: aus Settings)

    Returns:
        Tuple aus (Panel, sources_used, methods, warnings)
    """
    if settings is None:
        settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    patent_years: list[dict[str, int]] = []
    patent_countries: list[dict[str, str | int]] = []
    total_patents = 0

    project_years: list[dict[str, int]] = []
    project_countries: list[dict[str, str | int]] = []
    total_projects = 0

    publication_years: list[dict[str, int]] = []
    total_publications = 0

    # Parallel queries auf alle Datenquellen
    tasks: list[asyncio.Task[Any]] = []

    if settings.patents_db_available:
        if patent_repo is None:
            patent_repo = PatentRepository(settings.patents_db_path)
        # Nur vollstaendige Jahre fuer Patent-Daten verwenden
        effective_patent_end = await _effective_patent_end_year(
            patent_repo, end_year, warnings,
        )
        end = effective_patent_end
        tasks.append(asyncio.create_task(
            patent_repo.count_by_year(technology, start_year=start_year, end_year=end),
            name="patent_years",
        ))
        tasks.append(asyncio.create_task(
            patent_repo.count_by_country(technology, start_year=start_year, end_year=end),
            name="patent_countries",
        ))
    else:
        warnings.append("Patent-DB nicht verfuegbar — keine Patentdaten")

    if settings.cordis_db_available:
        if cordis_repo is None:
            cordis_repo = CordisRepository(settings.cordis_db_path)
        tasks.append(asyncio.create_task(
            cordis_repo.count_by_year(technology, start_year=start_year, end_year=end_year),
            name="project_years",
        ))
        tasks.append(asyncio.create_task(
            cordis_repo.count_by_country(technology, start_year=start_year, end_year=end_year),
            name="project_countries",
        ))
    else:
        warnings.append("CORDIS-DB nicht verfuegbar — keine Projektdaten")

    if settings.openaire_available:
        if openaire_adapter is None:
            openaire_adapter = OpenAIREAdapter(
                access_token=settings.openaire_access_token,
                refresh_token=settings.openaire_refresh_token,
            )
        tasks.append(asyncio.create_task(
            openaire_adapter.count_by_year(technology, start_year=start_year, end_year=end_year),
            name="publication_years",
        ))

    # Alle Tasks ausfuehren
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for task, result in zip(tasks, results, strict=False):
            if isinstance(result, Exception):
                logger.warning("Landscape query '%s' failed: %s", task.get_name(), result)
                warnings.append(f"Query '{task.get_name()}' fehlgeschlagen: {result}")
                continue

            name = task.get_name()
            if name == "patent_years":
                patent_years = cast(list[dict[str, int]], result)
            elif name == "patent_countries":
                patent_countries = cast(list[dict[str, str | int]], result)
            elif name == "project_years":
                project_years = cast(list[dict[str, int]], result)
            elif name == "project_countries":
                project_countries = cast(list[dict[str, str | int]], result)
            elif name == "publication_years":
                publication_years = cast(list[dict[str, int]], result)

    # Quellen und Methoden dokumentieren
    if patent_years or patent_countries:
        sources.append("EPO DOCDB (lokal)")
        total_patents = sum(y["count"] for y in patent_years)

    if project_years or project_countries:
        sources.append("CORDIS (lokal)")
        total_projects = sum(y["count"] for y in project_years)

    if publication_years:
        sources.append("OpenAIRE (API)")
        total_publications = sum(y["count"] for y in publication_years)

    methods.append("FTS5-Volltextsuche")
    methods.append("Jaehrliche Aggregation")
    if publication_years:
        methods.append("Normalisierte Wachstumsraten (YoY %)")

    # Time Series zusammenfuehren (Jahr, Patente, Projekte, Publikationen)
    time_series = _merge_time_series(
        patent_years, project_years, publication_years, start_year, end_year,
    )

    # Top Countries zusammenfuehren
    top_countries = merge_country_data(patent_countries, project_countries, limit=20)

    panel = LandscapePanel(
        total_patents=total_patents,
        total_projects=total_projects,
        total_publications=total_publications,
        time_series=time_series,
        top_countries=top_countries,
    )
    panel.analysis_text = generate_landscape_text(panel)

    return panel, sources, methods, warnings


