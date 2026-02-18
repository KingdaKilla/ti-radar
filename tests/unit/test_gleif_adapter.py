"""Unit-Tests fuer den GLEIF Adapter mit Cache."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ti_radar.infrastructure.adapters.gleif_adapter import GleifAdapter

_DUMMY_REQUEST = httpx.Request("GET", "https://api.gleif.org/api/v1/lei-records")


def _gleif_response(data: dict[str, Any], status: int = 200) -> httpx.Response:
    """Create httpx.Response with request instance (needed for raise_for_status)."""
    return httpx.Response(status, json=data, request=_DUMMY_REQUEST)


@pytest.fixture()
def cache_db(tmp_path: Path) -> str:
    """Temp SQLite DB for GLEIF cache."""
    return str(tmp_path / "gleif_cache.db")


class TestGleifAdapter:
    """Tests fuer GLEIF API Adapter."""

    def test_base_url(self):
        adapter = GleifAdapter(cache_db_path=":memory:")
        assert "gleif.org" in adapter.BASE_URL

    async def test_resolve_entity_returns_match(self, cache_db: str):
        adapter = GleifAdapter(cache_db_path=cache_db)
        mock_response = _gleif_response({
            "data": [{
                "attributes": {
                    "lei": "529900HNOAA1KXQJUQ27",
                    "entity": {
                        "legalName": {"name": "SIEMENS AKTIENGESELLSCHAFT"},
                        "jurisdiction": "DE",
                        "legalAddress": {
                            "city": "MUNICH",
                            "country": "DE",
                            "region": "DE-BY",
                        },
                    },
                },
            }],
        })
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await adapter.resolve_entity("SIEMENS AG")
        assert result is not None
        assert result["legal_name"] == "SIEMENS AKTIENGESELLSCHAFT"
        assert result["country"] == "DE"
        assert result["city"] == "MUNICH"

    async def test_resolve_entity_none_on_no_match(self, cache_db: str):
        adapter = GleifAdapter(cache_db_path=cache_db)
        mock_response = _gleif_response({"data": []})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await adapter.resolve_entity("NONEXISTENT CORP XYZ")
        assert result is None

    async def test_resolve_entity_none_on_error(self, cache_db: str):
        adapter = GleifAdapter(cache_db_path=cache_db)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.HTTPError("timeout")):
            result = await adapter.resolve_entity("SIEMENS AG")
        assert result is None

    async def test_cache_hit(self, cache_db: str):
        """Second resolve uses cache, no API call."""
        adapter = GleifAdapter(cache_db_path=cache_db)
        mock_response = _gleif_response({
            "data": [{
                "attributes": {
                    "lei": "529900HNOAA1KXQJUQ27",
                    "entity": {
                        "legalName": {"name": "SIEMENS AG"},
                        "jurisdiction": "DE",
                        "legalAddress": {"city": "MUNICH", "country": "DE", "region": ""},
                    },
                },
            }],
        })
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response) as mock_get:
            r1 = await adapter.resolve_entity("SIEMENS AG")
            r2 = await adapter.resolve_entity("SIEMENS AG")
        assert mock_get.call_count == 1
        assert r1 is not None
        assert r2 is not None
        assert r1["legal_name"] == r2["legal_name"]

    async def test_resolve_batch(self, cache_db: str):
        adapter = GleifAdapter(cache_db_path=cache_db)
        mock_response = _gleif_response({"data": []})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await adapter.resolve_batch(["A", "B", "C"])
        assert isinstance(result, dict)
        assert len(result) == 3

    async def test_cache_negative_result(self, cache_db: str):
        """Negative results (no match) are cached too."""
        adapter = GleifAdapter(cache_db_path=cache_db)
        mock_response = _gleif_response({"data": []})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response) as mock_get:
            await adapter.resolve_entity("UNKNOWN XYZ")
            await adapter.resolve_entity("UNKNOWN XYZ")
        assert mock_get.call_count == 1
