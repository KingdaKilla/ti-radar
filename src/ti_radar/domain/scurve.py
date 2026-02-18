"""S-Curve Fitting via logistische und Gompertz-Funktion.

Implementiert zwei Wachstumskurven zur Reifegrad-Analyse:
- Logistisch: f(x) = L / (1 + exp(-k*(x - x0))) — symmetrisch
- Gompertz: f(x) = L * exp(-b * exp(-k*(x - x0))) — asymmetrisch

Phasenklassifikation nach Gao et al. (2013). Modellselektion nach Franses (1994).
Ensemble-Selektion via R².
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)


def logistic_function(
    x: NDArray[np.float64], L: float, k: float, x0: float  # noqa: N803
) -> NDArray[np.float64]:
    """
    Logistische Funktion: f(x) = L / (1 + exp(-k * (x - x0))).

    Args:
        x: Zeitpunkte (Jahre)
        L: Saettigungsniveau (Obergrenze)
        k: Wachstumsrate (Steilheit)
        x0: Wendepunkt (Jahr mit staerkstem Wachstum)
    """
    result: NDArray[np.float64] = L / (1.0 + np.exp(-k * (x - x0)))
    return result


def estimate_initial_params(
    years: NDArray[np.float64],
    cumulative: NDArray[np.float64],
) -> tuple[float, float, float]:
    """
    Initiale Parameter fuer curve_fit schaetzen.

    Returns:
        (L0, k0, x0) — Startwerte fuer Saettigung, Wachstumsrate, Wendepunkt
    """
    y_max = float(cumulative[-1])
    sat = y_max * 1.5 if y_max > 0 else 1.0

    # x0: Jahr, in dem cumulative am naechsten an sat/2 liegt
    half_sat = sat / 2.0
    idx_mid = int(np.argmin(np.abs(cumulative - half_sat)))
    x0 = float(years[idx_mid])

    # k0: Aus 10%-90% Transitionsbreite schaetzen
    threshold_10 = sat * 0.1
    threshold_90 = sat * 0.9
    idx_10 = int(np.argmin(np.abs(cumulative - threshold_10)))
    idx_90 = int(np.argmin(np.abs(cumulative - threshold_90)))
    width = float(years[idx_90] - years[idx_10])
    k0 = 4.0 / width if width > 0 else 0.5

    return sat, k0, x0


def fit_s_curve(
    years: list[int],
    cumulative: list[int],
) -> dict[str, Any] | None:
    """
    S-Curve an kumulative Zeitreihe fitten.

    Args:
        years: Liste von Jahren
        cumulative: Kumulative Werte (monoton steigend)

    Returns:
        Dict mit L, k, x0, r_squared, fitted_values, maturity_percent
        oder None bei Fehler / unzureichenden Daten.
    """
    if len(years) < 3 or len(cumulative) < 3:
        return None

    x = np.array(years, dtype=np.float64)
    y = np.array(cumulative, dtype=np.float64)

    # Nur Nullen → kein Fit moeglich
    if y[-1] <= 0:
        return None

    try:
        sat0, k0, x0_init = estimate_initial_params(x, y)

        # Bounds: L > 0, k > 0, x0 innerhalb des Zeitraums
        lower = [y[-1] * 0.5, 0.001, float(x[0]) - 10.0]
        upper = [y[-1] * 10.0, 5.0, float(x[-1]) + 10.0]

        popt, _ = curve_fit(
            logistic_function,
            x,
            y,
            p0=[sat0, k0, x0_init],
            bounds=(lower, upper),
            method="trf",
            maxfev=5000,
        )

        sat_fit, k_fit, x0_fit = float(popt[0]), float(popt[1]), float(popt[2])

        # Gefittete Werte
        fitted = logistic_function(x, sat_fit, k_fit, x0_fit)

        # R² berechnen
        ss_res = float(np.sum((y - fitted) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Maturity Percent: aktueller Wert / Saettigung
        maturity_percent = (float(y[-1]) / sat_fit) * 100.0 if sat_fit > 0 else 0.0

        return {
            "L": round(sat_fit, 2),
            "k": round(k_fit, 6),
            "x0": round(x0_fit, 2),
            "r_squared": round(r_squared, 4),
            "maturity_percent": round(min(maturity_percent, 100.0), 2),
            "model": "Logistic",
            "fitted_values": [
                {"year": int(years[i]), "fitted": round(float(fitted[i]), 1)}
                for i in range(len(years))
            ],
        }

    except (RuntimeError, ValueError, TypeError) as e:
        logger.warning("S-Curve fit fehlgeschlagen: %s", e)
        return None


def gompertz_function(
    x: NDArray[np.float64], L: float, b: float, k: float, x0: float  # noqa: N803
) -> NDArray[np.float64]:
    """
    Gompertz-Funktion: f(x) = L * exp(-b * exp(-k * (x - x0))).

    Asymmetrische S-Kurve — Wachstum verlangsamt sich frueher als bei Logistic.

    Args:
        x: Zeitpunkte (Jahre)
        L: Saettigungsniveau (Obergrenze)
        b: Verschiebungsparameter (bestimmt den Start)
        k: Wachstumsrate
        x0: Referenz-Zeitpunkt
    """
    result: NDArray[np.float64] = L * np.exp(-b * np.exp(-k * (x - x0)))
    return result


def fit_gompertz(
    years: list[int],
    cumulative: list[int],
) -> dict[str, Any] | None:
    """
    Gompertz-Curve an kumulative Zeitreihe fitten.

    Args:
        years: Liste von Jahren
        cumulative: Kumulative Werte (monoton steigend)

    Returns:
        Dict mit L, b, k, x0, r_squared, fitted_values, maturity_percent, model
        oder None bei Fehler / unzureichenden Daten.
    """
    if len(years) < 3 or len(cumulative) < 3:
        return None

    x = np.array(years, dtype=np.float64)
    y = np.array(cumulative, dtype=np.float64)

    if y[-1] <= 0:
        return None

    try:
        y_max = float(y[-1])
        sat0 = y_max * 1.5 if y_max > 0 else 1.0

        # Initiale Parameter: b so, dass Start bei ~5% von L liegt
        b0 = 5.0
        # k aus 10-90% Transitionsbreite
        idx_10 = int(np.argmin(np.abs(y - sat0 * 0.1)))
        idx_90 = int(np.argmin(np.abs(y - sat0 * 0.9)))
        width = float(x[idx_90] - x[idx_10])
        k0 = 4.0 / width if width > 0 else 0.3
        x0_init = float(x[0])

        lower = [y_max * 0.5, 0.1, 0.001, float(x[0]) - 10.0]
        upper = [y_max * 10.0, 50.0, 5.0, float(x[-1]) + 10.0]

        popt, _ = curve_fit(
            gompertz_function,
            x,
            y,
            p0=[sat0, b0, k0, x0_init],
            bounds=(lower, upper),
            method="trf",
            maxfev=5000,
        )

        sat_fit, b_fit, k_fit, x0_fit = (
            float(popt[0]), float(popt[1]), float(popt[2]), float(popt[3])
        )

        fitted = gompertz_function(x, sat_fit, b_fit, k_fit, x0_fit)

        ss_res = float(np.sum((y - fitted) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        maturity_percent = (float(y[-1]) / sat_fit) * 100.0 if sat_fit > 0 else 0.0

        return {
            "L": round(sat_fit, 2),
            "k": round(k_fit, 6),
            "x0": round(x0_fit, 2),
            "r_squared": round(r_squared, 4),
            "maturity_percent": round(min(maturity_percent, 100.0), 2),
            "model": "Gompertz",
            "fitted_values": [
                {"year": int(years[i]), "fitted": round(float(fitted[i]), 1)}
                for i in range(len(years))
            ],
        }

    except (RuntimeError, ValueError, TypeError) as e:
        logger.warning("Gompertz fit fehlgeschlagen: %s", e)
        return None


def fit_best_model(
    years: list[int],
    cumulative: list[int],
) -> dict[str, Any] | None:
    """
    Beide Modelle (Logistic + Gompertz) fitten, besseres R² auswaehlen.

    Returns:
        Dict des besseren Modells (mit 'model' Feld) oder None.
    """
    logistic_result = fit_s_curve(years, cumulative)
    gompertz_result = fit_gompertz(years, cumulative)

    if logistic_result is None and gompertz_result is None:
        return None
    if logistic_result is None:
        return gompertz_result
    if gompertz_result is None:
        return logistic_result

    # Besseres R² gewinnt
    if gompertz_result["r_squared"] > logistic_result["r_squared"]:
        return gompertz_result
    return logistic_result
