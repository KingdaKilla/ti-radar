"""Pydantic Request/Response Models fuer die API.

Panel-Modelle und Domain-Datenstrukturen sind in domain/models.py definiert
und werden hier re-exportiert fuer Rueckwaertskompatibilitaet.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Domain-Modelle (re-exportiert fuer Rueckwaertskompatibilitaet) ---
from ti_radar.domain.models import (  # noqa: E402
    ApiAlert as ApiAlert,
)
from ti_radar.domain.models import (
    CompetitivePanel as CompetitivePanel,
)
from ti_radar.domain.models import (
    CpcFlowPanel as CpcFlowPanel,
)
from ti_radar.domain.models import (
    ExplainabilityMetadata as ExplainabilityMetadata,
)
from ti_radar.domain.models import (
    FundingPanel as FundingPanel,
)
from ti_radar.domain.models import (
    GeographicPanel as GeographicPanel,
)
from ti_radar.domain.models import (
    LandscapePanel as LandscapePanel,
)
from ti_radar.domain.models import (
    MaturityPanel as MaturityPanel,
)
from ti_radar.domain.models import (
    ResearchImpactPanel as ResearchImpactPanel,
)
from ti_radar.domain.models import (
    TemporalPanel as TemporalPanel,
)

# --- Request (API-spezifisch) ---


class RadarRequest(BaseModel):
    """Anfrage fuer eine Technology-Radar-Analyse."""

    technology: str = Field(
        ..., min_length=1, max_length=200, description="Technologie-Suchbegriff"
    )
    years: int = Field(10, ge=3, le=30, description="Analysezeitraum in Jahren")


# --- Response: Gesamt-Radar (API-Envelope) ---


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
