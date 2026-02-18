"""Tests fuer CPC-Technologiefluss (Jaccard Co-Klassifikation)."""

from ti_radar.domain.cpc_flow import (
    assign_colors,
    build_cooccurrence,
    build_cooccurrence_with_years,
    build_jaccard_from_sql,
    build_year_data_from_aggregates,
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


class TestBuildJaccardFromSql:
    """Tests fuer Jaccard-Matrix aus SQL-Aggregaten."""

    def test_basic(self) -> None:
        top_codes = ["A", "B", "C"]
        code_counts = {"A": 10, "B": 8, "C": 5}
        pair_counts = [("A", "B", 6), ("A", "C", 3), ("B", "C", 2)]
        matrix, connections = build_jaccard_from_sql(top_codes, code_counts, pair_counts)
        assert connections == 3
        assert len(matrix) == 3
        # A-B: 6 / (10 + 8 - 6) = 0.5
        assert matrix[0][1] == 0.5
        assert matrix[1][0] == 0.5

    def test_symmetry(self) -> None:
        top_codes = ["A", "B"]
        code_counts = {"A": 10, "B": 10}
        pair_counts = [("A", "B", 5)]
        matrix, _ = build_jaccard_from_sql(top_codes, code_counts, pair_counts)
        assert matrix[0][1] == matrix[1][0]

    def test_diagonal_zero(self) -> None:
        top_codes = ["A", "B"]
        code_counts = {"A": 10, "B": 10}
        pair_counts = [("A", "B", 5)]
        matrix, _ = build_jaccard_from_sql(top_codes, code_counts, pair_counts)
        assert matrix[0][0] == 0.0
        assert matrix[1][1] == 0.0

    def test_perfect_overlap(self) -> None:
        """Jaccard = 1.0 wenn alle Patente beide Codes haben."""
        top_codes = ["A", "B"]
        code_counts = {"A": 5, "B": 5}
        pair_counts = [("A", "B", 5)]
        matrix, _ = build_jaccard_from_sql(top_codes, code_counts, pair_counts)
        assert matrix[0][1] == 1.0

    def test_empty_input(self) -> None:
        matrix, connections = build_jaccard_from_sql([], {}, [])
        assert matrix == []
        assert connections == 0

    def test_single_code(self) -> None:
        matrix, connections = build_jaccard_from_sql(["A"], {"A": 10}, [])
        assert matrix == []
        assert connections == 0

    def test_unknown_pair_code_ignored(self) -> None:
        top_codes = ["A", "B"]
        code_counts = {"A": 10, "B": 10}
        pair_counts = [("A", "B", 5), ("A", "Z", 3)]  # Z nicht in top_codes
        matrix, connections = build_jaccard_from_sql(top_codes, code_counts, pair_counts)
        assert connections == 1  # Nur A-B, nicht A-Z


class TestBuildYearDataFromAggregates:
    """Tests fuer Year-Data-Struktur aus SQL-Aggregaten."""

    def test_structure(self) -> None:
        all_codes = ["A", "B", "C"]
        cpc_year = [("A", 2020, 10), ("B", 2020, 5), ("A", 2021, 12)]
        pair_year = [("A", "B", 2020, 3)]
        result = build_year_data_from_aggregates(all_codes, cpc_year, pair_year)
        assert "min_year" in result
        assert "max_year" in result
        assert "all_labels" in result
        assert "pair_counts" in result
        assert "cpc_counts" in result

    def test_year_range(self) -> None:
        cpc_year = [("A", 2019, 5), ("A", 2022, 8)]
        result = build_year_data_from_aggregates(["A"], cpc_year, [])
        assert result["min_year"] == 2019
        assert result["max_year"] == 2022

    def test_cpc_counts(self) -> None:
        cpc_year = [("A", 2020, 10), ("B", 2020, 5)]
        result = build_year_data_from_aggregates(["A", "B"], cpc_year, [])
        assert result["cpc_counts"]["2020"]["A"] == 10
        assert result["cpc_counts"]["2020"]["B"] == 5

    def test_pair_counts(self) -> None:
        pair_year = [("A", "B", 2020, 3), ("A", "B", 2021, 7)]
        result = build_year_data_from_aggregates(["A", "B"], [], pair_year)
        assert result["pair_counts"]["2020"]["A|B"] == 3
        assert result["pair_counts"]["2021"]["A|B"] == 7

    def test_pair_key_ordering(self) -> None:
        """Pair-Key soll alphabetisch sortiert sein (A|B, nicht B|A)."""
        pair_year = [("B", "A", 2020, 5)]  # Ungeordnet
        result = build_year_data_from_aggregates(["A", "B"], [], pair_year)
        assert "A|B" in result["pair_counts"]["2020"]

    def test_empty_input(self) -> None:
        result = build_year_data_from_aggregates([], [], [])
        assert result["min_year"] == 0
        assert result["max_year"] == 0
        assert result["all_labels"] == []

    def test_all_labels_passed_through(self) -> None:
        codes = ["A", "B", "C", "D", "E"]
        result = build_year_data_from_aggregates(codes, [], [])
        assert result["all_labels"] == codes
