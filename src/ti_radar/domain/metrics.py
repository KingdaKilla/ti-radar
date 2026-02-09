"""Deterministische Metriken fuer Technology Intelligence.

Reine Funktionen ohne IO — testbar, auditierbar, reproduzierbar.
"""

from __future__ import annotations

import math


def cagr(first_value: float, last_value: float, periods: int) -> float:
    """
    Compound Annual Growth Rate.

    Formula: ((V_final / V_initial)^(1/n) - 1) * 100

    Returns percentage (e.g. 12.5 for 12.5% growth).
    Returns 0.0 if inputs are invalid.
    """
    if periods <= 0 or first_value <= 0 or last_value <= 0:
        return 0.0
    return (math.pow(last_value / first_value, 1.0 / periods) - 1.0) * 100.0


def hhi_index(shares: list[float]) -> float:
    """
    Herfindahl-Hirschman Index fuer Marktkonzentration.

    Formula: sum(share_i^2) * 10000
    Input: Liste von Marktanteilen (0.0 bis 1.0)
    Output: HHI-Wert (0 bis 10000)

    Interpretation:
    - < 1500: Geringe Konzentration
    - 1500-2500: Moderate Konzentration
    - > 2500: Hohe Konzentration
    """
    if not shares:
        return 0.0
    return sum(s * s for s in shares) * 10_000


def hhi_concentration_level(hhi: float) -> tuple[str, str]:
    """HHI-Wert in Konzentrationsstufe uebersetzen (EN, DE)."""
    if hhi < 1500:
        return "Low", "Gering"
    if hhi < 2500:
        return "Moderate", "Moderat"
    return "High", "Hoch"


def martini_john_ratio(patents: int, publications: int) -> float:
    """
    Martini-John Ratio: Patents / Publications.

    Misst den Kommerzialisierungsgrad einer Technologie.
    - > 1.0: Starke Kommerzialisierung
    - ~ 1.0: Ausgeglichen
    - < 1.0: Forschungsdominiert

    Verwendet projects als Proxy fuer publications wenn noetig.
    Returns 0.0 wenn publications == 0.
    """
    if publications <= 0:
        return 0.0
    return patents / publications


def s_curve_confidence(
    r_squared: float,
    n_years: int,
    total_patents: int,
) -> float:
    """
    Gewichtete Konfidenz fuer S-Curve-basierte Phasenklassifikation.

    Beruecksichtigt:
    - R² (Guete des Fits): 60% Gewicht
    - Datenabdeckung (Jahre): 20% Gewicht (15+ Jahre = voll)
    - Stichprobengroesse (Patente): 20% Gewicht (200+ Patente = voll)

    Returns: Wert zwischen 0.1 und 0.95
    """
    data_factor = min(1.0, n_years / 15.0)
    sample_factor = min(1.0, total_patents / 200.0)
    raw = (r_squared or 0.0) * 0.6 + data_factor * 0.2 + sample_factor * 0.2
    return round(min(0.95, max(0.1, raw)), 2)


def classify_maturity_phase(
    yearly_counts: list[int],
    maturity_percent: float | None = None,
    r_squared: float | None = None,
) -> tuple[str, str, float]:
    """
    Reifegrad-Phase klassifizieren.

    Wenn maturity_percent gegeben (aus S-Curve-Fit): Schwellwerte nach Lee et al. (2016).
    Sonst: Fallback auf Wachstumsmuster-Heuristik.

    Returns:
        (phase_en, phase_de, confidence)
    """
    # S-Curve-basierte Klassifikation (bevorzugt)
    if maturity_percent is not None:
        confidence = min(0.95, r_squared or 0.5)
        if maturity_percent < 10.0:
            return "Emerging", "Aufkommend", round(confidence, 2)
        if maturity_percent < 50.0:
            return "Growing", "Wachsend", round(confidence, 2)
        if maturity_percent < 90.0:
            return "Mature", "Ausgereift", round(confidence, 2)
        return "Declining", "Sättigung", round(confidence, 2)

    # Fallback: Wachstumsmuster-Heuristik
    if not yearly_counts or len(yearly_counts) < 3:
        return "Unknown", "Unbekannt", 0.0

    n = len(yearly_counts)

    # Durchschnitte fuer erste und zweite Haelfte
    mid = n // 2
    first_half = yearly_counts[:mid] if mid > 0 else yearly_counts[:1]
    second_half = yearly_counts[mid:]

    avg_first = sum(first_half) / len(first_half) if first_half else 0
    avg_second = sum(second_half) / len(second_half) if second_half else 0

    # Letzte 3 Jahre Trend
    recent = yearly_counts[-3:]
    if len(recent) >= 2 and recent[0] > 0:
        recent_growth = (recent[-1] - recent[0]) / recent[0]
    else:
        recent_growth = 0.0

    # Gesamttrend
    if avg_first > 0:
        overall_growth = (avg_second - avg_first) / avg_first
    else:
        overall_growth = 1.0 if avg_second > 0 else 0.0

    # Varianz in zweiter Haelfte (Stabilitaet)
    if second_half and avg_second > 0:
        variance = sum((x - avg_second) ** 2 for x in second_half) / len(second_half)
        cv = math.sqrt(variance) / avg_second  # Coefficient of Variation
    else:
        cv = 1.0

    # Klassifikation
    total = sum(yearly_counts)
    if total == 0:
        return "Unknown", "Unbekannt", 0.0

    if overall_growth > 0.5 and recent_growth > 0.1:
        phase_en, phase_de = "Emerging", "Aufkommend"
        confidence = min(0.9, 0.5 + overall_growth * 0.3)
    elif overall_growth > 0.1 and recent_growth > -0.1:
        phase_en, phase_de = "Growing", "Wachsend"
        confidence = min(0.9, 0.5 + (1.0 - cv) * 0.3)
    elif abs(overall_growth) <= 0.2 and cv < 0.4:
        phase_en, phase_de = "Mature", "Ausgereift"
        confidence = min(0.9, 0.6 + (1.0 - cv) * 0.3)
    elif overall_growth < -0.1 or recent_growth < -0.2:
        phase_en, phase_de = "Declining", "Rückläufig"
        confidence = min(0.9, 0.5 + abs(overall_growth) * 0.3)
    else:
        phase_en, phase_de = "Growing", "Wachsend"
        confidence = 0.4

    return phase_en, phase_de, round(confidence, 2)
