"""Repository fuer Zugriff auf die lokale Patent-Datenbank (patents.db)."""

from __future__ import annotations

import aiosqlite

from ti_radar.config import Settings


class PatentRepository:
    """Async SQLite-Zugriff auf die denormalisierte Patent-DB."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or Settings().patents_db_path

    async def search_by_technology(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 10_000,
    ) -> list[aiosqlite.Row]:
        """FTS5-Suche in Titel und CPC-Codes."""
        sql = """
            SELECT p.publication_number, p.country, p.title,
                   p.publication_date, p.applicant_names, p.applicant_countries,
                   p.cpc_codes, p.family_id
            FROM patents_fts fts
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.publication_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.publication_date <= ?"
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
        """Patentanzahl pro Jahr fuer eine Technologie."""
        sql = """
            SELECT SUBSTR(p.publication_date, 1, 4) AS year,
                   COUNT(*) AS count
            FROM patents_fts fts
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
              AND p.publication_date IS NOT NULL
              AND LENGTH(p.publication_date) >= 4
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND SUBSTR(p.publication_date, 1, 4) >= ?"
            params.append(str(start_year))
        if end_year:
            sql += " AND SUBSTR(p.publication_date, 1, 4) <= ?"
            params.append(str(end_year))

        sql += " GROUP BY year ORDER BY year"

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [{"year": int(row[0]), "count": row[1]} for row in await cursor.fetchall()]

    async def count_by_country(
        self, query: str, *, start_year: int | None = None, end_year: int | None = None
    ) -> list[dict[str, str | int]]:
        """Patentanzahl pro Land fuer eine Technologie."""
        sql = """
            SELECT p.country, COUNT(*) AS count
            FROM patents_fts fts
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.publication_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.publication_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY p.country ORDER BY count DESC LIMIT 20"

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [{"country": row[0], "count": row[1]} for row in await cursor.fetchall()]

    async def top_applicants(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, str | int]]:
        """Top-Anmelder fuer eine Technologie (normalisierte Tabellen).

        Nutzt die Tabellen 'applicants' + 'patent_applicants' fuer korrekte
        Aufschluesselung von Multi-Anmelder-Patenten. Fallback auf
        denormalisiertes Feld wenn Tabellen nicht existieren.
        """
        if await self._has_applicant_tables():
            return await self._top_applicants_normalized(
                query, start_year=start_year, end_year=end_year, limit=limit,
            )
        return await self._top_applicants_denormalized(
            query, start_year=start_year, end_year=end_year, limit=limit,
        )

    async def _has_applicant_tables(self) -> bool:
        """Pruefen ob die normalisierten Applicant-Tabellen existieren."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='patent_applicants'"
            )
            return await cursor.fetchone() is not None

    async def _top_applicants_normalized(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, str | int]]:
        """Top-Anmelder via normalisierte Tabellen (Multi-Applicant korrekt)."""
        sql = """
            SELECT a.normalized_name, COUNT(DISTINCT pa.patent_id) AS count
            FROM patents_fts fts
            JOIN patent_applicants pa ON pa.patent_id = fts.rowid
            JOIN applicants a ON a.id = pa.applicant_id
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.publication_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.publication_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY a.normalized_name ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [{"name": row[0], "count": row[1]} for row in await cursor.fetchall()]

    async def _top_applicants_denormalized(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, str | int]]:
        """Fallback: Top-Anmelder aus denormalisiertem Feld."""
        sql = """
            SELECT p.applicant_names, COUNT(*) AS count
            FROM patents_fts fts
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
              AND p.applicant_names IS NOT NULL
              AND p.applicant_names != ''
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.publication_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.publication_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " GROUP BY p.applicant_names ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            return [{"name": row[0], "count": row[1]} for row in await cursor.fetchall()]

    async def get_cpc_codes(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 10_000,
    ) -> list[str]:
        """CPC-Code-Strings aller Patente fuer eine Technologie."""
        sql = """
            SELECT p.cpc_codes
            FROM patents_fts fts
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
              AND p.cpc_codes IS NOT NULL
              AND p.cpc_codes != ''
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.publication_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.publication_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [str(row[0]) for row in rows if row[0]]

    async def get_cpc_codes_with_years(
        self,
        query: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 10_000,
    ) -> list[dict[str, str | int]]:
        """CPC-Code-Strings + Publikationsjahr fuer Co-Occurrence mit Zeitfilter."""
        sql = """
            SELECT p.cpc_codes, SUBSTR(p.publication_date, 1, 4) AS year
            FROM patents_fts fts
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
              AND p.cpc_codes IS NOT NULL
              AND p.cpc_codes != ''
              AND p.publication_date IS NOT NULL
              AND LENGTH(p.publication_date) >= 4
        """
        params: list[str | int] = [query]

        if start_year:
            sql += " AND p.publication_date >= ?"
            params.append(f"{start_year}-01-01")
        if end_year:
            sql += " AND p.publication_date <= ?"
            params.append(f"{end_year}-12-31")

        sql += " LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [
                {"cpc_codes": str(row[0]), "year": int(row[1])}
                for row in rows
                if row[0] and row[1]
            ]

    async def suggest_titles(self, prefix: str, limit: int = 500) -> list[str]:
        """Patent-Titel via FTS5-Prefix-Suche fuer Autocomplete."""
        fts_query = f'"{prefix}"*'
        sql = """
            SELECT p.title
            FROM patents_fts fts
            JOIN patents p ON p.id = fts.rowid
            WHERE patents_fts MATCH ?
            LIMIT ?
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql, [fts_query, limit])
            rows = await cursor.fetchall()
            return [str(row[0]) for row in rows if row[0]]

    async def get_last_full_year(self) -> int | None:
        """Letztes Jahr mit vollstaendigen Daten ermitteln.

        Prueft das maximale Publikationsdatum in der DB.
        Wenn der letzte Monat vor November liegt, gilt das Jahr
        als unvollstaendig und das Vorjahr wird zurueckgegeben.
        """
        sql = """
            SELECT MAX(publication_date) FROM patents
            WHERE publication_date IS NOT NULL
            AND LENGTH(publication_date) >= 7
        """
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(sql)
            row = await cursor.fetchone()
            if not row or not row[0]:
                return None
            max_date = str(row[0])
            try:
                max_year = int(max_date[:4])
                max_month = int(max_date[5:7])
            except (ValueError, IndexError):
                return None
            return max_year if max_month >= 11 else max_year - 1

    async def total_count(self) -> int:
        """Gesamtanzahl Patente in der DB."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM patents")
            row = await cursor.fetchone()
            return row[0] if row else 0
