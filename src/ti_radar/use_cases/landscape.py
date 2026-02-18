"""UC1: Technology Landscape — Ueberblick ueber Patente, Projekte, Publikationen."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from ti_radar.api.schemas import LandscapePanel
from ti_radar.config import Settings
from ti_radar.domain.metrics import merge_country_data
from ti_radar.infrastructure.adapters.openaire_adapter import OpenAIREAdapter
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository

logger = logging.getLogger(__name__)


async def analyze_landscape(
    technology: str,
    start_year: int,
    end_year: int,
) -> tuple[LandscapePanel, list[str], list[str], list[str]]:
    """
    UC1: Technology Landscape analysieren.

    Returns:
        Tuple aus (Panel, sources_used, methods, warnings)
    """
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
        patent_repo = PatentRepository(settings.patents_db_path)
        # Nur vollstaendige Jahre fuer Patent-Daten verwenden
        effective_patent_end = end_year
        last_full = await patent_repo.get_last_full_year()
        if last_full is not None and last_full < end_year:
            effective_patent_end = last_full
            warnings.append(
                f"Patent-Daten bis {effective_patent_end} vollstaendig "
                f"(ab {effective_patent_end + 1} unvollstaendig)"
            )
        tasks.append(asyncio.create_task(
            patent_repo.count_by_year(technology, start_year=start_year, end_year=effective_patent_end),
            name="patent_years",
        ))
        tasks.append(asyncio.create_task(
            patent_repo.count_by_country(technology, start_year=start_year, end_year=effective_patent_end),
            name="patent_countries",
        ))
    else:
        warnings.append("Patent-DB nicht verfuegbar — keine Patentdaten")

    if settings.cordis_db_available:
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
        openaire = OpenAIREAdapter(access_token=settings.openaire_access_token)
        tasks.append(asyncio.create_task(
            openaire.count_by_year(technology, start_year=start_year, end_year=end_year),
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

    return panel, sources, methods, warnings


def _yoy_growth(current: int, previous: int) -> float | None:
    """Prozentuale Veraenderung zum Vorjahr. None wenn Vorjahr=0."""
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _merge_time_series(
    patent_years: list[dict[str, int]],
    project_years: list[dict[str, int]],
    publication_years: list[dict[str, int]],
    start_year: int,
    end_year: int,
) -> list[dict[str, Any]]:
    """Patent-, Projekt- und Publikations-Zeitreihen mit Wachstumsraten."""
    patent_map = {y["year"]: y["count"] for y in patent_years}
    project_map = {y["year"]: y["count"] for y in project_years}
    publication_map = {y["year"]: y["count"] for y in publication_years}

    all_years = set(range(start_year, end_year + 1))
    all_years |= set(patent_map.keys())
    all_years |= set(project_map.keys())
    all_years |= set(publication_map.keys())

    sorted_years = sorted(y for y in all_years if start_year <= y <= end_year)

    series: list[dict[str, Any]] = []
    for i, year in enumerate(sorted_years):
        pat = patent_map.get(year, 0)
        proj = project_map.get(year, 0)
        pub = publication_map.get(year, 0)

        entry: dict[str, Any] = {
            "year": year,
            "patents": pat,
            "projects": proj,
            "publications": pub,
        }

        if i > 0:
            prev_year = sorted_years[i - 1]
            entry["patents_growth"] = _yoy_growth(
                pat, patent_map.get(prev_year, 0),
            )
            entry["projects_growth"] = _yoy_growth(
                proj, project_map.get(prev_year, 0),
            )
            entry["publications_growth"] = _yoy_growth(
                pub, publication_map.get(prev_year, 0),
            )

        series.append(entry)

    return series


