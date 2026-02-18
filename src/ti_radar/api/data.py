"""GET-Endpoints fuer Health, Metadata, Suggestions und Cache."""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from ti_radar.config import Settings
from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository

router = APIRouter(tags=["Data"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Service Health Check mit Datenbank-Status."""
    settings = Settings()

    patents_db = Path(settings.patents_db_path)
    cordis_db = Path(settings.cordis_db_path)

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_sources": {
            "patents_db": {
                "available": patents_db.exists(),
                "path": settings.patents_db_path,
                "size_mb": round(patents_db.stat().st_size / 1_048_576, 1)
                if patents_db.exists()
                else 0,
            },
            "cordis_db": {
                "available": cordis_db.exists(),
                "path": settings.cordis_db_path,
                "size_mb": round(cordis_db.stat().st_size / 1_048_576, 1)
                if cordis_db.exists()
                else 0,
            },
            "epo_api": "configured" if settings.epo_ops_consumer_key else "not_configured",
            "cordis_api": "configured" if settings.cordis_api_key else "not_configured",
            "openaire_api": "configured"
            if settings.openaire_access_token
            else "public_access",
            "semantic_scholar_api": "configured"
            if settings.semantic_scholar_api_key
            else "public_access",
            "gleif_api": "public_access",
        },
    }


@router.get("/api/v1/data/metadata")
async def data_metadata() -> dict[str, Any]:
    """Metadaten ueber verfuegbare Datenquellen."""
    settings = Settings()
    return {
        "patents_db_available": settings.patents_db_available,
        "cordis_db_available": settings.cordis_db_available,
        "epo_api_configured": bool(settings.epo_ops_consumer_key),
        "cordis_api_configured": bool(settings.cordis_api_key),
        "openaire_configured": bool(settings.openaire_access_token),
        "semantic_scholar_configured": bool(settings.semantic_scholar_api_key),
        "gleif_available": True,
    }


# Patent/CORDIS-Titel enthalten viele generische Woerter die keine
# Technologiebegriffe sind — diese filtern wir aus den Ngrams.
_STOPWORDS = frozenset({
    # Englisch
    "a", "an", "the", "of", "for", "and", "or", "in", "on", "to", "with",
    "by", "from", "at", "its", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "not", "no", "nor",
    "but", "if", "than", "that", "this", "these", "those", "such", "as",
    "based", "method", "methods", "using", "use", "used", "system", "systems",
    "device", "devices", "apparatus", "process", "processes", "comprising",
    "related", "new", "novel", "improved", "thereof", "therein", "wherein",
    "means", "including", "particularly", "especially", "via",
    # Deutsch
    "und", "fuer", "der", "die", "das", "ein", "eine", "von", "mit",
    "zur", "zum", "auf", "aus", "bei", "nach", "ueber",
    # Franzoesisch
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en",
    "au", "aux", "pour", "par", "sur", "dans", "avec",
    # Spanisch
    "el", "lo", "los", "las", "del", "al", "su", "sus",
    "con", "por", "para", "se", "que", "es",
    # Italienisch
    "il", "di", "da", "nel", "nei", "per", "che",
    # Einzelbuchstaben (keine Technologiebegriffe)
    "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
})

# Kuratierte Liste beliebter Technologiebegriffe fuer leeres Suchfeld.
# Alphabetisch sortiert, aus den haeufigsten Patentklassen und EU-Projekten.
_DEFAULT_SUGGESTIONS = [
    "Artificial Intelligence",
    "Autonomous Vehicles",
    "Battery Technology",
    "Blockchain",
    "Carbon Capture",
    "CRISPR",
    "Cybersecurity",
    "Electric Vehicles",
    "Fuel Cells",
    "Gene Therapy",
    "Graphene",
    "Hydrogen Energy",
    "Internet of Things",
    "Laser Technology",
    "Machine Learning",
    "Nanotechnology",
    "Perovskite Solar",
    "Photovoltaic",
    "Quantum Computing",
    "Robotics",
    "Semiconductor",
    "Solid-State Batteries",
    "Superconductor",
    "Wind Energy",
]


def _extract_terms(
    titles: list[str], prefix: str, ngram_sizes: tuple[int, ...] = (2, 3)
) -> list[str]:
    """Haeufigste Ngrams aus Titeln extrahieren, die den Suchbegriff enthalten.

    Behaelt die Original-Gross-/Kleinschreibung bei (haeufigste Variante gewinnt).
    Filtert Stopword-lastige Ngrams und dedupliziert aehnliche Begriffe.
    """
    prefix_lower = prefix.lower()
    word_pattern = re.compile(r"[a-zA-Z0-9äöüÄÖÜß-]+")

    # Zaehle normalisierte Form -> {original_form: count}
    # Gruppiert verschiedene Schreibweisen desselben Begriffs
    norm_to_forms: dict[str, Counter[str]] = {}

    for title in titles:
        words = word_pattern.findall(title)
        for n in ngram_sizes:
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i : i + n])
                ngram_lower = ngram.lower()
                if prefix_lower in ngram_lower:
                    # Stopword-Check: Echte Technologiebegriffe beginnen/enden
                    # nicht mit Stopwords ("a quantum", "using laser" etc.)
                    ngram_words = ngram_lower.split()
                    if ngram_words[0] in _STOPWORDS or ngram_words[-1] in _STOPWORDS:
                        continue
                    norm_key = ngram_lower
                    if norm_key not in norm_to_forms:
                        norm_to_forms[norm_key] = Counter()
                    norm_to_forms[norm_key][ngram] += 1

    # Pro normalisiertem Begriff: Gesamtcount + smart Title Case
    scored: list[tuple[str, int]] = []
    for _norm, forms in norm_to_forms.items():
        total = sum(forms.values())
        best_form = forms.most_common(1)[0][0]
        scored.append((_normalize_case(best_form), total))

    # Sortiere nach Haeufigkeit (absteigend)
    scored.sort(key=lambda x: x[1], reverse=True)
    return [term for term, _ in scored[:30]]


def _normalize_case(term: str) -> str:
    """Intelligente Gross-/Kleinschreibung fuer Technologiebegriffe.

    - ALL CAPS oder all lowercase -> Title Case
    - Kurze Woerter (<=4 Zeichen) die ALL CAPS sind bleiben gross (Akronyme: LED, AI, CPC)
    - Bereits gemischte Schreibweise (Quantum Computing) bleibt erhalten
    """
    # Bereits sinnvoll gemischt (nicht alles gross/klein) -> beibehalten
    if not term.isupper() and not term.islower():
        return term

    # ALL CAPS oder all lowercase -> smart Title Case
    words = term.split()
    result: list[str] = []
    for word in words:
        if word.isupper() and len(word) <= 4 and not word.isdigit() and word.lower() not in _STOPWORDS:
            # Wahrscheinlich Akronym (LED, AI, CPC, IoT) -> gross lassen
            result.append(word)
        else:
            result.append(word.capitalize())
    return " ".join(result)


@router.get("/api/v1/suggestions")
async def suggest_technologies(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
) -> list[str]:
    """Technologie-Vorschlaege via FTS5-Prefix-Suche.

    Bei leerem q werden kuratierte Default-Vorschlaege zurueckgegeben.
    """
    # Leeres Suchfeld: kuratierte alphabetische Liste
    if not q or len(q.strip()) < 2:
        return _DEFAULT_SUGGESTIONS[:limit]

    q = q.strip()
    settings = Settings()
    all_titles: list[str] = []

    if settings.patents_db_available:
        try:
            repo = PatentRepository(settings.patents_db_path)
            all_titles.extend(await repo.suggest_titles(q, limit=500))
        except Exception as exc:
            logger.warning("Patent suggestions failed: %s", exc)

    if settings.cordis_db_available:
        try:
            repo_c = CordisRepository(settings.cordis_db_path)
            all_titles.extend(await repo_c.suggest_titles(q, limit=200))
        except Exception as exc:
            logger.warning("CORDIS suggestions failed: %s", exc)

    if not all_titles:
        return []

    terms = _extract_terms(all_titles, q)
    return terms[:limit]
