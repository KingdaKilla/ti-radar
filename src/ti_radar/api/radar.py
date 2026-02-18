"""POST /api/v1/radar — Zentraler Radar-Endpoint."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime

from fastapi import APIRouter

from ti_radar.api.schemas import (
    ExplainabilityMetadata,
    RadarRequest,
    RadarResponse,
)
from ti_radar.config import Settings
from ti_radar.domain.api_health import check_jwt_expiry, detect_runtime_failures
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository
from ti_radar.use_cases.competitive import analyze_competitive
from ti_radar.use_cases.cpc_flow import analyze_cpc_flow
from ti_radar.use_cases.funding import analyze_funding
from ti_radar.use_cases.geographic import analyze_geographic
from ti_radar.use_cases.landscape import analyze_landscape
from ti_radar.use_cases.maturity import analyze_maturity
from ti_radar.use_cases.research_impact import analyze_research_impact
from ti_radar.use_cases.temporal import analyze_temporal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Radar"])


@router.post("/radar", response_model=RadarResponse)
async def analyze_technology(request: RadarRequest) -> RadarResponse:
    """
    Technology Radar: Alle 8 Use Cases parallel ausfuehren.

    Gibt ein komplettes Dashboard-Objekt zurueck mit:
    - Landschaft (UC1): Patente + Projekte + Publikationen ueber Zeit
    - Reifegrad (UC2): S-Curve, Phase, Phasenklassifikation (Gao et al. 2013)
    - Wettbewerb (UC3): HHI, Top-Akteure, Marktanteile
    - Foerderung (UC4): EU-Foerderprogramme, CAGR, Projektgroessen
    - CPC-Fluss (UC5): CPC-Co-Klassifikation, Jaccard-Matrix
    - Geografie (UC6): Laenderverteilung, Staedte, Cross-Border
    - Forschungsimpact (UC7): h-Index, Zitationen, Top-Papers
    - Temporale Dynamik (UC8): Akteur-Dynamik, Programm-Evolution
    """
    t0 = time.monotonic()
    current_year = datetime.now().year
    start_year = current_year - request.years

    # Alle 8 UCs parallel ausfuehren (30s Timeout)
    results = await asyncio.wait_for(
        asyncio.gather(
            analyze_landscape(request.technology, start_year, current_year),
            analyze_maturity(request.technology, start_year, current_year),
            analyze_competitive(request.technology, start_year, current_year),
            analyze_funding(request.technology, start_year, current_year),
            analyze_cpc_flow(request.technology, start_year, current_year),
            analyze_geographic(request.technology, start_year, current_year),
            analyze_research_impact(request.technology, start_year, current_year),
            analyze_temporal(request.technology, start_year, current_year),
        ),
        timeout=30.0,
    )

    # Ergebnisse entpacken
    (
        landscape_result, maturity_result, competitive_result,
        funding_result, cpc_result, geographic_result,
        research_impact_result, temporal_result,
    ) = results
    landscape, l_sources, l_methods, l_warnings = landscape_result
    maturity, m_sources, m_methods, m_warnings = maturity_result
    competitive, c_sources, c_methods, c_warnings = competitive_result
    funding, f_sources, f_methods, f_warnings = funding_result
    cpc_flow, cp_sources, cp_methods, cp_warnings = cpc_result
    geographic, g_sources, g_methods, g_warnings = geographic_result
    research_impact, ri_sources, ri_methods, ri_warnings = research_impact_result
    temporal, t_sources, t_methods, t_warnings = temporal_result

    # Explainability aggregieren (Duplikate entfernen)
    all_sources = list(dict.fromkeys(
        l_sources + m_sources + c_sources + f_sources + cp_sources
        + g_sources + ri_sources + t_sources
    ))
    all_methods = list(dict.fromkeys(
        l_methods + m_methods + c_methods + f_methods + cp_methods
        + g_methods + ri_methods + t_methods
    ))
    all_warnings = (
        l_warnings + m_warnings + c_warnings + f_warnings + cp_warnings
        + g_warnings + ri_warnings + t_warnings
    )

    # Letztes vollstaendiges Datenjahr ermitteln
    data_complete_until: int | None = None
    settings = Settings()
    try:
        if settings.patents_db_available:
            repo = PatentRepository(settings.patents_db_path)
            data_complete_until = await repo.get_last_full_year()
    except Exception as exc:
        logger.warning("Could not determine last full year: %s", exc)

    # API-Key/Token Health Checks (lokal, 0ms)
    api_alerts = []
    openaire_alert = check_jwt_expiry(
        settings.openaire_access_token, "OpenAIRE",
    )
    if openaire_alert:
        api_alerts.append(openaire_alert)
    api_alerts.extend(detect_runtime_failures(all_warnings))

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    return RadarResponse(
        technology=request.technology,
        analysis_period=f"{start_year}-{current_year}",
        landscape=landscape,
        maturity=maturity,
        competitive=competitive,
        funding=funding,
        cpc_flow=cpc_flow,
        geographic=geographic,
        research_impact=research_impact,
        temporal=temporal,
        explainability=ExplainabilityMetadata(
            sources_used=all_sources,
            methods=all_methods,
            deterministic=True,
            warnings=all_warnings,
            api_alerts=api_alerts,
            query_time_ms=elapsed_ms,
            data_complete_until=data_complete_until,
        ),
    )
