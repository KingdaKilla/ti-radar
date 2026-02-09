"""Tests fuer Pydantic Request/Response Models (api/schemas.py)."""

import pytest
from pydantic import ValidationError

from ti_radar.api.schemas import (
    CompetitivePanel,
    ExplainabilityMetadata,
    FundingPanel,
    LandscapePanel,
    MaturityPanel,
    RadarRequest,
    RadarResponse,
)


# --- RadarRequest ---


class TestRadarRequest:
    """Tests fuer die Radar-Anfrage."""

    def test_valid_request(self):
        req = RadarRequest(technology="quantum computing", years=10)
        assert req.technology == "quantum computing"
        assert req.years == 10

    def test_default_years(self):
        req = RadarRequest(technology="solar energy")
        assert req.years == 10

    def test_min_years(self):
        req = RadarRequest(technology="test", years=3)
        assert req.years == 3

    def test_max_years(self):
        req = RadarRequest(technology="test", years=30)
        assert req.years == 30

    def test_years_too_low_raises(self):
        with pytest.raises(ValidationError):
            RadarRequest(technology="test", years=2)

    def test_years_too_high_raises(self):
        with pytest.raises(ValidationError):
            RadarRequest(technology="test", years=31)

    def test_empty_technology_raises(self):
        with pytest.raises(ValidationError):
            RadarRequest(technology="")

    def test_technology_too_long_raises(self):
        with pytest.raises(ValidationError):
            RadarRequest(technology="x" * 201)

    def test_technology_max_length(self):
        req = RadarRequest(technology="x" * 200)
        assert len(req.technology) == 200


# --- Panel Defaults ---


class TestPanelDefaults:
    """Tests fuer Standard-Werte der Panel-Models."""

    def test_maturity_defaults(self):
        p = MaturityPanel()
        assert p.phase == ""
        assert p.confidence == 0.0
        assert p.cagr == 0.0
        assert p.time_series == []

    def test_landscape_defaults(self):
        p = LandscapePanel()
        assert p.total_patents == 0
        assert p.total_projects == 0
        assert p.total_publications == 0

    def test_competitive_defaults(self):
        p = CompetitivePanel()
        assert p.hhi_index == 0.0
        assert p.concentration_level == ""
        assert p.top_actors == []

    def test_funding_defaults(self):
        p = FundingPanel()
        assert p.total_funding_eur == 0.0
        assert p.funding_cagr == 0.0
        assert p.by_programme == []

    def test_explainability_defaults(self):
        e = ExplainabilityMetadata()
        assert e.sources_used == []
        assert e.methods == []
        assert e.deterministic is True
        assert e.warnings == []
        assert e.query_time_ms == 0


# --- RadarResponse ---


class TestRadarResponse:
    """Tests fuer die Gesamt-Radar-Antwort."""

    def test_minimal_response(self):
        r = RadarResponse(
            technology="test",
            analysis_period="2015-2025",
        )
        assert r.technology == "test"
        assert r.maturity.phase == ""
        assert r.landscape.total_patents == 0

    def test_full_response(self):
        r = RadarResponse(
            technology="quantum computing",
            analysis_period="2015-2025",
            maturity=MaturityPanel(phase="Growing", confidence=0.75, cagr=12.5),
            landscape=LandscapePanel(total_patents=500, total_projects=30),
            competitive=CompetitivePanel(hhi_index=1200, top_3_share=0.45),
            funding=FundingPanel(total_funding_eur=5_000_000),
            explainability=ExplainabilityMetadata(
                sources_used=["EPO DOCDB", "CORDIS"],
                methods=["CAGR", "HHI"],
                deterministic=True,
                query_time_ms=42,
            ),
        )
        assert r.maturity.phase == "Growing"
        assert r.landscape.total_patents == 500
        assert r.competitive.hhi_index == 1200
        assert r.funding.total_funding_eur == 5_000_000
        assert len(r.explainability.sources_used) == 2

    def test_serialization_roundtrip(self):
        r = RadarResponse(
            technology="test",
            analysis_period="2020-2025",
            maturity=MaturityPanel(phase="Mature", cagr=3.2),
        )
        data = r.model_dump()
        r2 = RadarResponse.model_validate(data)
        assert r2.technology == r.technology
        assert r2.maturity.phase == r.maturity.phase
