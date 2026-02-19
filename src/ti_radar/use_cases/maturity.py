"""UC2: Technology Maturity Assessment — Reifegrad-Analyse mit S-Curve."""

from __future__ import annotations

import itertools
import logging
from typing import Any

from ti_radar.config import Settings
from ti_radar.domain.analysis_text import generate_maturity_text
from ti_radar.domain.metrics import cagr, classify_maturity_phase, s_curve_confidence
from ti_radar.domain.models import MaturityPanel
from ti_radar.domain.scurve import fit_best_model
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository
from ti_radar.use_cases._helpers import effective_patent_end_year as _effective_patent_end_year

logger = logging.getLogger(__name__)


async def analyze_maturity(
    technology: str,
    start_year: int,
    end_year: int,
    *,
    settings: Settings | None = None,
    patent_repo: PatentRepository | None = None,
) -> tuple[MaturityPanel, list[str], list[str], list[str]]:
    """
    UC2: Reifegrad einer Technologie analysieren.

    Basiert auf kumulativen Patent-Zeitreihen:
    - S-Curve-Fit (Levenberg-Marquardt) fuer Reifegradbestimmung
    - Phasen-Klassifikation nach Gao et al. (2013)
    - Patent-Familien-Deduplizierung (OECD, 2009)

    Args:
        technology: Suchbegriff
        start_year: Startjahr
        end_year: Endjahr
        settings: Optional — Settings-Instanz (Default: neu erzeugt)
        patent_repo: Optional — PatentRepository (Default: aus Settings)
    """
    if settings is None:
        settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    patent_years: dict[int, int] = {}
    effective_end_year = end_year

    # Patent-Zeitreihe (dedupliziert nach Patent-Familien)
    if settings.patents_db_available:
        try:
            if patent_repo is None:
                patent_repo = PatentRepository(settings.patents_db_path)
            # Primaer: unique families (OECD 2009 — Dopplungen vermeiden)
            rows = await patent_repo.count_families_by_year(
                technology, start_year=start_year, end_year=end_year
            )
            patent_years = {r["year"]: r["count"] for r in rows}
            # Fallback auf count_by_year falls keine family_id vorhanden
            if not patent_years:
                rows = await patent_repo.count_by_year(
                    technology, start_year=start_year, end_year=end_year
                )
                patent_years = {r["year"]: r["count"] for r in rows}
            else:
                methods.append("Patent-Familien-Deduplizierung (DISTINCT family_id)")
            if patent_years:
                sources.append("EPO DOCDB (lokal)")

            # Letztes vollstaendiges Jahr ermitteln (fuer S-Curve)
            effective_end_year = await _effective_patent_end_year(
                patent_repo, end_year, warnings,
            )
        except Exception as e:
            logger.warning("Maturity patent query failed: %s", e)
            warnings.append(f"Patent-Abfrage fehlgeschlagen: {e}")

    # Patent-Zeitreihe + kumulative Summe
    all_years = sorted(set(range(start_year, end_year + 1)))
    combined: list[int] = []
    time_series: list[dict[str, Any]] = []

    for year in all_years:
        p = patent_years.get(year, 0)
        combined.append(p)

    cumulative = list(itertools.accumulate(combined))

    for i, year in enumerate(all_years):
        time_series.append({
            "year": year,
            "patents": combined[i],
            "cumulative": cumulative[i],
        })

    # S-Curve und CAGR: nur vollstaendige Jahre verwenden
    fit_end_idx = len(all_years)
    for i, y in enumerate(all_years):
        if y > effective_end_year:
            fit_end_idx = i
            break
    fit_combined = combined[:fit_end_idx]
    fit_years = all_years[:fit_end_idx]
    fit_cumulative = cumulative[:fit_end_idx]

    # CAGR (ueber Patent-Zeitreihe, Kalenderjahr-Spanne)
    non_zero_indices = [i for i, c in enumerate(fit_combined) if c > 0]
    growth_rate = 0.0
    if len(non_zero_indices) >= 2:
        first_idx, last_idx = non_zero_indices[0], non_zero_indices[-1]
        year_span = fit_years[last_idx] - fit_years[first_idx]
        if year_span > 0:
            growth_rate = cagr(
                fit_combined[first_idx], fit_combined[last_idx], year_span,
            )
            methods.append(
                f"CAGR ueber {year_span} Jahre "
                f"({fit_years[first_idx]}-{fit_years[last_idx]})"
            )

    # S-Curve-Fit auf kumulative Daten (nur vollstaendige Jahre)
    # Mindestens 30 kumulative Patente fuer sinnvollen Fit
    min_patents_for_fit = 30
    s_curve_result: dict[str, Any] | None = None
    if fit_cumulative and fit_cumulative[-1] >= min_patents_for_fit:
        s_curve_result = fit_best_model(fit_years, fit_cumulative)
    elif fit_cumulative and fit_cumulative[-1] > 0:
        warnings.append(
            f"Zu wenige Patente ({fit_cumulative[-1]}) fuer S-Curve-Fit "
            f"(Minimum: {min_patents_for_fit}) — Fallback auf Heuristik"
        )
    s_curve_fitted: list[dict[str, Any]] = []
    maturity_pct = 0.0
    sat_level = 0.0
    inflection = 0.0
    r_sq = 0.0

    model_name = ""
    if s_curve_result is not None:
        maturity_pct = s_curve_result["maturity_percent"]
        sat_level = s_curve_result["L"]
        inflection = s_curve_result["x0"]
        r_sq = s_curve_result["r_squared"]
        s_curve_fitted = s_curve_result["fitted_values"]
        model_name = s_curve_result.get("model", "Logistic")
        methods.append(f"S-Curve ({model_name}, R\u00b2={r_sq})")

        # Gewichtete Konfidenz (R², Datenpunkte, Stichprobe)
        confidence = s_curve_confidence(
            r_sq, len(fit_years), fit_cumulative[-1] if fit_cumulative else 0
        )

        # Phase via maturity_percent (Gao et al. 2013)
        phase_en, phase_de, _ = classify_maturity_phase(
            combined, maturity_percent=maturity_pct, r_squared=r_sq
        )
        methods.append("Phasenklassifikation (Gao et al. 2013)")
    else:
        # Fallback: Heuristik
        phase_en, phase_de, confidence = classify_maturity_phase(combined)
        methods.append("Phasenklassifikation (Wachstumsmuster-Heuristik)")
        if (cumulative and cumulative[-1] > 0
                and fit_cumulative and fit_cumulative[-1] >= min_patents_for_fit):
            warnings.append("S-Curve-Fit fehlgeschlagen — Fallback auf Heuristik")

    panel = MaturityPanel(
        phase=phase_en,
        phase_de=phase_de,
        confidence=confidence,
        cagr=round(growth_rate, 2),
        maturity_percent=maturity_pct,
        saturation_level=sat_level,
        inflection_year=inflection,
        r_squared=r_sq,
        fit_model=model_name,
        time_series=time_series,
        s_curve_fitted=s_curve_fitted,
    )
    panel.analysis_text = generate_maturity_text(panel)

    return panel, sources, methods, warnings
