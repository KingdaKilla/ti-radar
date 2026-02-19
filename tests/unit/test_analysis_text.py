"""Tests fuer deterministische Analyse-Textgenerierung (domain/analysis_text.py)."""

import re

import pytest

from ti_radar.domain.analysis_text import (
    _fmt_eur,
    _fmt_int,
    _fmt_pct,
    _trend_word,
    generate_competitive_text,
    generate_cpc_flow_text,
    generate_funding_text,
    generate_geographic_text,
    generate_landscape_text,
    generate_maturity_text,
    generate_research_impact_text,
    generate_temporal_text,
)
from ti_radar.domain.models import (
    CompetitivePanel,
    CpcFlowPanel,
    FundingPanel,
    GeographicPanel,
    LandscapePanel,
    MaturityPanel,
    ResearchImpactPanel,
    TemporalPanel,
)


def _count_sentences(text: str) -> int:
    """Zaehlt Saetze: Punkt gefolgt von Leerzeichen oder Textende, nicht in Zahlen."""
    # Matches period followed by space-then-uppercase, or end of string
    # Excludes periods in numbers like "1.234" or "0.920"
    return len(re.findall(r"\.\s+[A-ZÄÖÜ]|\.\s*$", text))


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


class TestFmtInt:
    """Tests fuer _fmt_int (deutsches Tausender-Format)."""

    def test_small_number(self):
        assert _fmt_int(42) == "42"

    def test_thousands(self):
        assert _fmt_int(1234) == "1.234"

    def test_millions(self):
        assert _fmt_int(1234567) == "1.234.567"

    def test_zero(self):
        assert _fmt_int(0) == "0"


class TestFmtPct:
    """Tests fuer _fmt_pct (deutsches Prozent-Format)."""

    def test_default_decimal(self):
        assert _fmt_pct(67.3) == "67,3%"

    def test_zero_decimals(self):
        assert _fmt_pct(42.0, decimals=0) == "42%"

    def test_two_decimals(self):
        assert _fmt_pct(12.345, decimals=2) == "12,35%"

    def test_zero(self):
        assert _fmt_pct(0.0) == "0,0%"


class TestFmtEur:
    """Tests fuer _fmt_eur (Euro-Formatierung)."""

    def test_milliarden(self):
        result = _fmt_eur(2_500_000_000)
        assert "Mrd. EUR" in result
        assert "2,5" in result

    def test_millionen(self):
        result = _fmt_eur(345_600_000)
        assert "Mio. EUR" in result
        assert "345,6" in result

    def test_tausend(self):
        result = _fmt_eur(50_000)
        assert "Tsd. EUR" in result

    def test_small(self):
        result = _fmt_eur(500)
        assert "500 EUR" in result

    def test_zero(self):
        assert _fmt_eur(0) == "0 EUR"


class TestTrendWord:
    """Tests fuer _trend_word (CAGR-Bewertung)."""

    def test_very_strong(self):
        assert "sehr stark" in _trend_word(20.0)

    def test_solid(self):
        assert "solides" in _trend_word(10.0)

    def test_slight(self):
        assert "leichtes" in _trend_word(2.0)

    def test_stagnation(self):
        assert "Stagnation" in _trend_word(-2.0)

    def test_decline(self):
        assert "Rueckgang" in _trend_word(-10.0)


# ---------------------------------------------------------------------------
# UC1: Landscape
# ---------------------------------------------------------------------------


class TestGenerateLandscapeText:
    """Tests fuer generate_landscape_text (UC1)."""

    def test_empty_panel_returns_empty(self):
        panel = LandscapePanel()
        assert generate_landscape_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = LandscapePanel(
            total_patents=5000,
            total_projects=1200,
            total_publications=3000,
            top_countries=[
                {"country": "DE", "total": 1500},
                {"country": "FR", "total": 800},
            ],
            time_series=[
                {"year": 2020, "patents": 400, "projects": 100,
                 "patents_growth": 5.5, "projects_growth": 3.2},
                {"year": 2021, "patents": 420, "projects": 110,
                 "patents_growth": 5.0, "projects_growth": 10.0},
            ],
        )
        text = generate_landscape_text(panel)
        assert text != ""
        assert "9.200" in text  # total 5000+1200+3000
        assert "5.000" in text  # patents
        assert "Patente" in text
        assert "DE" in text  # top country
        # Sentence count: 4-8
        assert 4 <= _count_sentences(text) <= 8

    def test_only_patents(self):
        panel = LandscapePanel(total_patents=100)
        text = generate_landscape_text(panel)
        assert "100" in text
        assert "Patente" in text

    def test_active_countries_mentioned(self):
        panel = LandscapePanel(
            total_patents=10,
            top_countries=[
                {"country": "DE", "total": 5},
                {"country": "FR", "total": 3},
                {"country": "IT", "total": 2},
            ],
        )
        text = generate_landscape_text(panel)
        assert "3 Laender" in text


# ---------------------------------------------------------------------------
# UC2: Maturity
# ---------------------------------------------------------------------------


class TestGenerateMaturityText:
    """Tests fuer generate_maturity_text (UC2)."""

    def test_empty_panel_returns_empty(self):
        panel = MaturityPanel()
        assert generate_maturity_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = MaturityPanel(
            phase="Growing",
            phase_de="Wachsend",
            confidence=0.85,
            cagr=12.5,
            maturity_percent=35.0,
            saturation_level=1000.0,
            inflection_year=2025.0,
            r_squared=0.92,
            fit_model="Logistic",
            time_series=[
                {"year": 2020, "patents": 100, "cumulative": 100},
                {"year": 2021, "patents": 120, "cumulative": 220},
                {"year": 2022, "patents": 150, "cumulative": 370},
            ],
        )
        text = generate_maturity_text(panel)
        assert text != ""
        assert "Gao" in text  # Scientific reference
        assert "Wachsend" in text  # phase_de
        assert "35,0%" in text  # maturity percent
        assert "Logistic" in text  # fit model
        assert "0.920" in text  # R-squared
        assert "2025" in text  # inflection year
        period_count = text.count(".")
        assert 4 <= period_count <= 8

    def test_saturation_phase(self):
        panel = MaturityPanel(
            phase="Saturation",
            phase_de="Saettigung",
            maturity_percent=95.0,
            confidence=0.9,
        )
        text = generate_maturity_text(panel)
        assert "Saettigung" in text or "Saettigungsphase" in text
        assert "ausgeschoepft" in text

    def test_remaining_potential(self):
        panel = MaturityPanel(
            phase="Growing",
            phase_de="Wachsend",
            maturity_percent=40.0,
        )
        text = generate_maturity_text(panel)
        assert "50,0%" in text  # 90 - 40 = 50

    def test_no_r_squared_skips_quality(self):
        panel = MaturityPanel(
            phase="Emerging",
            phase_de="Aufkommend",
            maturity_percent=5.0,
        )
        text = generate_maturity_text(panel)
        assert "R\u00b2" not in text


# ---------------------------------------------------------------------------
# UC3: Competitive Intelligence
# ---------------------------------------------------------------------------


class TestGenerateCompetitiveText:
    """Tests fuer generate_competitive_text (UC3)."""

    def test_empty_panel_returns_empty(self):
        panel = CompetitivePanel()
        assert generate_competitive_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = CompetitivePanel(
            hhi_index=2200.0,
            concentration_level="Moderate",
            top_actors=[
                {"name": "SIEMENS AG", "count": 500, "share": 0.25},
                {"name": "BOSCH GMBH", "count": 300, "share": 0.15},
                {"name": "SAP SE", "count": 200, "share": 0.10},
            ],
            top_3_share=0.50,
            network_nodes=[{"id": "A"}, {"id": "B"}],
            network_edges=[{"source": "A", "target": "B", "weight": 5}],
            full_actors=[
                {"rank": 1, "name": "SIEMENS AG", "total": 500},
                {"rank": 2, "name": "BOSCH GMBH", "total": 300},
                {"rank": 3, "name": "SAP SE", "total": 200},
                {"rank": 4, "name": "BMW AG", "total": 100},
            ],
        )
        text = generate_competitive_text(panel)
        assert text != ""
        assert "Garcia-Vega" in text  # Scientific reference
        assert "2.200" in text  # HHI value
        assert "moderat" in text  # concentration level DE
        assert "SIEMENS AG" in text  # top actor
        assert "4 Akteure" in text  # total actors from full_actors
        assert "2 Knoten" in text  # network nodes
        period_count = text.count(".")
        assert 4 <= period_count <= 8

    def test_high_concentration(self):
        panel = CompetitivePanel(
            hhi_index=5000.0,
            concentration_level="High",
            top_actors=[{"name": "MONOPOLIST", "count": 1000, "share": 0.9}],
            top_3_share=0.95,
        )
        text = generate_competitive_text(panel)
        assert "hoch" in text

    def test_fragmented_market(self):
        panel = CompetitivePanel(
            hhi_index=500.0,
            concentration_level="Low",
            top_actors=[
                {"name": "A", "count": 10, "share": 0.05},
                {"name": "B", "count": 10, "share": 0.05},
            ],
            top_3_share=0.15,
        )
        text = generate_competitive_text(panel)
        assert "fragmentiert" in text


# ---------------------------------------------------------------------------
# UC4: Funding
# ---------------------------------------------------------------------------


class TestGenerateFundingText:
    """Tests fuer generate_funding_text (UC4)."""

    def test_empty_panel_returns_empty(self):
        panel = FundingPanel()
        assert generate_funding_text(panel) == ""

    def test_zero_funding_returns_empty(self):
        panel = FundingPanel(total_funding_eur=0.0)
        assert generate_funding_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = FundingPanel(
            total_funding_eur=500_000_000.0,
            funding_cagr=8.5,
            funding_cagr_period="2015\u20132023",
            avg_project_size=2_500_000.0,
            by_programme=[
                {"programme": "HORIZON EUROPE", "funding": 300_000_000.0, "projects": 120},
                {"programme": "H2020", "funding": 200_000_000.0, "projects": 80},
            ],
            time_series=[
                {"year": 2020, "funding": 50_000_000, "projects": 20},
                {"year": 2021, "funding": 60_000_000, "projects": 25},
            ],
            instrument_breakdown=[
                {"instrument": "RIA", "year": 2020, "count": 15, "funding": 30_000_000},
                {"instrument": "IA", "year": 2020, "count": 5, "funding": 20_000_000},
                {"instrument": "RIA", "year": 2021, "count": 18, "funding": 35_000_000},
            ],
        )
        text = generate_funding_text(panel)
        assert text != ""
        assert "Mio. EUR" in text or "Mrd. EUR" in text
        assert "HORIZON EUROPE" in text
        assert "8,5%" in text  # CAGR
        assert "RIA" in text  # top instrument
        period_count = text.count(".")
        assert 4 <= period_count <= 8

    def test_milliarden_formatting(self):
        panel = FundingPanel(
            total_funding_eur=2_500_000_000.0,
            time_series=[{"year": 2020, "funding": 2_500_000_000, "projects": 100}],
        )
        text = generate_funding_text(panel)
        assert "Mrd. EUR" in text


# ---------------------------------------------------------------------------
# UC5: CPC Flow
# ---------------------------------------------------------------------------


class TestGenerateCpcFlowText:
    """Tests fuer generate_cpc_flow_text (UC5)."""

    def test_empty_panel_returns_empty(self):
        panel = CpcFlowPanel()
        assert generate_cpc_flow_text(panel) == ""

    def test_no_labels_returns_empty(self):
        panel = CpcFlowPanel(matrix=[[1.0]], labels=[])
        assert generate_cpc_flow_text(panel) == ""

    def test_no_matrix_returns_empty(self):
        panel = CpcFlowPanel(matrix=[], labels=["H01L"])
        assert generate_cpc_flow_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = CpcFlowPanel(
            matrix=[
                [1.0, 0.5, 0.1],
                [0.5, 1.0, 0.3],
                [0.1, 0.3, 1.0],
            ],
            labels=["H01L", "G06F", "B01D"],
            total_patents_analyzed=5000,
            total_connections=120,
            cpc_level=4,
            cpc_descriptions={
                "H01L": "Halbleiter",
                "G06F": "Datenverarbeitung",
                "B01D": "Trennung",
            },
        )
        text = generate_cpc_flow_text(panel)
        assert text != ""
        assert "5.000" in text  # total patents
        assert "120" in text  # connections
        assert "3 CPC-Codes" in text
        assert "H01L" in text  # strongest connection partner
        assert "G06F" in text
        assert "0.500" in text  # max jaccard
        period_count = text.count(".")
        assert 4 <= period_count <= 8

    def test_low_connectivity_interpretation(self):
        panel = CpcFlowPanel(
            matrix=[
                [1.0, 0.05],
                [0.05, 1.0],
            ],
            labels=["A01B", "C07D"],
            total_patents_analyzed=100,
            total_connections=5,
            cpc_level=4,
        )
        text = generate_cpc_flow_text(panel)
        assert "spezialisiert" in text

    def test_high_connectivity_interpretation(self):
        panel = CpcFlowPanel(
            matrix=[
                [1.0, 0.5],
                [0.5, 1.0],
            ],
            labels=["A01B", "C07D"],
            total_patents_analyzed=1000,
            total_connections=50,
            cpc_level=4,
        )
        text = generate_cpc_flow_text(panel)
        assert "interdisziplinaer" in text or "Querbezuege" in text


# ---------------------------------------------------------------------------
# UC6: Geographic
# ---------------------------------------------------------------------------


class TestGenerateGeographicText:
    """Tests fuer generate_geographic_text (UC6)."""

    def test_empty_panel_returns_empty(self):
        panel = GeographicPanel()
        assert generate_geographic_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = GeographicPanel(
            total_countries=25,
            total_cities=150,
            cross_border_share=0.42,
            country_distribution=[
                {"country": "DE", "total": 500},
                {"country": "FR", "total": 300},
                {"country": "IT", "total": 200},
                {"country": "ES", "total": 150},
                {"country": "NL", "total": 120},
                {"country": "SE", "total": 100},
                {"country": "AT", "total": 80},
                {"country": "BE", "total": 70},
                {"country": "PL", "total": 60},
                {"country": "US", "total": 50},
            ],
            collaboration_pairs=[
                {"country_a": "DE", "country_b": "FR", "count": 45},
            ],
        )
        text = generate_geographic_text(panel)
        assert text != ""
        assert "25 Laendern" in text
        assert "150 Staedten" in text
        assert "42,0%" in text  # cross-border share
        assert "DE" in text  # top country
        assert "FR" in text  # collaboration partner
        assert "EU" in text or "EWR" in text  # Europe focus
        period_count = text.count(".")
        assert 4 <= period_count <= 8

    def test_no_collaboration_pairs(self):
        panel = GeographicPanel(
            total_countries=5,
            total_cities=10,
            country_distribution=[{"country": "DE", "total": 100}],
        )
        text = generate_geographic_text(panel)
        assert text != ""
        assert "Kooperationsachse" not in text

    def test_zero_cross_border(self):
        panel = GeographicPanel(
            total_countries=3,
            country_distribution=[{"country": "DE", "total": 50}],
        )
        text = generate_geographic_text(panel)
        assert "grenzueberschreitend" not in text


# ---------------------------------------------------------------------------
# UC7: Research Impact
# ---------------------------------------------------------------------------


class TestGenerateResearchImpactText:
    """Tests fuer generate_research_impact_text (UC7)."""

    def test_empty_panel_returns_empty(self):
        panel = ResearchImpactPanel()
        assert generate_research_impact_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = ResearchImpactPanel(
            h_index=42,
            avg_citations=15.3,
            total_papers=200,
            influential_ratio=0.08,
            top_papers=[
                {"title": "A groundbreaking study on quantum computing",
                 "citations": 500, "year": 2020},
            ],
            top_venues=[
                {"venue": "Nature", "count": 25},
            ],
        )
        text = generate_research_impact_text(panel)
        assert text != ""
        assert "Banks" in text  # Scientific reference
        assert "42" in text  # h-index
        assert "200" in text  # total papers
        assert "Valenzuela" in text  # influential citation reference
        assert "Nature" in text  # top venue
        assert "Stichprobe" in text  # sampling caveat (200 papers)
        period_count = text.count(".")
        assert 4 <= period_count <= 8

    def test_below_200_no_sampling_caveat(self):
        panel = ResearchImpactPanel(
            h_index=10,
            avg_citations=5.0,
            total_papers=50,
        )
        text = generate_research_impact_text(panel)
        assert "Stichprobe" not in text

    def test_zero_influential_ratio(self):
        panel = ResearchImpactPanel(
            h_index=5,
            avg_citations=3.0,
            total_papers=20,
            influential_ratio=0.0,
        )
        text = generate_research_impact_text(panel)
        assert "Valenzuela" not in text

    def test_long_title_truncated(self):
        long_title = "A" * 120
        panel = ResearchImpactPanel(
            h_index=5,
            total_papers=10,
            avg_citations=2.0,
            top_papers=[{"title": long_title, "citations": 100}],
        )
        text = generate_research_impact_text(panel)
        assert "..." in text


# ---------------------------------------------------------------------------
# UC8: Temporal Dynamics
# ---------------------------------------------------------------------------


class TestGenerateTemporalText:
    """Tests fuer generate_temporal_text (UC8)."""

    def test_empty_panel_returns_empty(self):
        panel = TemporalPanel()
        assert generate_temporal_text(panel) == ""

    def test_full_panel_produces_text(self):
        panel = TemporalPanel(
            new_entrant_rate=0.35,
            persistence_rate=0.65,
            dominant_programme="RIA",
            actor_timeline=[
                {"name": "SIEMENS AG", "years_active": [2018, 2019, 2020],
                 "total_count": 150},
            ],
            entrant_persistence_trend=[
                {"year": 2019, "new_entrant_rate": 0.4, "persistence_rate": 0.6,
                 "total_actors": 50},
                {"year": 2020, "new_entrant_rate": 0.35, "persistence_rate": 0.65,
                 "total_actors": 55},
            ],
            technology_breadth=[
                {"year": 2018, "unique_cpc_sections": 5, "unique_cpc_subclasses": 20},
                {"year": 2019, "unique_cpc_sections": 6, "unique_cpc_subclasses": 25},
                {"year": 2020, "unique_cpc_sections": 6, "unique_cpc_subclasses": 30},
            ],
        )
        text = generate_temporal_text(panel)
        assert text != ""
        assert "Malerba" in text  # Scientific reference
        assert "35,0%" in text  # new entrant rate
        assert "65,0%" in text  # persistence rate
        assert "RIA" in text  # dominant programme
        assert "SIEMENS AG" in text  # top actor
        assert "ausgeweitet" in text  # breadth increasing
        period_count = text.count(".")
        assert 4 <= period_count <= 8

    def test_converging_breadth(self):
        panel = TemporalPanel(
            new_entrant_rate=0.2,
            persistence_rate=0.8,
            entrant_persistence_trend=[
                {"year": 2020, "total_actors": 30},
            ],
            technology_breadth=[
                {"year": 2018, "unique_cpc_sections": 7, "unique_cpc_subclasses": 40},
                {"year": 2020, "unique_cpc_sections": 5, "unique_cpc_subclasses": 25},
            ],
        )
        text = generate_temporal_text(panel)
        assert "konvergiert" in text

    def test_stable_breadth(self):
        panel = TemporalPanel(
            new_entrant_rate=0.3,
            persistence_rate=0.7,
            entrant_persistence_trend=[
                {"year": 2020, "total_actors": 30},
            ],
            technology_breadth=[
                {"year": 2018, "unique_cpc_sections": 5, "unique_cpc_subclasses": 20},
                {"year": 2020, "unique_cpc_sections": 5, "unique_cpc_subclasses": 20},
            ],
        )
        text = generate_temporal_text(panel)
        assert "stabil" in text

    def test_no_dominant_programme(self):
        panel = TemporalPanel(
            new_entrant_rate=0.5,
            persistence_rate=0.5,
            dominant_programme="",
            entrant_persistence_trend=[
                {"year": 2020, "total_actors": 10},
            ],
        )
        text = generate_temporal_text(panel)
        assert "Foerderinstrument" not in text

    def test_no_actor_timeline(self):
        panel = TemporalPanel(
            new_entrant_rate=0.3,
            persistence_rate=0.7,
            entrant_persistence_trend=[
                {"year": 2020, "total_actors": 10},
            ],
        )
        text = generate_temporal_text(panel)
        assert "aktivste Akteur" not in text


# ---------------------------------------------------------------------------
# Edge cases across all generators
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Uebergreifende Edge-Case-Tests."""

    def test_all_generators_handle_defaults(self):
        """Alle Generatoren geben '' bei Default-Panels zurueck."""
        assert generate_landscape_text(LandscapePanel()) == ""
        assert generate_maturity_text(MaturityPanel()) == ""
        assert generate_competitive_text(CompetitivePanel()) == ""
        assert generate_funding_text(FundingPanel()) == ""
        assert generate_cpc_flow_text(CpcFlowPanel()) == ""
        assert generate_geographic_text(GeographicPanel()) == ""
        assert generate_research_impact_text(ResearchImpactPanel()) == ""
        assert generate_temporal_text(TemporalPanel()) == ""

    def test_all_generators_return_string(self):
        """Alle Generatoren geben immer einen String zurueck."""
        panels = [
            LandscapePanel(total_patents=1),
            MaturityPanel(phase="Growing", phase_de="Wachsend"),
            CompetitivePanel(top_actors=[{"name": "X", "share": 0.5, "count": 10}]),
            FundingPanel(total_funding_eur=1000.0),
            CpcFlowPanel(
                matrix=[[1.0, 0.1], [0.1, 1.0]],
                labels=["A", "B"],
                total_patents_analyzed=10,
                total_connections=1,
            ),
            GeographicPanel(total_countries=1,
                            country_distribution=[{"country": "DE", "total": 5}]),
            ResearchImpactPanel(h_index=1, total_papers=1, avg_citations=1.0),
            TemporalPanel(
                new_entrant_rate=0.5, persistence_rate=0.5,
                entrant_persistence_trend=[{"year": 2020, "total_actors": 1}],
            ),
        ]
        generators = [
            generate_landscape_text,
            generate_maturity_text,
            generate_competitive_text,
            generate_funding_text,
            generate_cpc_flow_text,
            generate_geographic_text,
            generate_research_impact_text,
            generate_temporal_text,
        ]
        for panel, gen in zip(panels, generators, strict=True):
            result = gen(panel)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_no_double_spaces(self):
        """Kein Text darf doppelte Leerzeichen enthalten."""
        panel = LandscapePanel(
            total_patents=100, total_projects=50, total_publications=30,
            top_countries=[{"country": "DE", "total": 50}],
        )
        text = generate_landscape_text(panel)
        assert "  " not in text
