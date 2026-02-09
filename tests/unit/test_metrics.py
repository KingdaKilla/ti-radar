"""Tests fuer deterministische Metriken (domain/metrics.py)."""

import math

import pytest

from ti_radar.domain.metrics import (
    cagr,
    classify_maturity_phase,
    hhi_concentration_level,
    hhi_index,
    martini_john_ratio,
    s_curve_confidence,
)


# --- CAGR ---


class TestCAGR:
    """Tests fuer Compound Annual Growth Rate."""

    def test_positive_growth(self):
        result = cagr(100, 200, 5)
        assert result == pytest.approx(14.87, abs=0.01)

    def test_no_growth(self):
        assert cagr(100, 100, 5) == pytest.approx(0.0)

    def test_negative_growth(self):
        result = cagr(200, 100, 5)
        assert result < 0

    def test_one_period(self):
        result = cagr(100, 150, 1)
        assert result == pytest.approx(50.0)

    def test_zero_periods_returns_zero(self):
        assert cagr(100, 200, 0) == 0.0

    def test_negative_periods_returns_zero(self):
        assert cagr(100, 200, -1) == 0.0

    def test_zero_first_value_returns_zero(self):
        assert cagr(0, 200, 5) == 0.0

    def test_zero_last_value_returns_zero(self):
        assert cagr(100, 0, 5) == 0.0

    def test_negative_values_returns_zero(self):
        assert cagr(-10, 200, 5) == 0.0

    def test_large_growth(self):
        result = cagr(1, 1000, 10)
        assert result > 0
        assert math.isfinite(result)


# --- HHI Index ---


class TestHHI:
    """Tests fuer Herfindahl-Hirschman Index."""

    def test_monopoly(self):
        assert hhi_index([1.0]) == pytest.approx(10_000)

    def test_duopoly_equal(self):
        assert hhi_index([0.5, 0.5]) == pytest.approx(5_000)

    def test_fragmented_market(self):
        shares = [0.1] * 10
        assert hhi_index(shares) == pytest.approx(1_000)

    def test_empty_returns_zero(self):
        assert hhi_index([]) == 0.0

    def test_realistic_market(self):
        shares = [0.3, 0.25, 0.2, 0.15, 0.1]
        result = hhi_index(shares)
        assert 0 < result < 10_000

    def test_single_dominant(self):
        shares = [0.9, 0.05, 0.05]
        result = hhi_index(shares)
        assert result > 8_000  # Hoch konzentriert


# --- HHI Concentration Level ---


class TestHHILevel:
    """Tests fuer HHI-Konzentrationsstufen."""

    def test_low(self):
        en, de = hhi_concentration_level(500)
        assert en == "Low"
        assert de == "Gering"

    def test_moderate(self):
        en, de = hhi_concentration_level(2000)
        assert en == "Moderate"
        assert de == "Moderat"

    def test_high(self):
        en, de = hhi_concentration_level(5000)
        assert en == "High"
        assert de == "Hoch"

    def test_boundary_low_moderate(self):
        en, _ = hhi_concentration_level(1499)
        assert en == "Low"
        en, _ = hhi_concentration_level(1500)
        assert en == "Moderate"

    def test_boundary_moderate_high(self):
        en, _ = hhi_concentration_level(2499)
        assert en == "Moderate"
        en, _ = hhi_concentration_level(2500)
        assert en == "High"

    def test_zero(self):
        en, _ = hhi_concentration_level(0)
        assert en == "Low"

    def test_max(self):
        en, _ = hhi_concentration_level(10_000)
        assert en == "High"


# --- Martini-John Ratio ---


class TestMartiniJohn:
    """Tests fuer Martini-John Ratio (Patents/Publications)."""

    def test_balanced(self):
        assert martini_john_ratio(100, 100) == pytest.approx(1.0)

    def test_commercial(self):
        result = martini_john_ratio(300, 100)
        assert result > 1.0

    def test_research_dominant(self):
        result = martini_john_ratio(50, 200)
        assert result < 1.0

    def test_zero_publications_returns_zero(self):
        assert martini_john_ratio(100, 0) == 0.0

    def test_negative_publications_returns_zero(self):
        assert martini_john_ratio(100, -1) == 0.0

    def test_zero_patents(self):
        assert martini_john_ratio(0, 100) == pytest.approx(0.0)


# --- Maturity Phase Classification ---


class TestClassifyMaturity:
    """Tests fuer Reifegrad-Klassifikation."""

    def test_empty_returns_unknown(self):
        phase, phase_de, conf = classify_maturity_phase([])
        assert phase == "Unknown"
        assert conf == 0.0

    def test_too_short_returns_unknown(self):
        phase, _, conf = classify_maturity_phase([1, 2])
        assert phase == "Unknown"
        assert conf == 0.0

    def test_emerging_pattern(self):
        # Starkes Wachstum: 1, 2, 5, 12, 30, 60, 120
        counts = [1, 2, 5, 12, 30, 60, 120]
        phase, phase_de, conf = classify_maturity_phase(counts)
        assert phase == "Emerging"
        assert phase_de == "Aufkommend"
        assert 0.0 < conf <= 0.9

    def test_growing_pattern(self):
        # Moderates Wachstum
        counts = [10, 12, 15, 18, 20, 22, 25, 28, 30, 33]
        phase, _, conf = classify_maturity_phase(counts)
        assert phase in ("Growing", "Emerging")
        assert conf > 0

    def test_mature_pattern(self):
        # Stabil, geringe Varianz
        counts = [100, 102, 98, 101, 99, 100, 103, 97, 101, 100]
        phase, phase_de, conf = classify_maturity_phase(counts)
        assert phase == "Mature"
        assert phase_de == "Ausgereift"
        assert conf > 0.5

    def test_declining_pattern(self):
        # Abnehmend
        counts = [100, 90, 75, 60, 50, 40, 30, 20]
        phase, phase_de, conf = classify_maturity_phase(counts)
        assert phase == "Declining"
        assert phase_de == "Rückläufig"
        assert conf > 0

    def test_all_zeros_returns_unknown(self):
        phase, _, conf = classify_maturity_phase([0, 0, 0, 0, 0])
        assert phase == "Unknown"
        assert conf == 0.0

    def test_confidence_never_exceeds_0_9(self):
        counts = [1, 5, 20, 80, 300, 1000, 5000]
        _, _, conf = classify_maturity_phase(counts)
        assert conf <= 0.9

    def test_returns_three_values(self):
        result = classify_maturity_phase([10, 20, 30])
        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)
        assert isinstance(result[2], float)


class TestClassifyMaturitySCurve:
    """Tests fuer S-Curve-basierte Phasenklassifikation (maturity_percent)."""

    def test_emerging_phase(self):
        phase, phase_de, _ = classify_maturity_phase([1, 2, 3], maturity_percent=5.0)
        assert phase == "Emerging"
        assert phase_de == "Aufkommend"

    def test_growing_phase(self):
        phase, _, _ = classify_maturity_phase([1, 2, 3], maturity_percent=30.0)
        assert phase == "Growing"

    def test_mature_phase(self):
        phase, phase_de, _ = classify_maturity_phase([1, 2, 3], maturity_percent=70.0)
        assert phase == "Mature"
        assert phase_de == "Ausgereift"

    def test_declining_phase(self):
        phase, phase_de, _ = classify_maturity_phase([1, 2, 3], maturity_percent=95.0)
        assert phase == "Declining"
        assert phase_de == "Sättigung"

    def test_boundary_10(self):
        phase, _, _ = classify_maturity_phase([1, 2, 3], maturity_percent=9.9)
        assert phase == "Emerging"
        phase, _, _ = classify_maturity_phase([1, 2, 3], maturity_percent=10.0)
        assert phase == "Growing"

    def test_boundary_50(self):
        phase, _, _ = classify_maturity_phase([1, 2, 3], maturity_percent=49.9)
        assert phase == "Growing"
        phase, _, _ = classify_maturity_phase([1, 2, 3], maturity_percent=50.0)
        assert phase == "Mature"

    def test_boundary_90(self):
        phase, _, _ = classify_maturity_phase([1, 2, 3], maturity_percent=89.9)
        assert phase == "Mature"
        phase, _, _ = classify_maturity_phase([1, 2, 3], maturity_percent=90.0)
        assert phase == "Declining"

    def test_confidence_from_r_squared(self):
        _, _, conf = classify_maturity_phase(
            [1, 2, 3], maturity_percent=50.0, r_squared=0.85
        )
        assert conf == pytest.approx(0.85, abs=0.01)

    def test_confidence_capped_at_0_95(self):
        _, _, conf = classify_maturity_phase(
            [1, 2, 3], maturity_percent=50.0, r_squared=0.99
        )
        assert conf <= 0.95


class TestSCurveConfidence:
    """Tests fuer gewichtete S-Curve-Konfidenzberechnung."""

    def test_high_r_squared_high_data(self):
        """Hoher R², viele Daten → hohe Konfidenz."""
        conf = s_curve_confidence(r_squared=0.95, n_years=20, total_patents=500)
        assert conf >= 0.8

    def test_low_r_squared(self):
        """Niedriger R² → niedrige Konfidenz."""
        conf = s_curve_confidence(r_squared=0.2, n_years=20, total_patents=500)
        assert conf < 0.6

    def test_few_years(self):
        """Wenige Jahre → reduzierte Konfidenz."""
        conf_many = s_curve_confidence(r_squared=0.9, n_years=20, total_patents=500)
        conf_few = s_curve_confidence(r_squared=0.9, n_years=4, total_patents=500)
        assert conf_few < conf_many

    def test_few_patents(self):
        """Wenige Patente → reduzierte Konfidenz."""
        conf_many = s_curve_confidence(r_squared=0.9, n_years=15, total_patents=500)
        conf_few = s_curve_confidence(r_squared=0.9, n_years=15, total_patents=40)
        assert conf_few < conf_many

    def test_lower_bound(self):
        """Minimum ist 0.1."""
        conf = s_curve_confidence(r_squared=0.0, n_years=1, total_patents=1)
        assert conf >= 0.1

    def test_upper_bound(self):
        """Maximum ist 0.95."""
        conf = s_curve_confidence(r_squared=1.0, n_years=30, total_patents=10000)
        assert conf <= 0.95

    def test_monotone_with_r_squared(self):
        """Konfidenz steigt monoton mit R²."""
        c1 = s_curve_confidence(0.3, 15, 200)
        c2 = s_curve_confidence(0.6, 15, 200)
        c3 = s_curve_confidence(0.9, 15, 200)
        assert c1 < c2 < c3
