"""UC5: CPC-Technologiefluss — Co-Klassifikations-Analyse."""

from __future__ import annotations

import logging

from ti_radar.api.schemas import CpcFlowPanel
from ti_radar.config import Settings
from ti_radar.domain.cpc_descriptions import describe_cpc
from ti_radar.domain.cpc_flow import (
    assign_colors,
    build_cooccurrence_with_years,
    extract_cpc_sets_with_years,
)
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository

logger = logging.getLogger(__name__)


async def analyze_cpc_flow(
    technology: str,
    start_year: int,
    end_year: int,
    *,
    cpc_level: int = 4,
    top_n: int = 15,
) -> tuple[CpcFlowPanel, list[str], list[str], list[str]]:
    """CPC-Technologiefluss analysieren via Jaccard Co-Klassifikation."""
    settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    if not settings.patents_db_available:
        warnings.append("Patent-DB nicht verfuegbar — CPC-Analyse uebersprungen")
        return CpcFlowPanel(), sources, methods, warnings

    try:
        repo = PatentRepository(settings.patents_db_path)
        # Nur vollstaendige Jahre verwenden
        effective_end = end_year
        last_full = await repo.get_last_full_year()
        if last_full is not None and last_full < end_year:
            effective_end = last_full
            warnings.append(
                f"Patent-Daten bis {effective_end} vollstaendig "
                f"(ab {effective_end + 1} unvollstaendig)"
            )
        patent_rows = await repo.get_cpc_codes_with_years(
            technology, start_year=start_year, end_year=effective_end
        )
    except Exception as exc:
        logger.warning("CPC flow query failed: %s", exc)
        warnings.append(f"CPC-Abfrage fehlgeschlagen: {exc}")
        return CpcFlowPanel(), sources, methods, warnings

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
