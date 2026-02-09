"""Tests fuer S-Curve Fitting (domain/scurve.py)."""

import numpy as np
import pytest

from ti_radar.domain.scurve import (
    estimate_initial_params,
    fit_best_model,
    fit_gompertz,
    fit_s_curve,
    gompertz_function,
    logistic_function,
)


class TestLogisticFunction:
    """Tests fuer die logistische Funktion."""

    def test_basic_shape(self):
        x = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
        result = logistic_function(x, L=100.0, k=0.5, x0=10.0)
        # Monoton steigend
        for i in range(len(result) - 1):
            assert result[i] < result[i + 1]

    def test_saturation_level(self):
        x = np.array([100.0])
        result = logistic_function(x, L=1000.0, k=1.0, x0=0.0)
        assert result[0] == pytest.approx(1000.0, rel=0.01)

    def test_inflection_point(self):
        x = np.array([10.0])
        result = logistic_function(x, L=100.0, k=1.0, x0=10.0)
        assert result[0] == pytest.approx(50.0, abs=0.01)

    def test_symmetry_around_inflection(self):
        L, k, x0 = 100.0, 0.5, 10.0
        left = logistic_function(np.array([x0 - 5.0]), L, k, x0)[0]
        right = logistic_function(np.array([x0 + 5.0]), L, k, x0)[0]
        assert left + right == pytest.approx(L, abs=0.01)


class TestEstimateInitialParams:
    """Tests fuer die initiale Parameterschaetzung."""

    def test_returns_three_values(self):
        years = np.array([2010.0, 2011.0, 2012.0, 2013.0, 2014.0])
        cumulative = np.array([10.0, 30.0, 60.0, 80.0, 95.0])
        L0, k0, x0 = estimate_initial_params(years, cumulative)
        assert L0 > 0
        assert k0 > 0
        assert 2010 <= x0 <= 2014

    def test_l0_above_max(self):
        years = np.array([2010.0, 2011.0, 2012.0])
        cumulative = np.array([10.0, 50.0, 100.0])
        L0, _, _ = estimate_initial_params(years, cumulative)
        assert L0 > 100.0  # Muss groesser als max sein


class TestFitSCurve:
    """Tests fuer den S-Curve-Fit."""

    def test_synthetic_logistic_data(self):
        """Perfekte logistische Daten → R² > 0.99."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        perfect = logistic_function(x, L=1000.0, k=0.5, x0=2010.0)
        cumulative = [int(v) for v in perfect]

        result = fit_s_curve(years, cumulative)
        assert result is not None
        assert result["r_squared"] > 0.99
        assert result["L"] == pytest.approx(1000.0, rel=0.1)
        assert result["maturity_percent"] > 0

    def test_growing_data(self):
        """Realistische wachsende Daten → Fit moeglich."""
        years = list(range(2015, 2026))
        cumulative = [5, 15, 35, 70, 130, 220, 350, 500, 680, 860, 1000]

        result = fit_s_curve(years, cumulative)
        assert result is not None
        assert result["r_squared"] > 0.5
        assert len(result["fitted_values"]) == 11
        assert result["maturity_percent"] > 0

    def test_insufficient_data(self):
        """Weniger als 3 Datenpunkte → None."""
        assert fit_s_curve([2020, 2021], [10, 20]) is None
        assert fit_s_curve([2020], [10]) is None
        assert fit_s_curve([], []) is None

    def test_all_zeros(self):
        """Nur Nullen → None."""
        result = fit_s_curve([2020, 2021, 2022, 2023], [0, 0, 0, 0])
        assert result is None

    def test_constant_data(self):
        """Konstante Werte → Fit moeglich, aber niedriges R²."""
        years = list(range(2015, 2025))
        cumulative = [100] * 10
        result = fit_s_curve(years, cumulative)
        # Kann None sein oder niedriges R² — beides akzeptabel
        if result is not None:
            assert result["r_squared"] >= 0

    def test_result_structure(self):
        """Alle erwarteten Keys im Ergebnis."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        perfect = logistic_function(x, L=500.0, k=0.3, x0=2010.0)
        cumulative = [int(v) for v in perfect]

        result = fit_s_curve(years, cumulative)
        assert result is not None
        assert "L" in result
        assert "k" in result
        assert "x0" in result
        assert "r_squared" in result
        assert "maturity_percent" in result
        assert "fitted_values" in result

    def test_fitted_values_match_years(self):
        """Fitted values haben gleiche Laenge wie Eingabe-Jahre."""
        years = list(range(2010, 2020))
        cumulative = [10, 25, 50, 90, 160, 260, 380, 500, 600, 680]

        result = fit_s_curve(years, cumulative)
        assert result is not None
        assert len(result["fitted_values"]) == len(years)
        for fv in result["fitted_values"]:
            assert "year" in fv
            assert "fitted" in fv

    def test_maturity_percent_bounded(self):
        """Maturity percent liegt zwischen 0 und 100."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        perfect = logistic_function(x, L=1000.0, k=0.5, x0=2010.0)
        cumulative = [int(v) for v in perfect]

        result = fit_s_curve(years, cumulative)
        assert result is not None
        assert 0 <= result["maturity_percent"] <= 100

    def test_result_contains_model(self):
        """Result enthält 'model' Feld mit Wert 'Logistic'."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        perfect = logistic_function(x, L=500.0, k=0.3, x0=2010.0)
        cumulative = [int(v) for v in perfect]

        result = fit_s_curve(years, cumulative)
        assert result is not None
        assert result["model"] == "Logistic"


class TestGompertzFunction:
    """Tests fuer die Gompertz-Funktion."""

    def test_monotonically_increasing(self):
        x = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
        result = gompertz_function(x, L=100.0, b=5.0, k=0.3, x0=0.0)
        for i in range(len(result) - 1):
            assert result[i] < result[i + 1]

    def test_saturation_level(self):
        x = np.array([200.0])
        result = gompertz_function(x, L=1000.0, b=5.0, k=1.0, x0=0.0)
        assert result[0] == pytest.approx(1000.0, rel=0.01)

    def test_starts_near_zero(self):
        x = np.array([0.0])
        result = gompertz_function(x, L=1000.0, b=10.0, k=0.5, x0=0.0)
        assert result[0] < 100  # Weit unter Saettigung

    def test_bounded_output(self):
        x = np.linspace(0, 50, 100)
        result = gompertz_function(x, L=500.0, b=5.0, k=0.3, x0=0.0)
        assert np.all(result >= 0)
        assert np.all(result <= 500.0 * 1.01)  # Leichte Toleranz


class TestFitGompertz:
    """Tests fuer den Gompertz-Fit."""

    def test_synthetic_gompertz_data(self):
        """Perfekte Gompertz-Daten → R² > 0.99."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        perfect = gompertz_function(x, L=1000.0, b=5.0, k=0.3, x0=2000.0)
        cumulative = [max(1, int(v)) for v in perfect]

        result = fit_gompertz(years, cumulative)
        assert result is not None
        assert result["r_squared"] > 0.95
        assert result["model"] == "Gompertz"
        assert result["maturity_percent"] > 0

    def test_growing_data(self):
        """Realistische wachsende Daten → Fit moeglich."""
        years = list(range(2015, 2026))
        cumulative = [5, 15, 35, 70, 130, 220, 350, 500, 680, 860, 1000]

        result = fit_gompertz(years, cumulative)
        assert result is not None
        assert result["r_squared"] > 0.5
        assert result["model"] == "Gompertz"

    def test_insufficient_data(self):
        """Weniger als 3 Datenpunkte → None."""
        assert fit_gompertz([2020, 2021], [10, 20]) is None
        assert fit_gompertz([], []) is None

    def test_all_zeros(self):
        """Nur Nullen → None."""
        result = fit_gompertz([2020, 2021, 2022, 2023], [0, 0, 0, 0])
        assert result is None

    def test_result_structure(self):
        """Alle erwarteten Keys im Ergebnis."""
        years = list(range(2015, 2026))
        cumulative = [5, 15, 35, 70, 130, 220, 350, 500, 680, 860, 1000]

        result = fit_gompertz(years, cumulative)
        assert result is not None
        assert "L" in result
        assert "k" in result
        assert "r_squared" in result
        assert "maturity_percent" in result
        assert "model" in result
        assert "fitted_values" in result


class TestFitBestModel:
    """Tests fuer die Ensemble-Modellselektion."""

    def test_selects_better_model(self):
        """Gibt das Modell mit hoeherem R² zurueck."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        perfect = logistic_function(x, L=1000.0, k=0.5, x0=2010.0)
        cumulative = [int(v) for v in perfect]

        result = fit_best_model(years, cumulative)
        assert result is not None
        assert result["model"] in ("Logistic", "Gompertz")
        assert result["r_squared"] > 0.9

    def test_insufficient_data_returns_none(self):
        """Wenige Datenpunkte → None."""
        assert fit_best_model([2020, 2021], [10, 20]) is None

    def test_all_zeros_returns_none(self):
        """Nur Nullen → None."""
        assert fit_best_model([2020, 2021, 2022, 2023], [0, 0, 0, 0]) is None

    def test_result_has_model_field(self):
        """Result enthält immer 'model' Feld."""
        years = list(range(2015, 2026))
        cumulative = [5, 15, 35, 70, 130, 220, 350, 500, 680, 860, 1000]

        result = fit_best_model(years, cumulative)
        assert result is not None
        assert "model" in result
        assert result["model"] in ("Logistic", "Gompertz")

    def test_growing_data_picks_model(self):
        """Realistische Daten → mindestens ein Modell erfolgreich."""
        years = list(range(2010, 2025))
        cumulative = [10, 25, 50, 90, 160, 260, 380, 500, 630, 750, 850, 920, 960, 985, 995]

        result = fit_best_model(years, cumulative)
        assert result is not None
        assert result["r_squared"] > 0.8
