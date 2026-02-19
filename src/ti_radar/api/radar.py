"""POST /api/v1/radar — Zentraler Radar-Endpoint."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter

from ti_radar.api.schemas import (
    ExplainabilityMetadata,
    RadarRequest,
    RadarResponse,
)
from ti_radar.config import Settings
from ti_radar.domain.api_health import check_jwt_expiry, detect_runtime_failures
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
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
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

    # Composition Root: Settings + Repos einmal erzeugen, an alle UCs weiterreichen
    settings = Settings()
    patent_repo: PatentRepository | None = None
    cordis_repo: CordisRepository | None = None
    if settings.patents_db_available:
        patent_repo = PatentRepository(settings.patents_db_path)
    if settings.cordis_db_available:
        cordis_repo = CordisRepository(settings.cordis_db_path)

    tech = request.technology

    # Alle 8 UCs parallel ausfuehren (per-UC Timeout, Graceful Degradation)
    # UC5 (CPC-Jaccard) benoetigt Self-Join auf patent_cpc (237M Zeilen)
    # Timeout auf 30s wie andere UCs — bei Timeout: leeres Panel + Warnung
    default_timeout = 30.0
    cpc_timeout = 30.0

    uc_tasks_with_timeout: list[tuple[Any, float]] = [
        (analyze_landscape(
            tech, start_year, current_year,
            settings=settings, patent_repo=patent_repo, cordis_repo=cordis_repo,
        ), default_timeout),
        (analyze_maturity(
            tech, start_year, current_year,
            settings=settings, patent_repo=patent_repo,
        ), default_timeout),
        (analyze_competitive(
            tech, start_year, current_year,
            settings=settings, patent_repo=patent_repo, cordis_repo=cordis_repo,
        ), default_timeout),
        (analyze_funding(
            tech, start_year, current_year,
            settings=settings, cordis_repo=cordis_repo,
        ), default_timeout),
        (analyze_cpc_flow(
            tech, start_year, current_year,
            settings=settings, patent_repo=patent_repo,
        ), cpc_timeout),
        (analyze_geographic(
            tech, start_year, current_year,
            settings=settings, patent_repo=patent_repo, cordis_repo=cordis_repo,
        ), default_timeout),
        (analyze_research_impact(
            tech, start_year, current_year,
            settings=settings,
        ), default_timeout),
        (analyze_temporal(
            tech, start_year, current_year,
            settings=settings, patent_repo=patent_repo, cordis_repo=cordis_repo,
        ), default_timeout),
    ]
    results = await asyncio.gather(
        *[asyncio.wait_for(t, timeout=to) for t, to in uc_tasks_with_timeout],
        return_exceptions=True,
    )

    # Ergebnisse entpacken (Graceful Degradation: fehlgeschlagene UCs -> leere Panels)
    uc_names = [
        "Landscape", "Maturity", "Competitive", "Funding",
        "CPC-Flow", "Geographic", "Research-Impact", "Temporal",
    ]
    empty_panels = [
        LandscapePanel(), MaturityPanel(), CompetitivePanel(), FundingPanel(),
        CpcFlowPanel(), GeographicPanel(), ResearchImpactPanel(), TemporalPanel(),
    ]
    panels = []
    all_sources: list[str] = []
    all_methods: list[str] = []
    all_warnings: list[str] = []

    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            err_type = type(result).__name__
            logger.warning("UC %s fehlgeschlagen: %s: %s", uc_names[i], err_type, result)
            panels.append(empty_panels[i])
            all_warnings.append(f"{uc_names[i]}: Timeout oder Fehler ({err_type})")
        else:
            panel, sources, methods, warnings = result
            panels.append(panel)
            all_sources.extend(sources)
            all_methods.extend(methods)
            all_warnings.extend(warnings)

    (landscape, maturity, competitive, funding,
     cpc_flow, geographic, research_impact, temporal) = panels

    # Duplikate entfernen
    all_sources = list(dict.fromkeys(all_sources))
    all_methods = list(dict.fromkeys(all_methods))

    # Letztes vollstaendiges Datenjahr ermitteln
    data_complete_until: int | None = None
    try:
        if patent_repo is not None:
            data_complete_until = await patent_repo.get_last_full_year()
    except Exception as exc:
        logger.warning("Could not determine last full year: %s", exc)

    # API-Key/Token Health Checks (lokal, 0ms)
    api_alerts = []
    openaire_alert = check_jwt_expiry(
        settings.openaire_access_token, "OpenAIRE",
        has_refresh_token=bool(settings.openaire_refresh_token),
    )
    if openaire_alert:
        api_alerts.append(openaire_alert)
    api_alerts.extend(detect_runtime_failures(all_warnings))

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    return RadarResponse(
        technology=request.technology,
        analysis_period=f"{start_year}-{current_year}",
        landscape=cast(LandscapePanel, landscape),
        maturity=cast(MaturityPanel, maturity),
        competitive=cast(CompetitivePanel, competitive),
        funding=cast(FundingPanel, funding),
        cpc_flow=cast(CpcFlowPanel, cpc_flow),
        geographic=cast(GeographicPanel, geographic),
        research_impact=cast(ResearchImpactPanel, research_impact),
        temporal=cast(TemporalPanel, temporal),
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
