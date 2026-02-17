"""POST /api/v1/radar — Zentraler Radar-Endpoint."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

from fastapi import APIRouter

from ti_radar.api.schemas import (
    ExplainabilityMetadata,
    RadarRequest,
    RadarResponse,
)
from ti_radar.use_cases.competitive import analyze_competitive
from ti_radar.use_cases.cpc_flow import analyze_cpc_flow
from ti_radar.use_cases.funding import analyze_funding
from ti_radar.use_cases.landscape import analyze_landscape
from ti_radar.use_cases.maturity import analyze_maturity

router = APIRouter(prefix="/api/v1", tags=["Radar"])


@router.post("/radar", response_model=RadarResponse)
async def analyze_technology(request: RadarRequest) -> RadarResponse:
    """
    Technology Radar: Alle 4 Use Cases parallel ausfuehren.

    Gibt ein komplettes Dashboard-Objekt zurueck mit:
    - Reifegrad (UC2): S-Curve, Phase, CAGR, Martini-John
    - Landschaft (UC1): Patente + Projekte + Publikationen ueber Zeit
    - Wettbewerb (UC3): HHI, Top-Akteure, Marktanteile
    - Foerderung (UC4): EU-Foerderprogramme, CAGR, Projektgroessen
    """
    t0 = time.monotonic()
    current_year = datetime.now().year
    start_year = current_year - request.years

    # Alle 5 UCs parallel ausfuehren (30s Timeout)
    results = await asyncio.wait_for(
        asyncio.gather(
            analyze_landscape(request.technology, start_year, current_year),
            analyze_maturity(request.technology, start_year, current_year),
            analyze_competitive(request.technology, start_year, current_year),
            analyze_funding(request.technology, start_year, current_year),
            analyze_cpc_flow(request.technology, start_year, current_year),
        ),
        timeout=30.0,
    )

    # Ergebnisse entpacken
    landscape_result, maturity_result, competitive_result, funding_result, cpc_result = results
    landscape, l_sources, l_methods, l_warnings = landscape_result
    maturity, m_sources, m_methods, m_warnings = maturity_result
    competitive, c_sources, c_methods, c_warnings = competitive_result
    funding, f_sources, f_methods, f_warnings = funding_result
    cpc_flow, cp_sources, cp_methods, cp_warnings = cpc_result

    # Explainability aggregieren (Duplikate entfernen)
    all_sources = list(dict.fromkeys(
        l_sources + m_sources + c_sources + f_sources + cp_sources
    ))
    all_methods = list(dict.fromkeys(
        l_methods + m_methods + c_methods + f_methods + cp_methods
    ))
    all_warnings = l_warnings + m_warnings + c_warnings + f_warnings + cp_warnings

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    return RadarResponse(
        technology=request.technology,
        analysis_period=f"{start_year}-{current_year}",
        landscape=landscape,
        maturity=maturity,
        competitive=competitive,
        funding=funding,
        cpc_flow=cpc_flow,
        explainability=ExplainabilityMetadata(
            sources_used=all_sources,
            methods=all_methods,
            deterministic=True,
            warnings=all_warnings,
            query_time_ms=elapsed_ms,
        ),
    )
