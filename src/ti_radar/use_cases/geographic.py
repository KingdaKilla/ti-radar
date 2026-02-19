"""UC6: Geographic Intelligence — Wo wird die Technologie entwickelt?"""

from __future__ import annotations

import logging

from ti_radar.config import Settings
from ti_radar.domain.metrics import merge_country_data
from ti_radar.domain.models import GeographicPanel
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository
from ti_radar.use_cases._helpers import effective_patent_end_year

logger = logging.getLogger(__name__)


async def analyze_geographic(
    technology: str,
    start_year: int,
    end_year: int,
    *,
    settings: Settings | None = None,
    patent_repo: PatentRepository | None = None,
    cordis_repo: CordisRepository | None = None,
) -> tuple[GeographicPanel, list[str], list[str], list[str]]:
    """UC6: Geografische Verteilung analysieren.

    Args:
        technology: Suchbegriff
        start_year: Startjahr
        end_year: Endjahr
        settings: Optional — Settings-Instanz (Default: neu erzeugt)
        patent_repo: Optional — PatentRepository (Default: aus Settings)
        cordis_repo: Optional — CordisRepository (Default: aus Settings)

    Returns:
        Tuple aus (Panel, sources_used, methods, warnings)
    """
    if settings is None:
        settings = Settings()
    sources: list[str] = []
    methods: list[str] = []
    warnings: list[str] = []

    patent_countries: list[dict[str, str | int]] = []
    applicant_countries: list[dict[str, str | int]] = []
    cordis_countries: list[dict[str, str | int]] = []
    city_data: list[dict[str, str | int]] = []
    collab_pairs: list[dict[str, str | int]] = []
    cross_border: dict[str, int | float] = {}

    # Patent-Daten
    if settings.patents_db_available:
        try:
            if patent_repo is None:
                patent_repo = PatentRepository(settings.patents_db_path)
            patent_end = await effective_patent_end_year(
                patent_repo, end_year, warnings,
            )
            patent_countries = await patent_repo.count_by_country(
                technology, start_year=start_year, end_year=patent_end
            )
            applicant_countries = await patent_repo.count_by_applicant_country(
                technology, start_year=start_year, end_year=patent_end
            )
            if patent_countries or applicant_countries:
                sources.append("EPO DOCDB (lokal)")
        except Exception as e:
            logger.warning("Geographic patent query failed: %s", e)
            warnings.append(f"Patent-Geo-Abfrage fehlgeschlagen: {e}")

    # CORDIS-Daten
    if settings.cordis_db_available:
        try:
            if cordis_repo is None:
                cordis_repo = CordisRepository(settings.cordis_db_path)
            cordis_countries = await cordis_repo.count_by_country(
                technology, start_year=start_year, end_year=end_year
            )
            city_data = await cordis_repo.orgs_by_city(
                technology, start_year=start_year, end_year=end_year
            )
            collab_pairs = await cordis_repo.country_collaboration_pairs(
                technology, start_year=start_year, end_year=end_year
            )
            cross_border = await cordis_repo.cross_border_projects(
                technology, start_year=start_year, end_year=end_year, min_countries=3
            )
            if cordis_countries:
                sources.append("CORDIS (lokal)")
        except Exception as e:
            logger.warning("Geographic CORDIS query failed: %s", e)
            warnings.append(f"CORDIS-Geo-Abfrage fehlgeschlagen: {e}")

    # Laender zusammenfuehren (prefer applicant_countries over filing country)
    country_source = applicant_countries if applicant_countries else patent_countries
    country_dist = merge_country_data(country_source, cordis_countries)

    total_countries = len(country_dist)
    total_cities = len(city_data)
    cross_share = float(cross_border.get("cross_border_share", 0.0))

    methods.append("Laender-Aggregation (Patent-Anmeldelaender + CORDIS-Organisationsstandorte)")
    if collab_pairs:
        methods.append("Laender-Kooperationspaare (CORDIS-Projektpartner)")

    panel = GeographicPanel(
        total_countries=total_countries,
        total_cities=total_cities,
        cross_border_share=round(cross_share, 4),
        country_distribution=country_dist,
        city_distribution=city_data,
        collaboration_pairs=collab_pairs,
    )

    return panel, sources, methods, warnings


