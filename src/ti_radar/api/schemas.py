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
    martini_john_ratio: float = 0.0
    maturity_percent: float = 0.0
    saturation_level: float = 0.0
    inflection_year: float = 0.0
    r_squared: float = 0.0
    fit_model: str = ""
    time_series: list[dict[str, Any]] = []
    s_curve_fitted: list[dict[str, Any]] = []
    forecast: list[dict[str, Any]] = []


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


class FundingPanel(BaseModel):
    """UC4: Foerderungs-Panel."""

    total_funding_eur: float = 0.0
    funding_cagr: float = 0.0
    avg_project_size: float = 0.0
    by_programme: list[dict[str, Any]] = []
    time_series: list[dict[str, Any]] = []
    time_series_by_programme: list[dict[str, Any]] = []


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
    """Komplette Radar-Antwort mit allen 5 Panels."""

    technology: str
    analysis_period: str
    maturity: MaturityPanel = MaturityPanel()
    landscape: LandscapePanel = LandscapePanel()
    competitive: CompetitivePanel = CompetitivePanel()
    funding: FundingPanel = FundingPanel()
    cpc_flow: CpcFlowPanel = CpcFlowPanel()
    explainability: ExplainabilityMetadata = ExplainabilityMetadata()
