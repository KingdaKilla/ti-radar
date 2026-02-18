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
    Gesamtbild der wichtigsten Akteure mit HHI-Konzentration,
    Netzwerk-Graph und vollstaendiger Akteur-Tabelle.
    """
    settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    # Akteure getrennt nach Quelle sammeln
    patent_actors: dict[str, int] = {}
    cordis_actors: dict[str, int] = {}
    cordis_countries: dict[str, str] = {}
    cordis_sme: dict[str, bool] = {}
    cordis_coordinator: dict[str, bool] = {}
    effective_patent_end = end_year

    # Patent-Anmelder
    if settings.patents_db_available:
        try:
            repo = PatentRepository(settings.patents_db_path)
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
                    patent_actors[name] = patent_actors.get(name, 0) + int(a["count"])
            if applicants:
                sources.append("EPO DOCDB (lokal)")
        except Exception as e:
            logger.warning("Competitive patent query failed: %s", e)
            warnings.append(f"Patent-Abfrage fehlgeschlagen: {e}")

    # CORDIS-Organisationen (mit Land-Info)
    if settings.cordis_db_available:
        try:
            repo_c = CordisRepository(settings.cordis_db_path)
            orgs = await repo_c.top_organizations_with_country(
                technology, start_year=start_year, end_year=end_year, limit=50
            )
            for o in orgs:
                name = str(o["name"]).upper().strip()
                if name:
                    cordis_actors[name] = cordis_actors.get(name, 0) + int(o["count"])
                    if o.get("country"):
                        cordis_countries[name] = str(o["country"])
                    if o.get("is_sme"):
                        cordis_sme[name] = True
                    if o.get("is_coordinator"):
                        cordis_coordinator[name] = True
            if orgs:
                sources.append("CORDIS (lokal)")
        except Exception as e:
            logger.warning("Competitive CORDIS query failed: %s", e)
            warnings.append(f"CORDIS-Abfrage fehlgeschlagen: {e}")

    # Gesamte Akteur-Counts zusammenfuehren
    actor_counts: dict[str, int] = {}
    for name, count in patent_actors.items():
        actor_counts[name] = actor_counts.get(name, 0) + count
    for name, count in cordis_actors.items():
        actor_counts[name] = actor_counts.get(name, 0) + count

    if not actor_counts:
        return CompetitivePanel(), sources, methods, warnings

    # Sortieren und Top-Akteure
    sorted_actors = sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)
    total_activity = sum(c for _, c in sorted_actors)

    # Marktanteile berechnen (Top 20 fuer Chart)
    top_actors: list[dict[str, Any]] = []
    for name, count in sorted_actors[:20]:
        share = count / total_activity if total_activity > 0 else 0.0
        top_actors.append({
            "name": name,
            "count": count,
            "share": round(share, 4),
        })

    # HHI berechnen (ueber alle Akteure)
    shares = [c / total_activity for _, c in sorted_actors] if total_activity > 0 else []
    hhi = hhi_index(shares)
    level_en, _level_de = hhi_concentration_level(hhi)
    methods.append("HHI-Index (Herfindahl-Hirschman)")

    # Top-3 Anteil
    top_3_count = sum(c for _, c in sorted_actors[:3])
    top_3_share = top_3_count / total_activity if total_activity > 0 else 0.0

    methods.append("Akteur-Aggregation (Patent-Anmelder + CORDIS-Organisationen)")

    # --- Netzwerk-Graph ---
    network_nodes, network_edges = await _build_network(
        technology, start_year, end_year, effective_patent_end,
        actor_counts, patent_actors, cordis_actors, settings, warnings,
    )
    if network_edges:
        methods.append("Co-Partizipation-Netzwerk (Patent-Co-Anmelder + CORDIS-Projektpartner)")

    # --- Vollstaendige Tabelle ---
    full_actors = _build_full_table(
        patent_actors, cordis_actors, cordis_countries,
        cordis_sme, cordis_coordinator,
        actor_counts, total_activity,
    )

    panel = CompetitivePanel(
        hhi_index=round(hhi, 1),
        concentration_level=level_en,
        top_actors=top_actors,
        top_3_share=round(top_3_share, 4),
        network_nodes=network_nodes,
        network_edges=network_edges,
        full_actors=full_actors,
    )

    return panel, sources, methods, warnings


async def _build_network(
    technology: str,
    start_year: int,
    end_year: int,
    effective_patent_end: int,
    actor_counts: dict[str, int],
    patent_actors: dict[str, int],
    cordis_actors: dict[str, int],
    settings: Settings,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Netzwerk-Graph: Knoten + Kanten aus Co-Applicants und Co-Partizipation."""
    patent_actor_set: set[str] = set(patent_actors.keys())
    cordis_actor_set: set[str] = set(cordis_actors.keys())
    all_edges: dict[tuple[str, str], int] = {}

    # Patent-Co-Anmelder
    if settings.patents_db_available:
        try:
            repo = PatentRepository(settings.patents_db_path)
            co_apps = await repo.co_applicants(
                technology, start_year=start_year, end_year=effective_patent_end, limit=200
            )
            for edge in co_apps:
                a = str(edge["actor_a"]).upper().strip()
                b = str(edge["actor_b"]).upper().strip()
                patent_actor_set.add(a)
                patent_actor_set.add(b)
                key = (min(a, b), max(a, b))
                all_edges[key] = all_edges.get(key, 0) + int(edge["co_count"])
        except Exception as e:
            logger.warning("Network patent edges failed: %s", e)
            warnings.append(f"Netzwerk Patent-Kanten fehlgeschlagen: {e}")

    # CORDIS-Co-Partizipation
    if settings.cordis_db_available:
        try:
            repo_c = CordisRepository(settings.cordis_db_path)
            co_parts = await repo_c.co_participation(
                technology, start_year=start_year, end_year=end_year, limit=200
            )
            for edge in co_parts:
                a = str(edge["actor_a"]).upper().strip()
                b = str(edge["actor_b"]).upper().strip()
                cordis_actor_set.add(a)
                cordis_actor_set.add(b)
                key = (min(a, b), max(a, b))
                all_edges[key] = all_edges.get(key, 0) + int(edge["co_count"])
        except Exception as e:
            logger.warning("Network CORDIS edges failed: %s", e)
            warnings.append(f"Netzwerk CORDIS-Kanten fehlgeschlagen: {e}")

    if not all_edges:
        return [], []

    # Top 40 Akteure, Top 100 Kanten
    top_actor_names = sorted(
        actor_counts.keys(), key=lambda n: actor_counts[n], reverse=True
    )[:40]
    top_set = set(top_actor_names)

    filtered_edges = [
        (a, b, w) for (a, b), w in all_edges.items()
        if a in top_set and b in top_set
    ]
    filtered_edges.sort(key=lambda x: x[2], reverse=True)
    filtered_edges = filtered_edges[:100]

    # Nur verbundene Knoten
    connected: set[str] = set()
    for a, b, _ in filtered_edges:
        connected.add(a)
        connected.add(b)

    nodes: list[dict[str, Any]] = []
    for name in connected:
        actor_type = (
            "both" if name in patent_actor_set and name in cordis_actor_set
            else "patent" if name in patent_actor_set
            else "cordis"
        )
        nodes.append({
            "id": name,
            "name": name,
            "count": actor_counts.get(name, 0),
            "type": actor_type,
        })

    edges: list[dict[str, Any]] = [
        {"source": a, "target": b, "weight": w}
        for a, b, w in filtered_edges
    ]

    return nodes, edges


def _build_full_table(
    patent_actors: dict[str, int],
    cordis_actors: dict[str, int],
    cordis_countries: dict[str, str],
    cordis_sme: dict[str, bool],
    cordis_coordinator: dict[str, bool],
    actor_counts: dict[str, int],
    total_activity: int,
) -> list[dict[str, Any]]:
    """Vollstaendige Akteur-Tabelle fuer sortierbare Ansicht."""
    sorted_actors = sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)
    result: list[dict[str, Any]] = []
    for rank, (name, count) in enumerate(sorted_actors, 1):
        share = count / total_activity if total_activity > 0 else 0.0
        result.append({
            "rank": rank,
            "name": name,
            "patents": patent_actors.get(name, 0),
            "projects": cordis_actors.get(name, 0),
            "total": count,
            "share": round(share, 4),
            "country": cordis_countries.get(name, ""),
            "is_sme": cordis_sme.get(name, False),
            "is_coordinator": cordis_coordinator.get(name, False),
        })
    return result
