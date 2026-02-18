"""Repository fuer Zugriff auf die lokale CORDIS-Datenbank (cordis.db)."""

from __future__ import annotations

import aiosqlite

from ti_radar.config import Settings


class CordisRepository:
    """Async SQLite-Zugriff auf die CORDIS-Projekt-DB."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or Settings().cordis_db_path

    async def search_projects(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 10_000,
    ) -> list[aiosqlite.Row]:
        """FTS5-Suche in Titel, Objective und Keywords."""
        sql = """
            SELECT p.id, p.framework, p.acronym, p.title,
                   p.start_date, p.end_date, p.status,
                   p.total_cost, p.ec_max_contribution,
                   p.funding_scheme, p.keywords
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            WHERE projects_fts MATCH ?
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            return list(await cursor.fetchall())

    async def count_by_year(
        self, query: str, *, start_year: int | None = None, end_year: int | None = None
    ) -> list[dict[str, int]]:
        """Projektanzahl pro Startjahr fuer eine Technologie."""
        sql = """
            SELECT SUBSTR(p.start_date, 1, 4) AS year,
                   COUNT(*) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            WHERE projects_fts MATCH ?
              AND p.start_date IS NOT NULL
              AND LENGTH(p.start_date) >= 4
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) >= ?"
            params.append(str(start_year))
        if end_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) <= ?"
            params.append(str(end_year))

        sql += " GROUP BY year ORDER BY year"

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [{"year": int(row[0]), "count": row[1]} for row in await cursor.fetchall()]

    async def count_by_country(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, str | int]]:
        """Projektanzahl pro Land (aus Organizations-Tabelle)."""
        sql = """
            SELECT o.country, COUNT(DISTINCT o.project_id) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o ON o.project_id = p.id
            WHERE projects_fts MATCH ?
              AND o.country IS NOT NULL
              AND o.country != ''
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY o.country ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [{"country": row[0], "count": row[1]} for row in await cursor.fetchall()]

    async def top_organizations(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, str | int]]:
        """Top-Organisationen fuer eine Technologie."""
        sql = """
            SELECT o.name, COUNT(DISTINCT o.project_id) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o ON o.project_id = p.id
            WHERE projects_fts MATCH ?
              AND o.name IS NOT NULL
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY o.name ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [{"name": row[0], "count": row[1]} for row in await cursor.fetchall()]

    async def funding_by_year(
        self, query: str, *, start_year: int | None = None, end_year: int | None = None
    ) -> list[dict[str, int | float]]:
        """EU-Foerderung pro Jahr fuer eine Technologie."""
        sql = """
            SELECT SUBSTR(p.start_date, 1, 4) AS year,
                   SUM(p.ec_max_contribution) AS funding,
                   COUNT(*) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            WHERE projects_fts MATCH ?
              AND p.start_date IS NOT NULL
              AND LENGTH(p.start_date) >= 4
              AND p.ec_max_contribution IS NOT NULL
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) >= ?"
            params.append(str(start_year))
        if end_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) <= ?"
            params.append(str(end_year))

        sql += " GROUP BY year ORDER BY year"

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {"year": int(row[0]), "funding": row[1] or 0.0, "count": row[2]}
                for row in await cursor.fetchall()
            ]

    async def funding_by_programme(
        self, query: str, *, start_year: int | None = None, end_year: int | None = None
    ) -> list[dict[str, str | int | float]]:
        """EU-Foerderung pro Framework-Programm fuer eine Technologie."""
        sql = """
            SELECT p.framework,
                   SUM(p.ec_max_contribution) AS funding,
                   COUNT(*) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            WHERE projects_fts MATCH ?
              AND p.ec_max_contribution IS NOT NULL
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY p.framework ORDER BY funding DESC"

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {"programme": row[0], "funding": row[1] or 0.0, "count": row[2]}
                for row in await cursor.fetchall()
            ]

    async def suggest_titles(self, prefix: str, limit: int = 500) -> list[str]:
        """Projekt-Titel via FTS5-Prefix-Suche fuer Autocomplete."""
        fts_query = f'"{prefix}"*'
        sql = """
            SELECT p.title
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            WHERE projects_fts MATCH ?
            LIMIT ?
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, [fts_query, limit])
            rows = await cursor.fetchall()
            return [str(row[0]) for row in rows if row[0]]

    async def funding_by_year_and_programme(
        self, query: str, *, start_year: int | None = None, end_year: int | None = None
    ) -> list[dict[str, str | int | float]]:
        """EU-Foerderung pro Jahr UND Programm fuer Stacked-Bar-Visualisierung."""
        sql = """
            SELECT SUBSTR(p.start_date, 1, 4) AS year,
                   p.framework,
                   SUM(p.ec_max_contribution) AS funding,
                   COUNT(*) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            WHERE projects_fts MATCH ?
              AND p.start_date IS NOT NULL
              AND LENGTH(p.start_date) >= 4
              AND p.ec_max_contribution IS NOT NULL
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) >= ?"
            params.append(str(start_year))
        if end_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) <= ?"
            params.append(str(end_year))

        sql += " GROUP BY year, p.framework ORDER BY year, p.framework"

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {
                    "year": int(row[0]),
                    "programme": row[1] or "UNKNOWN",
                    "funding": row[2] or 0.0,
                    "count": row[3],
                }
                for row in await cursor.fetchall()
            ]

    async def get_last_full_year(self) -> int | None:
        """Letztes Jahr mit vollstaendigen Daten ermitteln.

        Prueft das maximale start_date in der DB.
        Wenn der letzte Monat vor November liegt, gilt das Jahr
        als unvollstaendig und das Vorjahr wird zurueckgegeben.
        """
        sql = """
            SELECT MAX(start_date) FROM projects
            WHERE start_date IS NOT NULL
            AND LENGTH(start_date) >= 7
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql)
            row = await cursor.fetchone()
            if not row or not row[0]:
                return None

            date_str = str(row[0])
            try:
                year = int(date_str[:4])
                month = int(date_str[5:7])
            except (ValueError, IndexError):
                return None

            return year if month >= 11 else year - 1

    async def co_participation(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
    ) -> list[dict[str, str | int]]:
        """Co-Partizipation: Zwei Organisationen im selben Projekt."""
        sql = """
            SELECT o1.name AS actor_a,
                   o2.name AS actor_b,
                   COUNT(DISTINCT o1.project_id) AS co_count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o1 ON o1.project_id = p.id
            JOIN organizations o2 ON o2.project_id = o1.project_id
                                   AND o2.id > o1.id
            WHERE projects_fts MATCH ?
              AND o1.name IS NOT NULL AND o2.name IS NOT NULL
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY o1.name, o2.name"
        sql += " ORDER BY co_count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {"actor_a": row[0], "actor_b": row[1], "co_count": row[2]}
                for row in await cursor.fetchall()
            ]

    async def organizations_with_programme(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 500,
    ) -> list[dict[str, str | int]]:
        """Organisationen mit Foerderprogramm-Zuordnung fuer Sankey."""
        sql = """
            SELECT o.name, p.framework, COUNT(DISTINCT p.id) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o ON o.project_id = p.id
            WHERE projects_fts MATCH ?
              AND o.name IS NOT NULL
              AND p.framework IS NOT NULL
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY o.name, p.framework ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {"name": row[0], "programme": row[1], "count": row[2]}
                for row in await cursor.fetchall()
            ]

    async def top_organizations_with_country(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, str | int]]:
        """Top-Organisationen mit Land, SME-Flag und Rolle."""
        sql = """
            SELECT o.name, o.country,
                   COUNT(DISTINCT o.project_id) AS count,
                   MAX(CASE WHEN UPPER(o.sme) = 'YES' THEN 1 ELSE 0 END) AS is_sme,
                   MAX(CASE WHEN o.role = 'coordinator' THEN 1 ELSE 0 END) AS is_coordinator
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o ON o.project_id = p.id
            WHERE projects_fts MATCH ?
              AND o.name IS NOT NULL
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY o.name, o.country ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {
                    "name": row[0],
                    "country": row[1] or "",
                    "count": row[2],
                    "is_sme": bool(row[3]),
                    "is_coordinator": bool(row[4]),
                }
                for row in await cursor.fetchall()
            ]

    async def orgs_by_city(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, str | int]]:
        """Organisationen nach Stadt gruppiert."""
        sql = """
            SELECT o.city, o.country, COUNT(DISTINCT o.project_id) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o ON o.project_id = p.id
            WHERE projects_fts MATCH ?
              AND o.city IS NOT NULL AND o.city != ''
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY o.city, o.country ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {"city": row[0], "country": row[1] or "", "count": row[2]}
                for row in await cursor.fetchall()
            ]

    async def cross_border_projects(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        min_countries: int = 3,
    ) -> dict[str, int | float]:
        """Anteil Cross-Border-Projekte (Projekte mit >= min_countries Laendern)."""
        base_where = "WHERE projects_fts MATCH ?"
        params_base: list[str | int] = [query]

        if start_year:
            base_where += " AND p.start_date >= ?"
            params_base.append(f"{start_year}-01-01")
        if end_year:
            base_where += " AND p.start_date <= ?"
            params_base.append(f"{end_year}-12-31")

        sql_total = f"""
            SELECT COUNT(DISTINCT p.id)
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            {base_where}
        """

        sql_cross = f"""
            SELECT COUNT(*) FROM (
                SELECT o.project_id
                FROM projects_fts fts
                JOIN projects p ON p.id = fts.rowid
                JOIN organizations o ON o.project_id = p.id
                {base_where}
                  AND o.country IS NOT NULL AND o.country != ''
                GROUP BY o.project_id
                HAVING COUNT(DISTINCT o.country) >= ?
            )
        """
        cross_params = list(params_base) + [min_countries]

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql_total, params_base)
            row = await cursor.fetchone()
            total = row[0] if row else 0

            cursor2 = await db.execute(sql_cross, cross_params)
            row2 = await cursor2.fetchone()
            cross = row2[0] if row2 else 0

        share = cross / total if total > 0 else 0.0
        return {
            "total_projects": total,
            "cross_border_count": cross,
            "cross_border_share": round(share, 4),
        }

    async def country_collaboration_pairs(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 30,
    ) -> list[dict[str, str | int]]:
        """Laender-Paare aus CORDIS-Projekt-Kooperationen."""
        sql = """
            SELECT o1.country AS country_a,
                   o2.country AS country_b,
                   COUNT(DISTINCT o1.project_id) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o1 ON o1.project_id = p.id
            JOIN organizations o2 ON o2.project_id = o1.project_id
                                   AND o2.country > o1.country
            WHERE projects_fts MATCH ?
              AND o1.country IS NOT NULL AND o1.country != ''
              AND o2.country IS NOT NULL AND o2.country != ''
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.start_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.start_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY o1.country, o2.country ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {"country_a": row[0], "country_b": row[1], "count": row[2]}
                for row in await cursor.fetchall()
            ]

    async def orgs_by_year(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
    ) -> list[dict[str, str | int]]:
        """Organisationen pro Jahr fuer Temporal-Analyse."""
        sql = """
            SELECT o.name,
                   SUBSTR(p.start_date, 1, 4) AS year,
                   COUNT(DISTINCT p.id) AS count
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            JOIN organizations o ON o.project_id = p.id
            WHERE projects_fts MATCH ?
              AND o.name IS NOT NULL
              AND p.start_date IS NOT NULL AND LENGTH(p.start_date) >= 4
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) >= ?"
            params.append(str(start_year))
        if end_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) <= ?"
            params.append(str(end_year))

        sql += " GROUP BY o.name, year ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {"name": row[0], "year": int(row[1]), "count": row[2]}
                for row in await cursor.fetchall()
            ]

    async def funding_by_instrument(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, str | int | float]]:
        """Foerderung nach Instrument (funding_scheme) pro Jahr."""
        sql = """
            SELECT p.funding_scheme,
                   SUBSTR(p.start_date, 1, 4) AS year,
                   COUNT(*) AS count,
                   SUM(COALESCE(p.ec_max_contribution, 0)) AS funding
            FROM projects_fts fts
            JOIN projects p ON p.id = fts.rowid
            WHERE projects_fts MATCH ?
              AND p.funding_scheme IS NOT NULL AND p.funding_scheme != ''
              AND p.start_date IS NOT NULL AND LENGTH(p.start_date) >= 4
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) >= ?"
            params.append(str(start_year))
        if end_year:
            sql += " AND SUBSTR(p.start_date, 1, 4) <= ?"
            params.append(str(end_year))

        sql += " GROUP BY p.funding_scheme, year ORDER BY year, count DESC"

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [
                {
                    "scheme": row[0],
                    "year": int(row[1]),
                    "count": row[2],
                    "funding": round(float(row[3] or 0), 2),
                }
                for row in await cursor.fetchall()
            ]

    async def total_count(self) -> int:
        """Gesamtanzahl Projekte in der DB."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM projects")
            row = await cursor.fetchone()
            return row[0] if row else 0
