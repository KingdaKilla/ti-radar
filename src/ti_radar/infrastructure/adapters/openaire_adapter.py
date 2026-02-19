"""OpenAIRE Search API Adapter fuer Publikationsdaten."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Modul-Level-Cache: vermeidet Token-Refresh bei jedem parallelen Year-Request
_cached_token: str = ""
_cached_token_exp: float = 0.0

_REFRESH_URL = (
    "https://services.openaire.eu/uoa-user-management"
    "/api/users/getAccessToken"
)
_TOKEN_MARGIN_S = 60  # Refresh 60s vor Ablauf


def _token_expiry(token: str) -> float:
    """JWT-Ablaufzeitpunkt (Unix-Timestamp) extrahieren. 0.0 bei Fehler."""
    if not token or "." not in token:
        return 0.0
    try:
        parts = token.split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return float(payload.get("exp", 0))
    except Exception:
        return 0.0


class OpenAIREAdapter:
    """Async-Adapter fuer die OpenAIRE Search API (Publikationen)."""

    BASE_URL = "https://api.openaire.eu/search/publications"
    TIMEOUT = 10.0

    def __init__(
        self, access_token: str = "", refresh_token: str = "",
    ) -> None:
        self._token = access_token
        self._refresh_token = refresh_token

    async def _ensure_valid_token(self) -> None:
        """Access-Token pruefen und bei Bedarf per Refresh-Token erneuern."""
        global _cached_token, _cached_token_exp  # noqa: PLW0603

        # Kein Token und kein Refresh-Token → oeffentlicher Zugang
        if not self._token and not self._refresh_token:
            return

        now = time.time()

        # 1. Gecachtes Token aus vorherigem Refresh noch gueltig?
        if (
            self._refresh_token
            and _cached_token
            and _cached_token_exp - now > _TOKEN_MARGIN_S
        ):
            self._token = _cached_token
            return

        # 2. Aktuelles Token noch gueltig?
        current_exp = _token_expiry(self._token)
        if current_exp - now > _TOKEN_MARGIN_S:
            return

        # 3. Refresh-Token vorhanden? → neues Access-Token holen
        if self._refresh_token:
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    resp = await client.get(
                        _REFRESH_URL,
                        params={"refreshToken": self._refresh_token},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                new_token = data.get("access_token", "")
                if new_token:
                    self._token = new_token
                    _cached_token = new_token
                    _cached_token_exp = _token_expiry(new_token)
                    logger.info(
                        "OpenAIRE Token auto-refreshed (gueltig %.0f min)",
                        (_cached_token_exp - time.time()) / 60,
                    )
                    return
            except Exception as exc:
                logger.warning("OpenAIRE Token-Refresh fehlgeschlagen: %s", exc)

        # 4. Fallback: altes Token verwenden (ggf. niedrigere Rate-Limits)

    async def count_by_year(
        self, query: str, start_year: int, end_year: int
    ) -> list[dict[str, int]]:
        """Publikationen pro Jahr zaehlen (parallele Header-Only-Abfragen)."""
        await self._ensure_valid_token()

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

        t0 = time.monotonic()
        resp = await client.get(self.BASE_URL, params=params, headers=headers)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "OpenAIRE year=%d -> %d (%dms)", year, resp.status_code, elapsed_ms,
        )
        resp.raise_for_status()

        data: dict[str, Any] = resp.json()
        total_str = data["response"]["header"]["total"]["$"]
        return {"year": year, "count": int(total_str)}
