"""GLEIF LEI Lookup Adapter mit persistentem SQLite-Cache."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL_DAYS = 90


class GleifAdapter:
    """Async-Adapter fuer die GLEIF API mit SQLite-Cache."""

    BASE_URL = "https://api.gleif.org/api/v1"
    TIMEOUT = 10.0

    def __init__(self, cache_db_path: str = "data/gleif_cache.db") -> None:
        self._cache_db = cache_db_path
        self._semaphore = asyncio.Semaphore(1)
        self._ensure_cache_table()

    def _ensure_cache_table(self) -> None:
        """Create cache table if it doesn't exist."""
        conn = sqlite3.connect(self._cache_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gleif_cache (
                raw_name TEXT PRIMARY KEY,
                lei TEXT,
                legal_name TEXT,
                country TEXT,
                city TEXT,
                resolved_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _get_cached(self, name: str) -> dict[str, Any] | None | str:
        """Check cache. Returns dict if hit, 'NEGATIVE' if negative cache, None if miss/expired."""
        conn = sqlite3.connect(self._cache_db)
        cursor = conn.execute(
            "SELECT lei, legal_name, country, city, resolved_at "
            "FROM gleif_cache WHERE raw_name = ?",
            (name.upper().strip(),),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        resolved_at = datetime.fromisoformat(row[4])
        if datetime.now() - resolved_at > timedelta(days=_CACHE_TTL_DAYS):
            return None

        if row[0] is None and row[1] is None:
            return "NEGATIVE"

        return {
            "lei": row[0],
            "legal_name": row[1],
            "country": row[2],
            "city": row[3],
        }

    def _write_cache(self, name: str, result: dict[str, Any] | None) -> None:
        """Write result to cache (including negative results)."""
        conn = sqlite3.connect(self._cache_db)
        now = datetime.now().isoformat()
        key = name.upper().strip()

        sql = (
            "INSERT OR REPLACE INTO gleif_cache "
            "(raw_name, lei, legal_name, country, city, resolved_at) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        if result:
            conn.execute(sql, (
                key, result.get("lei"), result.get("legal_name"),
                result.get("country"), result.get("city"), now,
            ))
        else:
            conn.execute(sql, (key, None, None, None, None, now))
        conn.commit()
        conn.close()

    async def resolve_entity(self, name: str) -> dict[str, Any] | None:
        """Resolve a single entity name to GLEIF LEI record."""
        cached = self._get_cached(name)
        if cached == "NEGATIVE":
            return None
        if isinstance(cached, dict):
            return cached

        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    t0 = time.monotonic()
                    resp = await client.get(
                        f"{self.BASE_URL}/lei-records",
                        params={"filter[entity.legalName]": name},
                    )
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    logger.info(
                        "GLEIF name='%s' -> %d (%dms)",
                        name[:30], resp.status_code, elapsed_ms,
                    )
                    resp.raise_for_status()
                    data: dict[str, Any] = resp.json()

                records = data.get("data", [])
                if not records:
                    self._write_cache(name, None)
                    return None

                entity = records[0]["attributes"]["entity"]
                result: dict[str, Any] = {
                    "lei": records[0]["attributes"]["lei"],
                    "legal_name": entity["legalName"]["name"],
                    "country": entity.get("legalAddress", {}).get("country", ""),
                    "city": entity.get("legalAddress", {}).get("city", ""),
                }
                self._write_cache(name, result)
                return result

            except Exception as e:
                logger.warning("GLEIF resolve failed for '%s': %s", name, e)
                return None

            finally:
                await asyncio.sleep(1.0)

    async def resolve_batch(
        self, names: list[str], max_api_calls: int = 20
    ) -> dict[str, dict[str, Any] | None]:
        """Resolve multiple names. Uses cache first, API for misses."""
        results: dict[str, dict[str, Any] | None] = {}
        to_resolve: list[str] = []

        for name in names:
            cached = self._get_cached(name)
            if cached == "NEGATIVE":
                results[name] = None
            elif isinstance(cached, dict):
                results[name] = cached
            else:
                to_resolve.append(name)

        for name in to_resolve[:max_api_calls]:
            results[name] = await self.resolve_entity(name)

        for name in to_resolve[max_api_calls:]:
            results[name] = None

        return results
