"""Pydantic Request/Response Models fuer die API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# --- Request ---

class RadarRequest(BaseModel):
    """Anfrage fuer eine Technology-Radar-Analyse."""

    technology: str = Field(
        ..., min_length=1, max_length=200, description="Technologie-Suchbegriff"
    )
    years: int = Field(10, ge=3, le=30, description="Analysezeitraum in Jahren")


# --- Response: Einzelne Panels ---

class MaturityPanel(BaseModel):
    """UC2: Reifegrad-Panel."""

    phase: str = ""
    phase_de: str = ""
    confidence: float = 0.0
    cagr: float = 0.0
    maturity_percent: float = 0.0
    saturation_level: float = 0.0
    inflection_year: float = 0.0
    r_squared: float = 0.0
    fit_model: str = ""
    time_series: list[dict[str, Any]] = []
    s_curve_fitted: list[dict[str, Any]] = []


class LandscapePanel(BaseModel):
    """UC1: Landschaft-Panel."""

    total_patents: int = 0
    total_projects: int = 0
    total_publications: int = 0
    time_series: list[dict[str, Any]] = []
    top_countries: list[dict[str, Any]] = []


class CompetitivePanel(BaseModel):
    """UC3: Wettbewerb-Panel."""

    hhi_index: float = 0.0
    concentration_level: str = ""
    top_actors: list[dict[str, Any]] = []
    top_3_share: float = 0.0

    # Netzwerk-Graph Daten (Force-Directed)
    network_nodes: list[dict[str, Any]] = []
    network_edges: list[dict[str, Any]] = []

    # Vollstaendige Akteur-Tabelle
    full_actors: list[dict[str, Any]] = []


class FundingPanel(BaseModel):
    """UC4: Foerderungs-Panel."""

    total_funding_eur: float = 0.0
    funding_cagr: float = 0.0
    avg_project_size: float = 0.0
    by_programme: list[dict[str, Any]] = []
    time_series: list[dict[str, Any]] = []
    time_series_by_programme: list[dict[str, Any]] = []
    instrument_breakdown: list[dict[str, Any]] = []


class CpcFlowPanel(BaseModel):
    """UC5: CPC-Technologiefluss-Panel."""

    matrix: list[list[float]] = []
    labels: list[str] = []
    colors: list[str] = []
    total_patents_analyzed: int = 0
    total_connections: int = 0
    cpc_level: int = 4
    year_data: dict[str, Any] = {}
    cpc_descriptions: dict[str, str] = {}


class GeographicPanel(BaseModel):
    """UC6: Geografie-Panel."""

    total_countries: int = 0
    total_cities: int = 0
    cross_border_share: float = 0.0
    country_distribution: list[dict[str, Any]] = []
    city_distribution: list[dict[str, Any]] = []
    collaboration_pairs: list[dict[str, Any]] = []


class ResearchImpactPanel(BaseModel):
    """UC7: Research-Impact-Panel."""

    h_index: int = 0
    avg_citations: float = 0.0
    total_papers: int = 0
    influential_ratio: float = 0.0
    citation_trend: list[dict[str, Any]] = []
    top_papers: list[dict[str, Any]] = []
    top_venues: list[dict[str, Any]] = []
    publication_types: list[dict[str, Any]] = []


class TemporalPanel(BaseModel):
    """UC8: Temporal-Dynamik-Panel."""

    new_entrant_rate: float = 0.0
    persistence_rate: float = 0.0
    dominant_programme: str = ""
    actor_timeline: list[dict[str, Any]] = []
    programme_evolution: list[dict[str, Any]] = []
    entrant_persistence_trend: list[dict[str, Any]] = []
    instrument_evolution: list[dict[str, Any]] = []
    technology_breadth: list[dict[str, Any]] = []


# --- Response: Explainability ---

class ExplainabilityMetadata(BaseModel):
    """Transparenz-Metadaten fuer jede Analyse."""

    sources_used: list[str] = []
    methods: list[str] = []
    deterministic: bool = True
    warnings: list[str] = []
    query_time_ms: int = 0


# --- Response: Gesamt-Radar ---

class RadarResponse(BaseModel):
    """Komplette Radar-Antwort mit allen 8 Panels."""

    technology: str
    analysis_period: str
    maturity: MaturityPanel = MaturityPanel()
    landscape: LandscapePanel = LandscapePanel()
    competitive: CompetitivePanel = CompetitivePanel()
    funding: FundingPanel = FundingPanel()
    cpc_flow: CpcFlowPanel = CpcFlowPanel()
    geographic: GeographicPanel = GeographicPanel()
    research_impact: ResearchImpactPanel = ResearchImpactPanel()
    temporal: TemporalPanel = TemporalPanel()
    explainability: ExplainabilityMetadata = ExplainabilityMetadata()
