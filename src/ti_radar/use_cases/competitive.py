"""UC3: Competitive Intelligence — Wettbewerbs-Analyse."""

from __future__ import annotations

import logging
from typing import Any

from ti_radar.api.schemas import CompetitivePanel
from ti_radar.config import Settings
from ti_radar.domain.metrics import hhi_concentration_level, hhi_index
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository

logger = logging.getLogger(__name__)


async def analyze_competitive(
    technology: str,
    start_year: int,
    end_year: int,
) -> tuple[CompetitivePanel, list[str], list[str], list[str]]:
    """
    UC3: Wettbewerbslandschaft analysieren.

    Kombiniert Patent-Anmelder und CORDIS-Organisationen zu einem
    Gesamtbild der wichtigsten Akteure mit HHI-Konzentration.
    """
    settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    # Akteure aus beiden Quellen sammeln
    actor_counts: dict[str, int] = {}

    # Patent-Anmelder
    if settings.patents_db_available:
        try:
            repo = PatentRepository(settings.patents_db_path)
            # Nur vollstaendige Jahre verwenden
            effective_patent_end = end_year
            last_full = await repo.get_last_full_year()
            if last_full is not None and last_full < end_year:
                effective_patent_end = last_full
                warnings.append(
                    f"Patent-Daten bis {effective_patent_end} vollstaendig "
                    f"(ab {effective_patent_end + 1} unvollstaendig)"
                )
            applicants = await repo.top_applicants(
                technology, start_year=start_year, end_year=effective_patent_end, limit=50
            )
            for a in applicants:
                name = str(a["name"]).upper().strip()
                if name:
                    actor_counts[name] = actor_counts.get(name, 0) + int(a["count"])
            if applicants:
                sources.append("EPO DOCDB (lokal)")
        except Exception as e:
            logger.warning("Competitive patent query failed: %s", e)
            warnings.append(f"Patent-Abfrage fehlgeschlagen: {e}")

    # CORDIS-Organisationen
    if settings.cordis_db_available:
        try:
            repo_c = CordisRepository(settings.cordis_db_path)
            orgs = await repo_c.top_organizations(
                technology, start_year=start_year, end_year=end_year, limit=50
            )
            for o in orgs:
                name = str(o["name"]).upper().strip()
                if name:
                    actor_counts[name] = actor_counts.get(name, 0) + int(o["count"])
            if orgs:
                sources.append("CORDIS (lokal)")
        except Exception as e:
            logger.warning("Competitive CORDIS query failed: %s", e)
            warnings.append(f"CORDIS-Abfrage fehlgeschlagen: {e}")

    if not actor_counts:
        return CompetitivePanel(), sources, methods, warnings

    # Sortieren und Top-Akteure
    sorted_actors = sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)
    total_activity = sum(c for _, c in sorted_actors)

    # Marktanteile berechnen
    top_actors: list[dict[str, Any]] = []
    for name, count in sorted_actors[:20]:
        share = count / total_activity if total_activity > 0 else 0.0
        top_actors.append({
            "name": name,
            "count": count,
            "share": round(share, 4),
        })

    # HHI berechnen (ueber alle Akteure, nicht nur Top 20)
    shares = [c / total_activity for _, c in sorted_actors] if total_activity > 0 else []
    hhi = hhi_index(shares)
    level_en, _level_de = hhi_concentration_level(hhi)
    methods.append("HHI-Index (Herfindahl-Hirschman)")

    # Top-3 Anteil
    top_3_count = sum(c for _, c in sorted_actors[:3])
    top_3_share = top_3_count / total_activity if total_activity > 0 else 0.0

    methods.append("Akteur-Aggregation (Patent-Anmelder + CORDIS-Organisationen)")

    panel = CompetitivePanel(
        hhi_index=round(hhi, 1),
        concentration_level=level_en,
        top_actors=top_actors,
        top_3_share=round(top_3_share, 4),
    )

    return panel, sources, methods, warnings
