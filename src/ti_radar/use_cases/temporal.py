"""UC8: Temporal Dynamics — Zeitliche Entwicklung des Technologiefeldes."""

from __future__ import annotations

import logging
from typing import Any

from ti_radar.api.schemas import TemporalPanel
from ti_radar.config import Settings
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository

logger = logging.getLogger(__name__)


async def analyze_temporal(
    technology: str,
    start_year: int,
    end_year: int,
) -> tuple[TemporalPanel, list[str], list[str], list[str]]:
    """UC8: Temporal-Dynamik analysieren."""
    settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    actors_by_year: dict[int, dict[str, int]] = {}
    cpc_by_year: dict[int, list[str]] = {}
    instrument_data: list[dict[str, str | int | float]] = []

    # Patent-Akteure pro Jahr
    if settings.patents_db_available:
        try:
            repo = PatentRepository(settings.patents_db_path)
            last_full = await repo.get_last_full_year()
            patent_end = min(end_year, last_full) if last_full else end_year
            if last_full and last_full < end_year:
                warnings.append(f"Patent-Daten bis {last_full} vollstaendig — {end_year} trunkiert")
            patent_actors = await repo.top_applicants_by_year(
                technology, start_year=start_year, end_year=patent_end
            )
            for row in patent_actors:
                year = int(row["year"])
                name = str(row["name"]).upper().strip()
                if year not in actors_by_year:
                    actors_by_year[year] = {}
                actors_by_year[year][name] = actors_by_year[year].get(name, 0) + int(row["count"])

            cpc_rows = await repo.get_cpc_codes_with_years(
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

    # CORDIS-Akteure pro Jahr
    if settings.cordis_db_available:
        try:
            repo_c = CordisRepository(settings.cordis_db_path)
            cordis_actors = await repo_c.orgs_by_year(
                technology, start_year=start_year, end_year=end_year
            )
            for row in cordis_actors:
                year = int(row["year"])
                name = str(row["name"]).upper().strip()
                if year not in actors_by_year:
                    actors_by_year[year] = {}
                actors_by_year[year][name] = actors_by_year[year].get(name, 0) + int(row["count"])

            instrument_data = await repo_c.funding_by_instrument(
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

    return panel, sources, methods, warnings


def _compute_actor_dynamics(
    actors_by_year: dict[int, dict[str, int]],
) -> list[dict[str, Any]]:
    """New Entrant Rate und Persistence Rate pro Jahr."""
    sorted_years = sorted(actors_by_year.keys())
    if not sorted_years:
        return []

    result: list[dict[str, Any]] = []
    prev_actors: set[str] = set()

    for year in sorted_years:
        current_actors = set(actors_by_year[year].keys())

        if not prev_actors:
            new_entrant_rate = 1.0
            persistence_rate = 0.0
        else:
            new_entrants = current_actors - prev_actors
            persisting = current_actors & prev_actors
            new_entrant_rate = len(new_entrants) / len(current_actors) if current_actors else 0.0
            persistence_rate = len(persisting) / len(prev_actors) if prev_actors else 0.0

        result.append({
            "year": year,
            "new_entrant_rate": round(new_entrant_rate, 4),
            "persistence_rate": round(persistence_rate, 4),
            "total_actors": len(current_actors),
        })

        prev_actors = current_actors

    return result


def _compute_technology_breadth(
    cpc_by_year: dict[int, list[str]],
) -> list[dict[str, Any]]:
    """Technologie-Breite pro Jahr (Leydesdorff et al. 2015).

    Zwei Granularitaeten:
    - unique_cpc_sections: CPC-Sektionen (A-H, grob, max 9)
    - unique_cpc_subclasses: CPC-Subklassen (Level 4, z.B. H01L, feinkoernig)
    """
    result: list[dict[str, Any]] = []

    for year in sorted(cpc_by_year.keys()):
        sections: set[str] = set()
        subclasses: set[str] = set()
        for cpc_str in cpc_by_year[year]:
            for code in cpc_str.split(","):
                code = code.strip()
                if code:
                    sections.add(code[0])
                    if len(code) >= 4:
                        subclasses.add(code[:4])

        result.append({
            "year": year,
            "unique_cpc_sections": len(sections),
            "unique_cpc_subclasses": len(subclasses),
        })

    return result


def _compute_actor_timeline(
    actors_by_year: dict[int, dict[str, int]], top_n: int = 10
) -> list[dict[str, Any]]:
    """Top-N Akteure mit ihren aktiven Jahren."""
    total_counts: dict[str, int] = {}
    actor_years: dict[str, list[int]] = {}

    for year, actors in actors_by_year.items():
        for name, count in actors.items():
            total_counts[name] = total_counts.get(name, 0) + count
            if name not in actor_years:
                actor_years[name] = []
            actor_years[name].append(year)

    top_actors = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return [
        {
            "name": name,
            "years_active": sorted(actor_years.get(name, [])),
            "total_count": count,
        }
        for name, count in top_actors
    ]


def _compute_programme_evolution(
    instrument_data: list[dict[str, str | int | float]],
) -> list[dict[str, Any]]:
    """Programm-Verteilung pro Jahr (fuer Stacked Area Chart)."""
    by_year: dict[int, dict[str, int]] = {}
    for row in instrument_data:
        year = int(row.get("year", 0))
        scheme = str(row.get("scheme", ""))
        count = int(row.get("count", 0))
        if year not in by_year:
            by_year[year] = {}
        by_year[year][scheme] = by_year[year].get(scheme, 0) + count

    return [
        {"year": year, **counts}
        for year, counts in sorted(by_year.items())
    ]
