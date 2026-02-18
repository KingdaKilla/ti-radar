"""Semantic Scholar Academic Graph API Adapter."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_FIELDS = (
    "title,year,citationCount,venue,authors,fieldsOfStudy,"
    "publicationTypes,influentialCitationCount,referenceCount"
)


class SemanticScholarAdapter:
    """Async-Adapter fuer die Semantic Scholar Academic Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    TIMEOUT = 10.0
    PAGE_SIZE = 100

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    async def search_papers(
        self, query: str, year_start: int, year_end: int, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Paginated paper search with year filtering.

        Returns up to `limit` papers. Graceful degradation on error.
        """
        all_papers: list[dict[str, Any]] = []
        offset = 0

        headers: dict[str, str] = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                while len(all_papers) < limit:
                    page_limit = min(self.PAGE_SIZE, limit - len(all_papers))
                    params: dict[str, str | int] = {
                        "query": query,
                        "year": f"{year_start}-{year_end}",
                        "fields": _FIELDS,
                        "offset": offset,
                        "limit": page_limit,
                    }

                    t0 = time.monotonic()
                    resp = await client.get(
                        self.BASE_URL, params=params, headers=headers
                    )
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    logger.info(
                        "Semantic Scholar offset=%d -> %d (%dms)",
                        offset, resp.status_code, elapsed_ms,
                    )
                    resp.raise_for_status()
                    data: dict[str, Any] = resp.json()

                    papers = data.get("data", [])
                    if not papers:
                        break

                    all_papers.extend(papers)
                    total = data.get("total", 0)

                    offset += len(papers)
                    if offset >= total:
                        break

                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.warning("Semantic Scholar search failed: %s", e)

        return all_papers[:limit]
