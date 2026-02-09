"""Tests fuer OpenAIRE Search API Adapter."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ti_radar.infrastructure.adapters.openaire_adapter import OpenAIREAdapter


def _make_response(total: int) -> dict[str, Any]:
    """OpenAIRE JSON-Antwort simulieren."""
    return {
        "response": {
            "header": {
                "total": {"$": str(total)},
            },
            "results": {},
        },
    }


class TestCountByYear:
    """Tests fuer count_by_year Methode."""

    @pytest.mark.asyncio
    async def test_single_year(self) -> None:
        adapter = OpenAIREAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = _make_response(42)
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.count_by_year("quantum", 2023, 2023)

        assert len(result) == 1
        assert result[0] == {"year": 2023, "count": 42}

    @pytest.mark.asyncio
    async def test_multiple_years_sorted(self) -> None:
        adapter = OpenAIREAdapter()

        call_count = 0

        async def mock_get(
            url: str, params: dict[str, Any], headers: dict[str, str]
        ) -> MagicMock:
            nonlocal call_count
            call_count += 1
            year = int(str(params["fromDateAccepted"])[:4])
            resp = MagicMock()
            resp.json.return_value = _make_response(year * 10)
            resp.raise_for_status = MagicMock()
            return resp

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.count_by_year("ai", 2020, 2022)

        assert len(result) == 3
        assert result[0]["year"] == 2020
        assert result[1]["year"] == 2021
        assert result[2]["year"] == 2022
        assert result[0]["count"] == 20200
        assert result[2]["count"] == 20220

    @pytest.mark.asyncio
    async def test_error_year_skipped(self) -> None:
        adapter = OpenAIREAdapter()

        async def mock_get(
            url: str, params: dict[str, Any], headers: dict[str, str]
        ) -> MagicMock:
            year = int(str(params["fromDateAccepted"])[:4])
            if year == 2021:
                raise httpx.HTTPStatusError(
                    "Server Error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            resp = MagicMock()
            resp.json.return_value = _make_response(100)
            resp.raise_for_status = MagicMock()
            return resp

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.count_by_year("test", 2020, 2022)

        assert len(result) == 2
        years = [r["year"] for r in result]
        assert 2021 not in years

    @pytest.mark.asyncio
    async def test_empty_range(self) -> None:
        adapter = OpenAIREAdapter()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.count_by_year("test", 2023, 2022)

        assert len(result) == 0


class TestAuthHeader:
    """Tests fuer Authorization-Header."""

    @pytest.mark.asyncio
    async def test_no_token_no_header(self) -> None:
        adapter = OpenAIREAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = _make_response(10)
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await adapter.count_by_year("test", 2023, 2023)

            call_args = mock_client.get.call_args
            headers = call_args.kwargs.get("headers", {})
            assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_token_sends_bearer(self) -> None:
        adapter = OpenAIREAdapter(access_token="my-secret-token")
        mock_response = MagicMock()
        mock_response.json.return_value = _make_response(10)
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await adapter.count_by_year("test", 2023, 2023)

            call_args = mock_client.get.call_args
            headers = call_args.kwargs.get("headers", {})
            assert headers["Authorization"] == "Bearer my-secret-token"


class TestRequestParams:
    """Tests fuer korrekte API-Parameter."""

    @pytest.mark.asyncio
    async def test_correct_params(self) -> None:
        adapter = OpenAIREAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = _make_response(5)
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await adapter.count_by_year("quantum computing", 2023, 2023)

            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert params["keywords"] == "quantum computing"
            assert params["fromDateAccepted"] == "2023-01-01"
            assert params["toDateAccepted"] == "2023-12-31"
            assert params["format"] == "json"
            assert params["size"] == 1


class TestResponseParsing:
    """Tests fuer JSON-Response-Parsing."""

    @pytest.mark.asyncio
    async def test_total_as_string(self) -> None:
        """Total wird als String geliefert und zu int konvertiert."""
        adapter = OpenAIREAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "header": {"total": {"$": "12345"}},
                "results": {},
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.count_by_year("test", 2023, 2023)

        assert result[0]["count"] == 12345

    @pytest.mark.asyncio
    async def test_zero_results(self) -> None:
        adapter = OpenAIREAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = _make_response(0)
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.count_by_year("nonexistent", 2023, 2023)

        assert result[0]["count"] == 0
