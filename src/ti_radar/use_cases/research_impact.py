"""UC7: Research Impact — Akademische Wirkung analysieren."""

from __future__ import annotations

import logging
from typing import Any

from ti_radar.api.schemas import ResearchImpactPanel
from ti_radar.config import Settings
from ti_radar.infrastructure.adapters.semantic_scholar_adapter import SemanticScholarAdapter

logger = logging.getLogger(__name__)


async def analyze_research_impact(
    technology: str,
    start_year: int,
    end_year: int,
) -> tuple[ResearchImpactPanel, list[str], list[str], list[str]]:
    """UC7: Forschungswirkung via Semantic Scholar analysieren."""
    settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    adapter = SemanticScholarAdapter(api_key=settings.semantic_scholar_api_key)
    papers: list[dict[str, Any]] = []

    try:
        papers = await adapter.search_papers(
            technology, year_start=start_year, year_end=end_year, limit=200
        )
        if papers:
            sources.append("Semantic Scholar Academic Graph API")
    except Exception as e:
        logger.warning("Research impact query failed: %s", e)
        warnings.append(f"Semantic Scholar Abfrage fehlgeschlagen: {e}")

    if not papers:
        return ResearchImpactPanel(), sources, methods, warnings

    # Metriken berechnen
    citations = [p.get("citationCount", 0) or 0 for p in papers]
    influential = [p.get("influentialCitationCount", 0) or 0 for p in papers]

    h_index = _compute_h_index(citations)
    total_citations = sum(citations)
    total_influential = sum(influential)
    avg_citations = total_citations / len(papers) if papers else 0.0
    influential_ratio = total_influential / total_citations if total_citations > 0 else 0.0

    citation_trend = _compute_citation_trend(papers)
    top_papers = _compute_top_papers(papers, top_n=10)
    top_venues = _compute_venue_distribution(papers, top_n=8)
    pub_types = _compute_publication_types(papers)

    methods.append("h-Index (Hirsch 2005; Banks 2006 — Topic-Level-Adaption)")
    methods.append(f"Stichprobe: {len(papers)} Papers (Semantic Scholar Top-200)")
    methods.append("Influential Citations (Valenzuela et al. 2015 — experimentell)")
    if len(papers) >= 200:
        warnings.append(
            "h-Index basiert auf Top-200 relevantesten Papers — Approximation, "
            "kein vollstaendiger Korpus (Banks 2006)"
        )

    panel = ResearchImpactPanel(
        h_index=h_index,
        avg_citations=round(avg_citations, 1),
        total_papers=len(papers),
        influential_ratio=round(influential_ratio, 4),
        citation_trend=citation_trend,
        top_papers=top_papers,
        top_venues=top_venues,
        publication_types=pub_types,
    )

    return panel, sources, methods, warnings


def _compute_h_index(citations: list[int]) -> int:
    """h-Index: groesster Wert h so dass h Paper >= h Zitationen haben."""
    sorted_c = sorted(citations, reverse=True)
    h = 0
    for i, c in enumerate(sorted_c):
        if c >= i + 1:
            h = i + 1
        else:
            break
    return h


def _compute_citation_trend(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Zitationen und Paper-Anzahl pro Jahr."""
    by_year: dict[int, dict[str, int]] = {}
    for p in papers:
        year = p.get("year")
        if not year:
            continue
        if year not in by_year:
            by_year[year] = {"citations": 0, "paper_count": 0}
        by_year[year]["citations"] += p.get("citationCount", 0) or 0
        by_year[year]["paper_count"] += 1

    return [
        {"year": y, "citations": d["citations"], "paper_count": d["paper_count"]}
        for y, d in sorted(by_year.items())
    ]


def _compute_top_papers(
    papers: list[dict[str, Any]], top_n: int = 10
) -> list[dict[str, Any]]:
    """Top-N Paper nach Zitationen sortiert."""
    sorted_papers = sorted(papers, key=lambda p: p.get("citationCount", 0) or 0, reverse=True)
    result: list[dict[str, Any]] = []
    for p in sorted_papers[:top_n]:
        authors = p.get("authors", []) or []
        authors_short = ", ".join(a.get("name", "") for a in authors[:3])
        if len(authors) > 3:
            authors_short += " et al."
        result.append({
            "title": p.get("title", ""),
            "venue": p.get("venue", ""),
            "year": p.get("year", 0),
            "citations": p.get("citationCount", 0) or 0,
            "authors_short": authors_short,
        })
    return result


def _compute_venue_distribution(
    papers: list[dict[str, Any]], top_n: int = 8
) -> list[dict[str, Any]]:
    """Top-Venues nach Anzahl der Paper."""
    counts: dict[str, int] = {}
    for p in papers:
        venue = p.get("venue") or ""
        if venue:
            counts[venue] = counts.get(venue, 0) + 1

    total = sum(counts.values())
    sorted_venues = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {
            "venue": v,
            "count": c,
            "share": round(c / total, 4) if total > 0 else 0.0,
        }
        for v, c in sorted_venues[:top_n]
    ]


def _compute_publication_types(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Publikationstypen zaehlen."""
    counts: dict[str, int] = {}
    for p in papers:
        types = p.get("publicationTypes") or []
        for t in types:
            if t:
                counts[t] = counts.get(t, 0) + 1

    return [
        {"type": t, "count": c}
        for t, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
