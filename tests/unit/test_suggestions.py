"""Tests fuer die Autocomplete-Logik (_extract_terms, _DEFAULT_SUGGESTIONS)."""

from __future__ import annotations

import pytest

from ti_radar.api.data import _DEFAULT_SUGGESTIONS, _STOPWORDS, _extract_terms


class TestExtractTermsCase:
    """Gross-/Kleinschreibung wird beibehalten."""

    def test_preserves_original_case(self) -> None:
        titles = [
            "Quantum Computing in Europe",
            "Quantum Computing Applications",
            "quantum computing methods",
        ]
        result = _extract_terms(titles, "quantum")
        assert any("Quantum Computing" == t for t in result), f"Expected 'Quantum Computing' in {result}"

    def test_most_common_form_wins(self) -> None:
        titles = [
            "QUANTUM COMPUTING patent",
            "Quantum Computing research",
            "Quantum Computing applications",
            "Quantum Computing devices",
        ]
        result = _extract_terms(titles, "quantum")
        # "Quantum Computing" (3x) sollte ueber "QUANTUM COMPUTING" (1x) gewinnen
        assert result[0] == "Quantum Computing"

    def test_case_insensitive_prefix_match(self) -> None:
        titles = ["Solar Cell Technology", "solar cell research"]
        result = _extract_terms(titles, "SOLAR")
        assert len(result) > 0, "Prefix-Match sollte case-insensitive sein"


class TestExtractTermsStopwords:
    """Stopword-Filter entfernt generische Ngrams."""

    def test_pure_stopword_ngrams_removed(self) -> None:
        titles = ["method for the use of quantum dots"]
        result = _extract_terms(titles, "for")
        # "for the" und "method for" bestehen nur aus Stopwords -> gefiltert
        assert "for the" not in [t.lower() for t in result]
        assert "method for" not in [t.lower() for t in result]

    def test_mixed_ngrams_kept(self) -> None:
        titles = ["method for quantum computing"] * 5
        result = _extract_terms(titles, "quantum")
        lower_results = [t.lower() for t in result]
        assert "quantum computing" in lower_results

    def test_stopwords_list_not_empty(self) -> None:
        assert len(_STOPWORDS) > 20


class TestExtractTermsDedup:
    """Deduplizierung aehnlicher Begriffe."""

    def test_deduplicates_case_variants(self) -> None:
        titles = [
            "Quantum Computing",
            "QUANTUM COMPUTING",
            "quantum computing",
        ]
        result = _extract_terms(titles, "quantum")
        lower_results = [t.lower() for t in result]
        assert lower_results.count("quantum computing") == 1

    def test_sorted_by_frequency(self) -> None:
        titles = (
            ["Solar Cell Technology"] * 10
            + ["Quantum Computing Research"] * 3
        )
        result = _extract_terms(titles, "")
        # Solar Cell sollte vor Quantum Computing stehen (10 > 3)
        solar_idx = next(i for i, t in enumerate(result) if "solar" in t.lower())
        quantum_idx = next(i for i, t in enumerate(result) if "quantum" in t.lower())
        assert solar_idx < quantum_idx


class TestExtractTermsEdgeCases:
    """Randfaelle."""

    def test_empty_titles(self) -> None:
        assert _extract_terms([], "quantum") == []

    def test_no_matches(self) -> None:
        titles = ["Solar Cell Technology"]
        assert _extract_terms(titles, "quantum") == []

    def test_max_30_results(self) -> None:
        # Viele verschiedene Titel erzeugen
        titles = [f"technology variant {i} quantum" for i in range(100)]
        result = _extract_terms(titles, "quantum")
        assert len(result) <= 30


class TestDefaultSuggestions:
    """Kuratierte Default-Vorschlaege."""

    def test_alphabetically_sorted(self) -> None:
        assert _DEFAULT_SUGGESTIONS == sorted(_DEFAULT_SUGGESTIONS, key=str.casefold)

    def test_not_empty(self) -> None:
        assert len(_DEFAULT_SUGGESTIONS) >= 10

    def test_proper_case(self) -> None:
        for s in _DEFAULT_SUGGESTIONS:
            # Jeder Begriff sollte mindestens einen Grossbuchstaben haben
            assert s != s.lower(), f"'{s}' sollte Grossbuchstaben enthalten"
