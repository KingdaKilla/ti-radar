"""OpenAIRE Search API Adapter fuer Publikationsdaten."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenAIREAdapter:
    """Async-Adapter fuer die OpenAIRE Search API (Publikationen)."""

    BASE_URL = "https://api.openaire.eu/search/publications"
    TIMEOUT = 10.0

    def __init__(self, access_token: str = "") -> None:
        self._token = access_token

    async def count_by_year(
        self, query: str, start_year: int, end_year: int
    ) -> list[dict[str, int]]:
        """Publikationen pro Jahr zaehlen (parallele Header-Only-Abfragen)."""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            tasks = [
                self._count_single_year(client, query, year)
                for year in range(start_year, end_year + 1)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        yearly: list[dict[str, int]] = []
        for result in results:
            if isinstance(result, dict):
                yearly.append(result)
            elif isinstance(result, Exception):
                logger.warning("OpenAIRE year query failed: %s", result)

        yearly.sort(key=lambda x: x["year"])
        return yearly

    async def _count_single_year(
        self, client: httpx.AsyncClient, query: str, year: int
    ) -> dict[str, int]:
        """Publikationen fuer ein einzelnes Jahr zaehlen."""
        params: dict[str, str | int] = {
            "keywords": query,
            "fromDateAccepted": f"{year}-01-01",
            "toDateAccepted": f"{year}-12-31",
            "format": "json",
            "size": 1,
        }
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        resp = await client.get(self.BASE_URL, params=params, headers=headers)
        resp.raise_for_status()

        data: dict[str, Any] = resp.json()
        total_str = data["response"]["header"]["total"]["$"]
        return {"year": year, "count": int(total_str)}
