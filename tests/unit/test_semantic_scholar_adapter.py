"""Unit-Tests fuer den Semantic Scholar Adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ti_radar.infrastructure.adapters.semantic_scholar_adapter import (
    SemanticScholarAdapter,
)


def _mock_client_with_get(mock_get_fn):
    """Helper: patch httpx.AsyncClient as async context manager with custom get."""
    mock_client = AsyncMock()
    mock_client.get = mock_get_fn

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_client_cls


class TestSemanticScholarAdapter:
    """Tests fuer Semantic Scholar API Adapter."""

    def test_base_url(self):
        adapter = SemanticScholarAdapter()
        assert "semanticscholar.org" in adapter.BASE_URL

    def test_default_timeout(self):
        adapter = SemanticScholarAdapter()
        assert adapter.TIMEOUT == 10.0

    async def test_search_papers_parses_response(self):
        adapter = SemanticScholarAdapter()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "total": 1,
            "data": [{
                "paperId": "abc",
                "title": "Quantum Computing",
                "year": 2022,
                "citationCount": 10,
                "influentialCitationCount": 2,
                "venue": "Nature",
                "authors": [{"name": "A. Author"}],
                "fieldsOfStudy": ["Computer Science"],
                "publicationTypes": ["JournalArticle"],
                "referenceCount": 5,
            }],
        }
        mock_response.raise_for_status = MagicMock()

        mock_get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", _mock_client_with_get(mock_get)):
            result = await adapter.search_papers("quantum computing", 2020, 2023, limit=10)

        assert len(result) == 1
        assert result[0]["title"] == "Quantum Computing"
        assert result[0]["citationCount"] == 10

    async def test_search_papers_empty_on_error(self):
        adapter = SemanticScholarAdapter()

        async def mock_get(*args, **kwargs):
            raise httpx.HTTPError("timeout")

        with patch("httpx.AsyncClient", _mock_client_with_get(mock_get)):
            result = await adapter.search_papers("quantum", 2020, 2023)
        assert result == []

    async def test_search_papers_pagination(self):
        """Adapter paginates when total > page size."""
        adapter = SemanticScholarAdapter()

        def make_page_data(start, end, total):
            return {
                "total": total,
                "data": [{"paperId": f"p{i}", "title": f"Paper {i}", "year": 2022,
                           "citationCount": i, "influentialCitationCount": 0,
                           "venue": "", "authors": [], "fieldsOfStudy": [],
                           "publicationTypes": [], "referenceCount": 0}
                          for i in range(start, end)],
            }

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if call_count == 1:
                resp.json.return_value = make_page_data(0, 100, 150)
            else:
                resp.json.return_value = make_page_data(100, 150, 150)
            return resp

        with patch("httpx.AsyncClient", _mock_client_with_get(mock_get)):
            result = await adapter.search_papers("quantum", 2020, 2023, limit=200)

        assert len(result) == 150
        assert call_count == 2

    async def test_search_papers_respects_limit(self):
        """Don't return more than requested limit."""
        adapter = SemanticScholarAdapter()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "total": 500,
            "data": [{"paperId": f"p{i}", "title": f"Paper {i}", "year": 2022,
                       "citationCount": i, "influentialCitationCount": 0,
                       "venue": "", "authors": [], "fieldsOfStudy": [],
                       "publicationTypes": [], "referenceCount": 0}
                      for i in range(100)],
        }
        mock_response.raise_for_status = MagicMock()

        mock_get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", _mock_client_with_get(mock_get)):
            result = await adapter.search_papers("quantum", 2020, 2023, limit=50)
        assert len(result) <= 50

    async def test_search_papers_empty_data(self):
        """API returns empty data array."""
        adapter = SemanticScholarAdapter()

        mock_response = MagicMock()
        mock_response.json.return_value = {"total": 0, "data": []}
        mock_response.raise_for_status = MagicMock()

        mock_get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", _mock_client_with_get(mock_get)):
            result = await adapter.search_papers("nonexistent", 2020, 2023)
        assert result == []
