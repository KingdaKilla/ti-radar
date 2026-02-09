"""Tests fuer CPC-Technologiefluss (Jaccard Co-Klassifikation)."""

from ti_radar.domain.cpc_flow import (
    assign_colors,
    build_cooccurrence,
    build_cooccurrence_with_years,
    extract_cpc_sets,
    extract_cpc_sets_with_years,
    normalize_cpc,
)


class TestNormalizeCpc:
    """Tests fuer CPC-Code-Normalisierung."""

    def test_level_4(self) -> None:
        assert normalize_cpc("H01L33/00", level=4) == "H01L"

    def test_level_3(self) -> None:
        assert normalize_cpc("H01L33/00", level=3) == "H01"

    def test_short_code(self) -> None:
        assert normalize_cpc("H01", level=4) == "H01"

    def test_whitespace(self) -> None:
        assert normalize_cpc("  H01L 33/00  ", level=4) == "H01L"


class TestExtractCpcSets:
    """Tests fuer CPC-Set-Extraktion aus kommaseparierten Strings."""

    def test_basic(self) -> None:
        result = extract_cpc_sets(["H01L,G06F,B01D"], level=4)
        assert len(result) == 1
        assert result[0] == {"H01L", "G06F", "B01D"}

    def test_single_code_filtered(self) -> None:
        result = extract_cpc_sets(["H01L"], level=4)
        assert len(result) == 0  # Mindestens 2 Codes noetig

    def test_empty_string(self) -> None:
        result = extract_cpc_sets([""], level=4)
        assert len(result) == 0

    def test_multiple_patents(self) -> None:
        result = extract_cpc_sets(["H01L,G06F", "B01D,C07C,H01L"], level=4)
        assert len(result) == 2

    def test_deduplication_within_patent(self) -> None:
        result = extract_cpc_sets(["H01L33/00,H01L21/00,G06F"], level=4)
        assert len(result) == 1
        assert result[0] == {"H01L", "G06F"}  # H01L dedupliziert


class TestBuildCooccurrence:
    """Tests fuer Co-Occurrence-Matrix und Jaccard-Berechnung."""

    def test_simple_pair(self) -> None:
        patent_sets = [{"A", "B"}, {"A", "B"}, {"A", "C"}]
        labels, matrix, connections = build_cooccurrence(patent_sets, top_n=5)
        assert "A" in labels
        assert "B" in labels
        assert connections > 0

    def test_matrix_symmetry(self) -> None:
        patent_sets = [{"A", "B", "C"}, {"A", "B"}, {"B", "C"}]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=5)
        n = len(labels)
        for i in range(n):
            for j in range(n):
                assert matrix[i][j] == matrix[j][i]

    def test_diagonal_zero(self) -> None:
        patent_sets = [{"A", "B"}, {"A", "C"}]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=5)
        for i in range(len(labels)):
            assert matrix[i][i] == 0.0

    def test_single_code_set(self) -> None:
        labels, matrix, connections = build_cooccurrence([{"A"}], top_n=5)
        assert len(labels) <= 1
        assert connections == 0

    def test_empty_input(self) -> None:
        labels, matrix, connections = build_cooccurrence([], top_n=5)
        assert len(labels) == 0
        assert connections == 0

    def test_top_n_limit(self) -> None:
        # 5 verschiedene Codes, top_n=3
        patent_sets = [{"A", "B", "C", "D", "E"}]
        labels, _, _ = build_cooccurrence(patent_sets, top_n=3)
        assert len(labels) <= 3

    def test_jaccard_value_range(self) -> None:
        patent_sets = [{"A", "B"}, {"A", "B"}, {"A", "C"}, {"B", "C"}]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=5)
        for row in matrix:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_perfect_cooccurrence(self) -> None:
        """Wenn A und B immer zusammen auftreten, Jaccard = 1.0."""
        patent_sets = [{"A", "B"}, {"A", "B"}, {"A", "B"}]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=5)
        a_idx = labels.index("A")
        b_idx = labels.index("B")
        assert matrix[a_idx][b_idx] == 1.0


class TestAssignColors:
    """Tests fuer CPC-Sektions-Farbzuweisung."""

    def test_known_sections(self) -> None:
        colors = assign_colors(["A01B", "B65D", "H01L"])
        assert len(colors) == 3
        assert all(c.startswith("#") for c in colors)

    def test_unknown_section(self) -> None:
        colors = assign_colors(["Z99X"])
        assert colors[0] == "#9ca3af"  # Fallback grau

    def test_empty_label(self) -> None:
        colors = assign_colors([""])
        assert colors[0] == "#9ca3af"

    def test_all_sections(self) -> None:
        colors = assign_colors(["A", "B", "C", "D", "E", "F", "G", "H", "Y"])
        assert len(set(colors)) >= 8  # Mindestens 8 verschiedene Farben


class TestExtractCpcSetsWithYears:
    """Tests fuer CPC-Set-Extraktion mit Jahres-Information."""

    def test_basic(self) -> None:
        rows = [{"cpc_codes": "H01L,G06F", "year": 2020}]
        result = extract_cpc_sets_with_years(rows, level=4)
        assert len(result) == 1
        assert result[0][0] == {"H01L", "G06F"}
        assert result[0][1] == 2020

    def test_single_code_filtered(self) -> None:
        rows = [{"cpc_codes": "H01L", "year": 2020}]
        result = extract_cpc_sets_with_years(rows, level=4)
        assert len(result) == 0

    def test_missing_year(self) -> None:
        rows = [{"cpc_codes": "H01L,G06F", "year": 0}]
        result = extract_cpc_sets_with_years(rows, level=4)
        assert len(result) == 0


class TestBuildCooccurrenceWithYears:
    """Tests fuer Co-Occurrence mit Year-Tracking."""

    def test_year_data_structure(self) -> None:
        data = [
            ({"A", "B"}, 2020),
            ({"A", "B"}, 2021),
            ({"A", "C"}, 2021),
        ]
        labels, matrix, connections, year_data = build_cooccurrence_with_years(data, top_n=5)
        assert "min_year" in year_data
        assert "max_year" in year_data
        assert "pair_counts" in year_data
        assert "cpc_counts" in year_data
        assert "all_labels" in year_data

    def test_year_range(self) -> None:
        data = [
            ({"A", "B"}, 2019),
            ({"A", "C"}, 2022),
        ]
        _, _, _, year_data = build_cooccurrence_with_years(data, top_n=5)
        assert year_data["min_year"] == 2019
        assert year_data["max_year"] == 2022

    def test_pair_counts_by_year(self) -> None:
        data = [
            ({"A", "B"}, 2020),
            ({"A", "B"}, 2020),
            ({"A", "B"}, 2021),
        ]
        _, _, _, year_data = build_cooccurrence_with_years(data, top_n=5)
        assert year_data["pair_counts"]["2020"]["A|B"] == 2
        assert year_data["pair_counts"]["2021"]["A|B"] == 1

    def test_cpc_counts_by_year(self) -> None:
        data = [
            ({"A", "B"}, 2020),
            ({"A", "C"}, 2020),
        ]
        _, _, _, year_data = build_cooccurrence_with_years(data, top_n=5)
        assert year_data["cpc_counts"]["2020"]["A"] == 2
        assert year_data["cpc_counts"]["2020"]["B"] == 1
        assert year_data["cpc_counts"]["2020"]["C"] == 1

    def test_matrix_still_correct(self) -> None:
        data = [({"A", "B"}, 2020), ({"A", "B"}, 2020), ({"A", "B"}, 2020)]
        labels, matrix, connections, _ = build_cooccurrence_with_years(data, top_n=5)
        a_idx = labels.index("A")
        b_idx = labels.index("B")
        assert matrix[a_idx][b_idx] == 1.0
        assert connections > 0

    def test_all_labels_returned(self) -> None:
        data = [({"A", "B", "C", "D", "E"}, 2020)]
        _, _, _, year_data = build_cooccurrence_with_years(data, top_n=3)
        assert len(year_data["all_labels"]) == 5  # All codes, not just top 3
