"""UC8: Temporal Dynamics — Zeitliche Entwicklung des Technologiefeldes."""

from __future__ import annotations

import logging

from ti_radar.config import Settings
from ti_radar.domain.analysis_text import generate_temporal_text
from ti_radar.domain.models import TemporalPanel
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository
from ti_radar.use_cases._helpers import effective_patent_end_year

logger = logging.getLogger(__name__)


async def analyze_temporal(
    technology: str,
    start_year: int,
    end_year: int,
    *,
    settings: Settings | None = None,
    patent_repo: PatentRepository | None = None,
    cordis_repo: CordisRepository | None = None,
) -> tuple[TemporalPanel, list[str], list[str], list[str]]:
    """UC8: Temporal-Dynamik analysieren."""
    if settings is None:
        settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    actors_by_year: dict[int, dict[str, int]] = {}
    cpc_by_year: dict[int, list[str]] = {}
    instrument_data: list[dict[str, str | int | float]] = []

    # Patent-Repo erstellen, falls nicht injiziert
    if patent_repo is None and settings.patents_db_available:
        patent_repo = PatentRepository(settings.patents_db_path)

    # Patent-Akteure pro Jahr
    if patent_repo is not None:
        try:
            patent_end = await effective_patent_end_year(patent_repo, end_year, warnings)
            patent_actors = await patent_repo.top_applicants_by_year(
                technology, start_year=start_year, end_year=patent_end
            )
            for row in patent_actors:
                year = int(row["year"])
                name = str(row["name"]).upper().strip()
                if year not in actors_by_year:
                    actors_by_year[year] = {}
                actors_by_year[year][name] = actors_by_year[year].get(name, 0) + int(row["count"])

            cpc_rows = await patent_repo.get_cpc_codes_with_years(
                technology, start_year=start_year, end_year=patent_end
            )
            for row in cpc_rows:
                year = int(row["year"])
                if year not in cpc_by_year:
                    cpc_by_year[year] = []
                cpc_by_year[year].append(str(row["cpc_codes"]))

            if patent_actors:
                sources.append("EPO DOCDB (lokal)")
        except Exception as e:
            logger.warning("Temporal patent query failed: %s", e)
            warnings.append(f"Patent-Temporal fehlgeschlagen: {e}")

    # CORDIS-Repo erstellen, falls nicht injiziert
    if cordis_repo is None and settings.cordis_db_available:
        cordis_repo = CordisRepository(settings.cordis_db_path)

    # CORDIS-Akteure pro Jahr
    if cordis_repo is not None:
        try:
            cordis_actors = await cordis_repo.orgs_by_year(
                technology, start_year=start_year, end_year=end_year
            )
            for row in cordis_actors:
                year = int(row["year"])
                name = str(row["name"]).upper().strip()
                if year not in actors_by_year:
                    actors_by_year[year] = {}
                actors_by_year[year][name] = actors_by_year[year].get(name, 0) + int(row["count"])

            instrument_data = await cordis_repo.funding_by_instrument(
                technology, start_year=start_year, end_year=end_year
            )
            if cordis_actors:
                sources.append("CORDIS (lokal)")
        except Exception as e:
            logger.warning("Temporal CORDIS query failed: %s", e)
            warnings.append(f"CORDIS-Temporal fehlgeschlagen: {e}")

    # Metriken berechnen
    entrant_persistence = _compute_actor_dynamics(actors_by_year)
    tech_breadth = _compute_technology_breadth(cpc_by_year)
    actor_timeline = _compute_actor_timeline(actors_by_year, top_n=10)
    programme_evo = _compute_programme_evolution(instrument_data)

    latest_new_entrant = entrant_persistence[-1]["new_entrant_rate"] if entrant_persistence else 0.0
    latest_persistence = entrant_persistence[-1]["persistence_rate"] if entrant_persistence else 0.0

    programme_counts: dict[str, int] = {}
    for instr_row in instrument_data:
        scheme = str(instr_row.get("scheme", ""))
        count_val = int(instr_row.get("count", 0))
        programme_counts[scheme] = programme_counts.get(scheme, 0) + count_val
    dominant = (
        max(programme_counts, key=lambda k: programme_counts[k], default="")
        if programme_counts else ""
    )

    methods.append("Akteur-Dynamik (New Entrant Rate, Persistence Rate)")
    if tech_breadth:
        methods.append("Technologie-Breite (einzigartige CPC-Sektionen pro Jahr)")

    panel = TemporalPanel(
        new_entrant_rate=round(latest_new_entrant, 4),
        persistence_rate=round(latest_persistence, 4),
        dominant_programme=dominant,
        actor_timeline=actor_timeline,
        programme_evolution=programme_evo,
        entrant_persistence_trend=entrant_persistence,
        instrument_evolution=instrument_data,
        technology_breadth=tech_breadth,
    )
    panel.analysis_text = generate_temporal_text(panel)

    return panel, sources, methods, warnings


# --- Reine Berechnungsfunktionen (definiert in domain/temporal_metrics.py) ---
# Re-Exports fuer Rueckwaertskompatibilitaet (Tests importieren diese Pfade)
from ti_radar.domain.temporal_metrics import (  # noqa: F401, E402
    _compute_actor_dynamics,
    _compute_actor_timeline,
    _compute_programme_evolution,
    _compute_technology_breadth,
)
