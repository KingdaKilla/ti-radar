"""
API-Konnektivitaetstest fuer den Technology Radar.

Testet alle externen APIs (OpenAIRE, Semantic Scholar, GLEIF, CORDIS DET).
Liest API Keys aus .env via Pydantic Settings.

Ausfuehrung: python scripts/test_api_keys.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Sicherstellen dass src/ im Python-Path liegt
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx  # noqa: E402
from ti_radar.config import Settings  # noqa: E402


def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def _result(ok: bool, msg: str) -> None:
    status = "\033[92m[OK]\033[0m" if ok else "\033[91m[FAIL]\033[0m"
    print(f"  {status} {msg}")


async def test_openaire(settings: Settings) -> bool:
    """OpenAIRE Search API (verwendet von UC1)."""
    _section("OpenAIRE Search API")

    if settings.openaire_access_token:
        print(f"  Token: {settings.openaire_access_token[:20]}... (konfiguriert)")
    else:
        print("  Token: nicht konfiguriert (Public Access)")

    headers: dict[str, str] = {}
    if settings.openaire_access_token:
        headers["Authorization"] = f"Bearer {settings.openaire_access_token}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            t0 = time.monotonic()
            resp = await client.get(
                "https://api.openaire.eu/search/publications",
                params={"keywords": "quantum computing", "format": "json", "size": 1},
                headers=headers,
            )
            ms = int((time.monotonic() - t0) * 1000)
            print(f"  Status: {resp.status_code} ({ms}ms)")

            if resp.status_code == 200:
                data = resp.json()
                total = data["response"]["header"]["total"]["$"]
                _result(True, f"OpenAIRE erreichbar, {total} Treffer fuer 'quantum computing'")
                return True
            else:
                _result(False, f"HTTP {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        _result(False, f"Fehler: {e}")
        return False


async def test_semantic_scholar(settings: Settings) -> bool:
    """Semantic Scholar Academic Graph API (verwendet von UC7)."""
    _section("Semantic Scholar API")

    if settings.semantic_scholar_api_key:
        print(f"  API Key: {settings.semantic_scholar_api_key[:8]}... (konfiguriert)")
    else:
        print("  API Key: nicht konfiguriert (Public Access)")

    headers: dict[str, str] = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            t0 = time.monotonic()
            resp = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": "quantum computing", "limit": 1, "fields": "title,year"},
                headers=headers,
            )
            ms = int((time.monotonic() - t0) * 1000)
            print(f"  Status: {resp.status_code} ({ms}ms)")

            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total", 0)
                _result(True, f"Semantic Scholar erreichbar, {total} Treffer")
                return True
            elif resp.status_code == 429:
                _result(False, "Rate Limit erreicht (429) — API Key empfohlen")
                return False
            else:
                _result(False, f"HTTP {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        _result(False, f"Fehler: {e}")
        return False


async def test_gleif() -> bool:
    """GLEIF LEI API (verwendet von UC3, kein Key noetig)."""
    _section("GLEIF LEI API")
    print("  Auth: oeffentlich (kein Key noetig)")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            t0 = time.monotonic()
            resp = await client.get(
                "https://api.gleif.org/api/v1/lei-records",
                params={"filter[entity.legalName]": "SIEMENS"},
            )
            ms = int((time.monotonic() - t0) * 1000)
            print(f"  Status: {resp.status_code} ({ms}ms)")

            if resp.status_code == 200:
                data = resp.json()
                count = len(data.get("data", []))
                _result(True, f"GLEIF erreichbar, {count} Treffer fuer 'SIEMENS'")
                return True
            else:
                _result(False, f"HTTP {resp.status_code}")
                return False
    except Exception as e:
        _result(False, f"Fehler: {e}")
        return False


async def test_cordis_api(settings: Settings) -> bool:
    """CORDIS Data Extraction Tool API (optional, Key erhoeht Rate Limits)."""
    _section("CORDIS DET API")

    if not settings.cordis_api_key:
        print("  API Key: nicht konfiguriert")
        _result(False, "CORDIS_API_KEY nicht gesetzt — uebersprungen")
        return False

    print(f"  API Key: {settings.cordis_api_key[:8]}... (konfiguriert)")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            t0 = time.monotonic()
            resp = await client.get(
                "https://cordis.europa.eu/api/dataextractions/getExtraction",
                params={
                    "query": "contenttype='project' AND 'quantum'",
                    "outputFormat": "json",
                    "key": settings.cordis_api_key,
                },
            )
            ms = int((time.monotonic() - t0) * 1000)
            print(f"  Status: {resp.status_code} ({ms}ms)")

            if resp.status_code == 200:
                _result(True, "CORDIS DET API Key gueltig")
                return True
            elif resp.status_code == 401:
                _result(False, "API Key ungueltig (401)")
                return False
            else:
                _result(False, f"HTTP {resp.status_code}")
                return False
    except Exception as e:
        _result(False, f"Fehler: {e}")
        return False


async def main() -> bool:
    """Alle APIs testen und Zusammenfassung ausgeben."""
    print(f"\n{'='*60}")
    print("  Technology Radar — API-Konnektivitaetstest")
    print(f"  Zeitpunkt: {datetime.now().isoformat()}")
    print(f"{'='*60}")

    settings = Settings()
    results: dict[str, bool] = {}

    results["OpenAIRE"] = await test_openaire(settings)
    results["Semantic Scholar"] = await test_semantic_scholar(settings)
    results["GLEIF"] = await test_gleif()
    results["CORDIS DET"] = await test_cordis_api(settings)

    _section("Zusammenfassung")
    for api, ok in results.items():
        status = "\033[92mOK\033[0m" if ok else "\033[91mFEHLGESCHLAGEN\033[0m"
        print(f"  {api}: {status}")

    all_ok = all(results.values())
    print(
        f"\n  Ergebnis: {'Alle Tests bestanden' if all_ok else 'Einige Tests fehlgeschlagen'}"
    )
    return all_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
