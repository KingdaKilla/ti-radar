"""UC4: Funding Radar — EU-Foerderungs-Analyse."""

from __future__ import annotations

import logging
from typing import Any

from ti_radar.api.schemas import FundingPanel
from ti_radar.config import Settings
from ti_radar.domain.metrics import cagr
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository

logger = logging.getLogger(__name__)


async def analyze_funding(
    technology: str,
    start_year: int,
    end_year: int,
) -> tuple[FundingPanel, list[str], list[str], list[str]]:
    """
    UC4: EU-Foerderung fuer eine Technologie analysieren.

    Ausschliesslich aus CORDIS-Daten (FP7, H2020, Horizon Europe).
    """
    settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    if not settings.cordis_db_available:
        warnings.append("CORDIS-DB nicht verfuegbar — keine Foerderdaten")
        return FundingPanel(), sources, methods, warnings

    repo = CordisRepository(settings.cordis_db_path)

    funding_years: list[dict[str, int | float]] = []
    programme_data: list[dict[str, str | int | float]] = []
    year_programme_data: list[dict[str, str | int | float]] = []

    # Datentrunkierung pruefen
    try:
        last_full = await repo.get_last_full_year()
        if last_full is not None and last_full < end_year:
            warnings.append(
                f"CORDIS-Daten bis {last_full} vollstaendig "
                f"(ab {last_full + 1} unvollstaendig)"
            )
    except Exception as e:
        logger.warning("CORDIS last full year check failed: %s", e)

    try:
        funding_years = await repo.funding_by_year(
            technology, start_year=start_year, end_year=end_year
        )
        sources.append("CORDIS (lokal)")
    except Exception as e:
        logger.warning("Funding year query failed: %s", e)
        warnings.append(f"Foerder-Zeitreihe fehlgeschlagen: {e}")

    try:
        programme_data = await repo.funding_by_programme(
            technology, start_year=start_year, end_year=end_year
        )
    except Exception as e:
        logger.warning("Funding programme query failed: %s", e)
        warnings.append(f"Programm-Abfrage fehlgeschlagen: {e}")

    try:
        year_programme_data = await repo.funding_by_year_and_programme(
            technology, start_year=start_year, end_year=end_year
        )
    except Exception as e:
        logger.warning("Funding year/programme query failed: %s", e)
        warnings.append(f"Programm-Zeitreihe fehlgeschlagen: {e}")

    # Instrument-Breakdown (RIA, IA, CSA, etc.)
    instrument_data: list[dict[str, str | int | float]] = []
    try:
        instrument_data = await repo.funding_by_instrument(
            technology, start_year=start_year, end_year=end_year
        )
    except Exception as e:
        logger.warning("Funding instrument query failed: %s", e)
        warnings.append(f"Instrument-Abfrage fehlgeschlagen: {e}")

    # Gesamtfoerderung (null-safe)
    total_funding = sum(float(f["funding"] or 0) for f in funding_years)
    total_projects = sum(int(f["count"] or 0) for f in funding_years)
    avg_size = total_funding / total_projects if total_projects > 0 else 0.0

    # CAGR der Foerderung (Kalenderjahr-Spanne)
    funding_cagr = 0.0
    non_zero = [f for f in funding_years if float(f["funding"] or 0) > 0]
    if len(non_zero) >= 2:
        first = float(non_zero[0]["funding"] or 0)
        last = float(non_zero[-1]["funding"] or 0)
        first_year = int(non_zero[0]["year"])
        last_year = int(non_zero[-1]["year"])
        year_span = last_year - first_year
        if year_span > 0:
            funding_cagr = cagr(first, last, year_span)
            methods.append(
                f"Foerder-CAGR ueber {year_span} Jahre "
                f"({first_year}-{last_year})"
            )

    # Zeitreihe formatieren
    time_series: list[dict[str, Any]] = []
    for f in funding_years:
        time_series.append({
            "year": int(f["year"]),
            "funding": round(float(f["funding"] or 0), 2),
            "projects": int(f["count"] or 0),
        })

    # Programme formatieren
    by_programme: list[dict[str, Any]] = []
    for p in programme_data:
        by_programme.append({
            "programme": str(p["programme"] or "UNKNOWN"),
            "funding": round(float(p["funding"] or 0), 2),
            "projects": int(p["count"] or 0),
        })

    # Zeitreihe pro Programm formatieren
    time_series_by_programme: list[dict[str, Any]] = []
    for yp in year_programme_data:
        time_series_by_programme.append({
            "year": int(yp["year"]),
            "programme": str(yp["programme"] or "UNKNOWN"),
            "funding": round(float(yp["funding"] or 0), 2),
            "projects": int(yp["count"] or 0),
        })

    # Instrument-Breakdown formatieren
    instrument_breakdown: list[dict[str, Any]] = []
    for inst in instrument_data:
        instrument_breakdown.append({
            "instrument": str(inst.get("funding_scheme") or "UNKNOWN"),
            "year": int(inst.get("year") or 0),
            "count": int(inst.get("count") or 0),
            "funding": round(float(inst.get("funding") or 0), 2),
        })

    methods.append("EU-Foerderdaten-Aggregation (FP7, H2020, Horizon Europe)")

    panel = FundingPanel(
        total_funding_eur=round(total_funding, 2),
        funding_cagr=round(funding_cagr, 2),
        avg_project_size=round(avg_size, 2),
        by_programme=by_programme,
        time_series=time_series,
        time_series_by_programme=time_series_by_programme,
        instrument_breakdown=instrument_breakdown,
    )

    return panel, sources, methods, warnings
