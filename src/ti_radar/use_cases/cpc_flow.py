"""UC5: CPC-Technologiefluss — Co-Klassifikations-Analyse."""

from __future__ import annotations

import logging

from ti_radar.config import Settings
from ti_radar.domain.cpc_descriptions import describe_cpc
from ti_radar.domain.cpc_flow import (
    assign_colors,
    build_cooccurrence_with_years,
    extract_cpc_sets_with_years,
)
from ti_radar.domain.models import CpcFlowPanel
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository
from ti_radar.use_cases._helpers import effective_patent_end_year

logger = logging.getLogger(__name__)


async def analyze_cpc_flow(
    technology: str,
    start_year: int,
    end_year: int,
    *,
    cpc_level: int = 4,
    top_n: int = 15,
    settings: Settings | None = None,
    patent_repo: PatentRepository | None = None,
) -> tuple[CpcFlowPanel, list[str], list[str], list[str]]:
    """CPC-Technologiefluss analysieren via Jaccard Co-Klassifikation.

    Args:
        technology: Suchbegriff
        start_year: Startjahr
        end_year: Endjahr
        cpc_level: CPC-Hierarchie-Tiefe (Default: 4)
        top_n: Anzahl Top-Codes (Default: 15)
        settings: Optional — Settings-Instanz (Default: neu erzeugt)
        patent_repo: Optional — PatentRepository (Default: aus Settings)

    Returns:
        Tuple aus (Panel, sources_used, methods, warnings)
    """
    if settings is None:
        settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    if not settings.patents_db_available:
        warnings.append("Patent-DB nicht verfuegbar — CPC-Analyse uebersprungen")
        return CpcFlowPanel(), sources, methods, warnings

    try:
        if patent_repo is None:
            patent_repo = PatentRepository(settings.patents_db_path)
        # Nur vollstaendige Jahre verwenden
        effective_end = await effective_patent_end_year(
            patent_repo, end_year, warnings,
        )

        # SQL-Pfad: Normalisierte patent_cpc Tabelle (alle Patente, kein Sampling)
        if await patent_repo.has_cpc_table():
            return await _analyze_sql_path(
                patent_repo, technology, start_year, effective_end,
                cpc_level=cpc_level, top_n=top_n,
                sources=sources, methods=methods, warnings=warnings,
            )

        # Fallback: Python-Pfad (denormalisierte CPC-Codes, LIMIT 10.000)
        logger.info("patent_cpc Tabelle nicht vorhanden — Fallback auf Python-Pfad")
        return await _analyze_python_path(
            patent_repo, technology, start_year, effective_end,
            cpc_level=cpc_level, top_n=top_n,
            sources=sources, methods=methods, warnings=warnings,
        )

    except Exception as exc:
        logger.warning("CPC flow query failed: %s", exc)
        warnings.append(f"CPC-Abfrage fehlgeschlagen: {exc}")
        return CpcFlowPanel(), sources, methods, warnings


async def _analyze_sql_path(
    repo: PatentRepository,
    technology: str,
    start_year: int,
    end_year: int,
    *,
    cpc_level: int = 4,
    top_n: int = 15,
    sources: list[str],
    methods: list[str],
    warnings: list[str],
) -> tuple[CpcFlowPanel, list[str], list[str], list[str]]:
    """SQL-native Jaccard-Berechnung via patent_cpc Tabelle (alle Patente)."""
    result = await repo.compute_cpc_jaccard(
        technology, start_year=start_year, end_year=end_year,
        top_n=top_n, cpc_level=cpc_level,
    )

    labels = result["labels"]
    matrix = result["matrix"]
    total_connections = result["total_connections"]
    year_data = result["year_data"]
    total_patents = result["total_patents"]

    if not labels or len(labels) < 2:
        warnings.append("Zu wenige CPC-Codes fuer Fluss-Analyse")
        return CpcFlowPanel(), sources, methods, warnings

    sources.append("EPO DOCDB (lokal)")
    colors = assign_colors(labels)

    # CPC-Beschreibungen fuer alle Labels (inkl. year_data.all_labels)
    all_labels = year_data.get("all_labels", labels) if year_data else labels
    cpc_descriptions = {label: describe_cpc(label) for label in set(labels) | set(all_labels)}

    methods.append("CPC-Co-Klassifikation (Jaccard-Index, SQL-nativ)")
    methods.append(f"CPC-Level {cpc_level} (Top {len(labels)} Codes, {total_patents} Patente)")

    panel = CpcFlowPanel(
        matrix=matrix,
        labels=labels,
        colors=colors,
        total_patents_analyzed=total_patents,
        total_connections=total_connections,
        cpc_level=cpc_level,
        year_data=year_data,
        cpc_descriptions=cpc_descriptions,
    )

    return panel, sources, methods, warnings


async def _analyze_python_path(
    repo: PatentRepository,
    technology: str,
    start_year: int,
    end_year: int,
    *,
    cpc_level: int = 4,
    top_n: int = 15,
    sources: list[str],
    methods: list[str],
    warnings: list[str],
) -> tuple[CpcFlowPanel, list[str], list[str], list[str]]:
    """Fallback: Python-basierte Berechnung mit Sampling (max. 10.000 Patente)."""
    patent_rows = await repo.get_cpc_codes_with_years(
        technology, start_year=start_year, end_year=end_year
    )

    if not patent_rows:
        warnings.append("Keine CPC-Codes fuer diese Technologie gefunden")
        return CpcFlowPanel(), sources, methods, warnings

    sources.append("EPO DOCDB (lokal)")

    # CPC-Code-Sets + Jahr pro Patent extrahieren
    patent_data = extract_cpc_sets_with_years(patent_rows, level=cpc_level)

    if len(patent_data) < 2:
        warnings.append("Zu wenige Patente mit mehreren CPC-Codes fuer Fluss-Analyse")
        return CpcFlowPanel(), sources, methods, warnings

    # Co-Occurrence + Jaccard + Year-Data berechnen
    labels, matrix, total_connections, year_data = build_cooccurrence_with_years(
        patent_data, top_n=top_n
    )
    colors = assign_colors(labels)

    # CPC-Beschreibungen fuer Labels generieren
    cpc_descriptions = {label: describe_cpc(label) for label in labels}

    methods.append("CPC-Co-Klassifikation (Jaccard-Index)")
    methods.append(f"CPC-Level {cpc_level} (Top {len(labels)} Codes)")
    warnings.append("Stichprobe max. 10.000 Patente (patent_cpc-Migration empfohlen)")

    panel = CpcFlowPanel(
        matrix=matrix,
        labels=labels,
        colors=colors,
        total_patents_analyzed=len(patent_data),
        total_connections=total_connections,
        cpc_level=cpc_level,
        year_data=year_data,
        cpc_descriptions=cpc_descriptions,
    )

    return panel, sources, methods, warnings
