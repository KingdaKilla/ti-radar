"""Tests fuer deterministische jahresstratifizierte Stichprobenziehung.

Testet die Kernfunktionen aus ti_radar.domain.sampling:
- stratified_sample (Hauptfunktion)
- _group_by_year, _allocate_proportional, _systematic_select (Hilfsfunktionen)
- estimate_jaccard_confidence (Stichprobenfehler)
"""

from __future__ import annotations

import math
import time
from collections import Counter

import pytest

from ti_radar.domain.sampling import (
    CENSUS_THRESHOLD,
    DEFAULT_SAMPLE_SIZE,
    JaccardConfidence,
    SamplingResult,
    StratumInfo,
    _allocate_proportional,
    _group_by_year,
    _systematic_select,
    estimate_jaccard_confidence,
    stratified_sample,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_patents(year_counts: dict[int, int]) -> list[tuple[set[str], int]]:
    """Testdaten erzeugen: n Patente pro Jahr mit synthetischen CPC-Codes."""
    data: list[tuple[set[str], int]] = []
    for year, count in sorted(year_counts.items()):
        for i in range(count):
            # Jedes Patent erhaelt 2-3 CPC-Codes
            codes = {f"C{i % 10:02d}", f"D{(i + 1) % 10:02d}"}
            if i % 3 == 0:
                codes.add(f"E{(i + 2) % 10:02d}")
            data.append((codes, year))
    return data


# ---------------------------------------------------------------------------
# Tests: _group_by_year
# ---------------------------------------------------------------------------


class TestGroupByYear:
    """Tests fuer die Gruppierung nach Publikationsjahr."""

    def test_basic_grouping(self) -> None:
        data = [
            ({"A", "B"}, 2020),
            ({"C", "D"}, 2021),
            ({"E", "F"}, 2020),
        ]
        groups = _group_by_year(data)
        assert set(groups.keys()) == {2020, 2021}
        assert groups[2020] == [0, 2]
        assert groups[2021] == [1]

    def test_empty_input(self) -> None:
        assert _group_by_year([]) == {}

    def test_single_year(self) -> None:
        data = [({"A", "B"}, 2020)] * 5
        groups = _group_by_year(data)
        assert len(groups) == 1
        assert len(groups[2020]) == 5


# ---------------------------------------------------------------------------
# Tests: _systematic_select
# ---------------------------------------------------------------------------


class TestSystematicSelect:
    """Tests fuer die systematische Auswahl mit Midpoint-Regel."""

    def test_basic(self) -> None:
        indices = list(range(100))
        selected = _systematic_select(indices, 10)
        assert len(selected) == 10
        # Alle Indizes muessen aus der Eingabe stammen
        assert all(idx in indices for idx in selected)

    def test_deterministic(self) -> None:
        indices = list(range(1000))
        a = _systematic_select(indices, 50)
        b = _systematic_select(indices, 50)
        assert a == b

    def test_evenly_spaced(self) -> None:
        """Auswahl soll gleichmaessig verteilt sein."""
        indices = list(range(100))
        selected = _systematic_select(indices, 10)
        gaps = [selected[i + 1] - selected[i] for i in range(len(selected) - 1)]
        # Alle Abstande sollten 9 oder 10 sein (step = 100/10 = 10)
        assert all(9 <= g <= 11 for g in gaps)

    def test_n_equals_total(self) -> None:
        indices = list(range(10))
        selected = _systematic_select(indices, 10)
        assert selected == indices

    def test_n_exceeds_total(self) -> None:
        indices = list(range(5))
        selected = _systematic_select(indices, 20)
        assert selected == indices

    def test_n_zero(self) -> None:
        assert _systematic_select(list(range(10)), 0) == []

    def test_n_one(self) -> None:
        indices = list(range(100))
        selected = _systematic_select(indices, 1)
        assert len(selected) == 1
        # Midpoint: start = (100/1) / 2 = 50
        assert selected[0] == 50

    def test_non_contiguous_indices(self) -> None:
        """Auch bei nicht-zusammenhaengenden Indizes korrekt."""
        indices = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        selected = _systematic_select(indices, 3)
        assert len(selected) == 3
        assert all(idx in indices for idx in selected)


# ---------------------------------------------------------------------------
# Tests: _allocate_proportional
# ---------------------------------------------------------------------------


class TestAllocateProportional:
    """Tests fuer die proportionale Allokation mit Census-Strata."""

    def test_basic_proportional(self) -> None:
        sizes = {2020: 500, 2021: 300, 2022: 200}
        alloc = _allocate_proportional(sizes, target_size=100, census_threshold=5)
        # Proportional: 2020=50, 2021=30, 2022=20
        assert alloc[2020] == 50
        assert alloc[2021] == 30
        assert alloc[2022] == 20
        assert sum(alloc.values()) == 100

    def test_sum_equals_target(self) -> None:
        """Summe der Allokation muss exakt target_size sein."""
        sizes = {2018: 137, 2019: 283, 2020: 419, 2021: 561, 2022: 100}
        alloc = _allocate_proportional(sizes, target_size=1000, census_threshold=5)
        assert sum(alloc.values()) == 1000

    def test_census_stratum(self) -> None:
        """Kleine Schichten werden vollstaendig uebernommen."""
        sizes = {2020: 3, 2021: 500, 2022: 497}
        alloc = _allocate_proportional(sizes, target_size=100, census_threshold=5)
        assert alloc[2020] == 3  # Census: vollstaendig
        assert sum(alloc.values()) == 100

    def test_all_census(self) -> None:
        """Wenn alle Schichten klein sind, werden alle vollstaendig uebernommen."""
        sizes = {2020: 2, 2021: 3, 2022: 4}
        alloc = _allocate_proportional(sizes, target_size=100, census_threshold=5)
        assert alloc[2020] == 2
        assert alloc[2021] == 3
        assert alloc[2022] == 4

    def test_no_over_allocation(self) -> None:
        """Kein Stratum darf mehr als seine Population erhalten."""
        sizes = {2020: 10, 2021: 1000}
        alloc = _allocate_proportional(sizes, target_size=100, census_threshold=0)
        assert alloc[2020] <= 10
        assert alloc[2021] <= 1000

    def test_largest_remainder_correction(self) -> None:
        """Largest-Remainder korrigiert Rundungsfehler."""
        # 3 Schichten mit je 333 Elementen, Target 100
        # Exakt: 33.3 pro Schicht -> floor = 33 -> Summe = 99
        # Largest-Remainder vergibt 1 Extra
        sizes = {2020: 333, 2021: 333, 2022: 334}
        alloc = _allocate_proportional(sizes, target_size=100, census_threshold=0)
        assert sum(alloc.values()) == 100

    def test_single_stratum(self) -> None:
        sizes = {2020: 50000}
        alloc = _allocate_proportional(sizes, target_size=10000, census_threshold=5)
        assert alloc[2020] == 10000


# ---------------------------------------------------------------------------
# Tests: stratified_sample (Hauptfunktion)
# ---------------------------------------------------------------------------


class TestStratifiedSample:
    """Tests fuer die Hauptfunktion stratified_sample."""

    def test_no_sampling_when_small(self) -> None:
        """Keine Stichprobe wenn Population <= target_size."""
        data = _make_patents({2020: 100, 2021: 200})
        result = stratified_sample(data, target_size=10000)
        assert result.was_sampled is False
        assert result.sample_size == 300
        assert result.sampling_fraction == 1.0

    def test_returns_correct_size(self) -> None:
        data = _make_patents({2020: 5000, 2021: 3000, 2022: 2000})
        result = stratified_sample(data, target_size=1000)
        assert result.was_sampled is True
        assert result.sample_size == 1000

    def test_proportionality(self) -> None:
        """Jahresanteile in Stichprobe entsprechen Population."""
        data = _make_patents({2020: 5000, 2021: 3000, 2022: 2000})
        result = stratified_sample(data, target_size=1000)

        # Zaehle Jahre in der Stichprobe
        year_counts = Counter(year for _, year in result.sampled_data)

        # Toleranz: +/- 2% (durch Rundung)
        assert abs(year_counts[2020] / 1000 - 0.50) < 0.02
        assert abs(year_counts[2021] / 1000 - 0.30) < 0.02
        assert abs(year_counts[2022] / 1000 - 0.20) < 0.02

    def test_deterministic(self) -> None:
        """Identischer Input -> identischer Output."""
        data = _make_patents({2020: 5000, 2021: 3000, 2022: 2000})
        result_a = stratified_sample(data, target_size=1000)
        result_b = stratified_sample(data, target_size=1000)

        assert result_a.sampled_data == result_b.sampled_data
        assert result_a.sample_size == result_b.sample_size

    def test_census_strata_preserved(self) -> None:
        """Kleine Jahrgaenge werden vollstaendig uebernommen."""
        data = _make_patents({2018: 3, 2019: 2, 2020: 5000, 2021: 4995})
        result = stratified_sample(data, target_size=1000, census_threshold=5)

        assert result.strata_info[2018].is_census is True
        assert result.strata_info[2018].sample_count == 3
        assert result.strata_info[2019].is_census is True
        assert result.strata_info[2019].sample_count == 2

    def test_empty_input(self) -> None:
        result = stratified_sample([], target_size=1000)
        assert result.sample_size == 0
        assert result.was_sampled is False
        assert result.sampling_fraction == 1.0

    def test_single_patent(self) -> None:
        data = [({" H01L", "G06N"}, 2020)]
        result = stratified_sample(data, target_size=1000)
        assert result.sample_size == 1
        assert result.was_sampled is False

    def test_invalid_target_size(self) -> None:
        with pytest.raises(ValueError, match="target_size muss >= 1"):
            stratified_sample([], target_size=0)

    def test_strata_info_completeness(self) -> None:
        """Alle Jahre muessen in strata_info vorhanden sein."""
        data = _make_patents({2018: 100, 2019: 200, 2020: 300, 2021: 400})
        result = stratified_sample(data, target_size=500)
        assert set(result.strata_info.keys()) == {2018, 2019, 2020, 2021}

    def test_sampling_fraction(self) -> None:
        data = _make_patents({2020: 5000, 2021: 5000})
        result = stratified_sample(data, target_size=2000)
        assert abs(result.sampling_fraction - 0.2) < 0.001

    def test_all_data_has_valid_years(self) -> None:
        """Alle Elemente in der Stichprobe muessen gueltige Jahre haben."""
        data = _make_patents({2015: 500, 2016: 500, 2017: 500, 2018: 500,
                              2019: 500, 2020: 500, 2021: 500, 2022: 500})
        result = stratified_sample(data, target_size=1000)
        for codes, year in result.sampled_data:
            assert 2015 <= year <= 2022
            assert len(codes) >= 2

    def test_large_census_threshold(self) -> None:
        """Mit hohem census_threshold werden mehr Schichten voll uebernommen."""
        data = _make_patents({2020: 50, 2021: 50, 2022: 5000})
        result = stratified_sample(data, target_size=1000, census_threshold=100)
        assert result.strata_info[2020].is_census is True
        assert result.strata_info[2020].sample_count == 50
        assert result.strata_info[2021].is_census is True
        assert result.strata_info[2021].sample_count == 50

    def test_many_small_strata(self) -> None:
        """Viele kleine Jahrgaenge (z.B. Nischen-Technologie).

        Wenn alle Strata Census sind, werden alle Elemente uebernommen,
        auch wenn die Population > target_size ist. was_sampled ist True
        weil die Sampling-Logik durchlaufen wurde, aber die resultierende
        Stichprobe ist groesser als target_size (Census hat Vorrang).
        """
        years = {y: 3 for y in range(2000, 2025)}  # 25 Jahre x 3 = 75
        data = _make_patents(years)
        result = stratified_sample(data, target_size=50, census_threshold=5)
        # Alle Strata sind Census (3 <= 5), daher wird alles uebernommen
        assert result.sample_size == 75
        assert all(info.is_census for info in result.strata_info.values())


# ---------------------------------------------------------------------------
# Tests: Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    """Performance-Tests: Muss unter 50ms bleiben."""

    def test_100k_to_10k_under_50ms(self) -> None:
        """100.000 Patente -> 10.000 Stichprobe in < 50ms."""
        data = _make_patents({
            2015: 5000, 2016: 8000, 2017: 12000, 2018: 15000,
            2019: 18000, 2020: 20000, 2021: 15000, 2022: 7000,
        })
        assert len(data) == 100_000

        start = time.perf_counter()
        result = stratified_sample(data, target_size=10_000)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.sample_size == 10_000
        assert elapsed_ms < 50, f"Dauer: {elapsed_ms:.1f}ms (Limit: 50ms)"

    def test_50k_to_10k(self) -> None:
        """50.000 Patente -> 10.000 Stichprobe."""
        data = _make_patents({
            2018: 10000, 2019: 15000, 2020: 15000, 2021: 10000,
        })
        assert len(data) == 50_000

        start = time.perf_counter()
        result = stratified_sample(data, target_size=10_000)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.sample_size == 10_000
        assert elapsed_ms < 50, f"Dauer: {elapsed_ms:.1f}ms (Limit: 50ms)"


# ---------------------------------------------------------------------------
# Tests: estimate_jaccard_confidence
# ---------------------------------------------------------------------------


class TestJaccardConfidence:
    """Tests fuer die Stichprobenfehler-Schaetzung."""

    def test_perfect_overlap(self) -> None:
        """Jaccard = 1.0 bei perfekter Ueberlappung."""
        result = estimate_jaccard_confidence(
            intersection_count=100,
            union_count=100,
            sample_size=1000,
            population_size=10000,
        )
        assert result.jaccard == 1.0
        assert result.ci_upper == 1.0

    def test_no_overlap(self) -> None:
        """Jaccard = 0.0 bei keiner Ueberlappung."""
        result = estimate_jaccard_confidence(
            intersection_count=0,
            union_count=100,
            sample_size=1000,
            population_size=10000,
        )
        assert result.jaccard == 0.0
        assert result.ci_lower == 0.0

    def test_empty_union(self) -> None:
        result = estimate_jaccard_confidence(0, 0, 1000, 10000)
        assert result.jaccard == 0.0
        assert result.standard_error == 0.0
        assert result.effective_n == 0

    def test_full_population(self) -> None:
        """Bei Vollerhebung ist der Standardfehler 0."""
        result = estimate_jaccard_confidence(
            intersection_count=50,
            union_count=200,
            sample_size=10000,
            population_size=10000,
        )
        assert result.standard_error == 0.0
        assert result.jaccard == 0.25

    def test_confidence_interval_contains_point_estimate(self) -> None:
        result = estimate_jaccard_confidence(
            intersection_count=30,
            union_count=100,
            sample_size=5000,
            population_size=50000,
        )
        assert result.ci_lower <= result.jaccard <= result.ci_upper

    def test_ci_within_0_1(self) -> None:
        """Konfidenzintervall muss in [0, 1] liegen."""
        result = estimate_jaccard_confidence(
            intersection_count=5,
            union_count=10,
            sample_size=100,
            population_size=100000,
        )
        assert 0.0 <= result.ci_lower
        assert result.ci_upper <= 1.0

    def test_larger_sample_smaller_error(self) -> None:
        """Groessere Stichprobe -> kleinerer Standardfehler."""
        small = estimate_jaccard_confidence(30, 100, 500, 50000)
        large = estimate_jaccard_confidence(60, 200, 1000, 50000)
        # Bei doppelter Stichprobe ~sqrt(2) kleinerer SE
        assert large.standard_error < small.standard_error

    def test_fpc_reduces_error(self) -> None:
        """Finite Population Correction reduziert den Fehler."""
        # Gleiche Proportion (0.3), gleiche Stichprobengroesse im Union
        # Aber unterschiedliche Populationsgroesse
        infinite_pop = estimate_jaccard_confidence(30, 100, 100, 1_000_000)
        small_pop = estimate_jaccard_confidence(30, 100, 100, 200)
        # Bei kleiner Population ist FPC staerker -> kleinerer SE
        assert small_pop.standard_error < infinite_pop.standard_error

    def test_moe_is_196_times_se(self) -> None:
        """Margin of Error = 1.96 * SE."""
        result = estimate_jaccard_confidence(30, 100, 1000, 50000)
        if result.standard_error > 0:
            expected_moe = round(1.96 * result.standard_error, 6)
            assert result.margin_of_error_95 == expected_moe


# ---------------------------------------------------------------------------
# Tests: Randfall-Kombination
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Kombinierte Randfaelle."""

    def test_single_year_large_sample(self) -> None:
        """Alle Patente im selben Jahr."""
        data = _make_patents({2020: 50000})
        result = stratified_sample(data, target_size=10000)
        assert result.sample_size == 10000
        years = {year for _, year in result.sampled_data}
        assert years == {2020}

    def test_two_patents_target_one(self) -> None:
        """Zwei Patente in zwei Jahren, target=1.

        Beide Strata haben 1 Element (<= census_threshold=5), werden also
        Census-uebernommen. Ergebnis: 2 statt 1 (Census hat Vorrang vor
        target_size um keine Jahre komplett zu verlieren).
        """
        data = [
            ({"A", "B"}, 2020),
            ({"C", "D"}, 2021),
        ]
        result = stratified_sample(data, target_size=1)
        # Beide Strata sind Census (1 <= 5)
        assert result.sample_size == 2
        assert result.strata_info[2020].is_census is True
        assert result.strata_info[2021].is_census is True

    def test_target_size_one(self) -> None:
        data = _make_patents({2020: 100, 2021: 200})
        result = stratified_sample(data, target_size=1)
        assert result.sample_size == 1

    def test_wide_year_range_sparse(self) -> None:
        """30 Jahre mit je 2 Patenten = 60 total, target 20.

        Alle Strata sind Census (2 <= 5), daher werden alle 60 uebernommen.
        """
        years = {y: 2 for y in range(1993, 2023)}
        data = _make_patents(years)
        result = stratified_sample(data, target_size=20, census_threshold=5)
        # Census hat Vorrang: alle 60 werden uebernommen
        assert result.sample_size == 60
        assert all(info.is_census for info in result.strata_info.values())

    def test_one_large_one_tiny_stratum(self) -> None:
        """Ein dominantes Jahr + ein winziges Jahr."""
        data = _make_patents({2020: 1, 2021: 99999})
        result = stratified_sample(data, target_size=10000)
        # 2020 hat 1 Patent (Census)
        assert result.strata_info[2020].sample_count == 1
        assert result.strata_info[2020].is_census is True
        # Rest geht an 2021
        assert result.strata_info[2021].sample_count == 9999

    def test_result_data_matches_original_format(self) -> None:
        """Stichprobendaten muessen dasselbe Format haben wie Eingabe."""
        data = _make_patents({2020: 5000, 2021: 5000})
        result = stratified_sample(data, target_size=1000)
        for codes, year in result.sampled_data:
            assert isinstance(codes, set)
            assert isinstance(year, int)
            assert len(codes) >= 2
