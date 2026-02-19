"""UC7: Research Impact — Akademische Wirkung analysieren."""

from __future__ import annotations

import logging
from typing import Any

from ti_radar.config import Settings
from ti_radar.domain.analysis_text import generate_research_impact_text
from ti_radar.domain.models import ResearchImpactPanel
from ti_radar.infrastructure.adapters.semantic_scholar_adapter import SemanticScholarAdapter

logger = logging.getLogger(__name__)


async def analyze_research_impact(
    technology: str,
    start_year: int,
    end_year: int,
    *,
    settings: Settings | None = None,
    semantic_scholar_adapter: SemanticScholarAdapter | None = None,
) -> tuple[ResearchImpactPanel, list[str], list[str], list[str]]:
    """UC7: Forschungswirkung via Semantic Scholar analysieren."""
    if settings is None:
        settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    if semantic_scholar_adapter is None:
        semantic_scholar_adapter = SemanticScholarAdapter(
            api_key=settings.semantic_scholar_api_key
        )
    papers: list[dict[str, Any]] = []

    try:
        papers = await semantic_scholar_adapter.search_papers(
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
    panel.analysis_text = generate_research_impact_text(panel)

    return panel, sources, methods, warnings


# --- Reine Berechnungsfunktionen (definiert in domain/research_metrics.py) ---
# Re-Exports fuer Rueckwaertskompatibilitaet (Tests importieren diese Pfade)
from ti_radar.domain.research_metrics import (  # noqa: F401, E402
    _compute_citation_trend,
    _compute_h_index,
    _compute_publication_types,
    _compute_top_papers,
    _compute_venue_distribution,
)
