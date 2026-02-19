"""Shared Hilfsfunktionen fuer Use Cases.

Reduziert Boilerplate-Duplikation ueber die 8 UC-Module hinweg.
"""

from __future__ import annotations

from ti_radar.infrastructure.repositories.patent_repo import PatentRepository


async def effective_patent_end_year(
    repo: PatentRepository, end_year: int, warnings: list[str]
) -> int:
    """Ermittelt das letzte vollstaendige Patent-Datenjahr.

    Fuegt eine Warnung hinzu, wenn Daten ab einem bestimmten Jahr
    unvollstaendig sind. Gibt das effektive Endjahr zurueck.
    """
    last_full = await repo.get_last_full_year()
    if last_full is not None and last_full < end_year:
        warnings.append(
            f"Patent-Daten bis {last_full} vollstaendig "
            f"(ab {last_full + 1} unvollstaendig)"
        )
        return last_full
    return end_year
