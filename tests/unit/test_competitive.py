"""Unit-Tests fuer UC3 Competitive Intelligence Helper-Funktionen."""

from ti_radar.use_cases.competitive import _build_full_table


class TestBuildFullTable:
    """Tests fuer die vollstaendige Akteur-Tabelle."""

    def test_basic_table(self):
        patent_actors = {"SIEMENS": 10, "BOSCH": 5}
        cordis_actors = {"SIEMENS": 3, "CNRS": 7}
        cordis_countries = {"SIEMENS": "DE", "CNRS": "FR"}
        cordis_sme = {"CNRS": True}
        cordis_coordinator = {"SIEMENS": True}
        actor_counts = {"SIEMENS": 13, "CNRS": 7, "BOSCH": 5}
        total = 25

        result = _build_full_table(
            patent_actors, cordis_actors, cordis_countries,
            cordis_sme, cordis_coordinator, actor_counts, total
        )

        assert len(result) == 3
        assert result[0]["name"] == "SIEMENS"
        assert result[0]["rank"] == 1
        assert result[0]["patents"] == 10
        assert result[0]["projects"] == 3
        assert result[0]["total"] == 13
        assert result[0]["country"] == "DE"
        assert result[0]["is_coordinator"] is True
        assert result[0]["is_sme"] is False

    def test_sme_flag(self):
        cordis_sme = {"SME_CORP": True}
        actor_counts = {"SME_CORP": 5}
        result = _build_full_table({}, {}, {}, cordis_sme, {}, actor_counts, 5)
        assert result[0]["is_sme"] is True
        assert result[0]["is_coordinator"] is False

    def test_sorted_by_total_descending(self):
        actor_counts = {"A": 5, "B": 10, "C": 1}
        result = _build_full_table({}, {}, {}, {}, {}, actor_counts, 16)
        assert result[0]["name"] == "B"
        assert result[1]["name"] == "A"
        assert result[2]["name"] == "C"

    def test_share_calculation(self):
        actor_counts = {"A": 50, "B": 50}
        result = _build_full_table({}, {}, {}, {}, {}, actor_counts, 100)
        assert result[0]["share"] == 0.5
        assert result[1]["share"] == 0.5

    def test_zero_total_activity(self):
        actor_counts = {"A": 0}
        result = _build_full_table({}, {}, {}, {}, {}, actor_counts, 0)
        assert result[0]["share"] == 0.0

    def test_empty_input(self):
        result = _build_full_table({}, {}, {}, {}, {}, {}, 0)
        assert result == []

    def test_missing_country_defaults_empty(self):
        actor_counts = {"UNKNOWN_CORP": 5}
        result = _build_full_table({}, {}, {}, {}, {}, actor_counts, 5)
        assert result[0]["country"] == ""

    def test_patent_only_actor(self):
        patent_actors = {"PATENT_ONLY": 8}
        actor_counts = {"PATENT_ONLY": 8}
        result = _build_full_table(patent_actors, {}, {}, {}, {}, actor_counts, 8)
        assert result[0]["patents"] == 8
        assert result[0]["projects"] == 0

    def test_cordis_only_actor(self):
        cordis_actors = {"CORDIS_ONLY": 6}
        actor_counts = {"CORDIS_ONLY": 6}
        result = _build_full_table({}, cordis_actors, {}, {}, {}, actor_counts, 6)
        assert result[0]["patents"] == 0
        assert result[0]["projects"] == 6

    def test_rank_numbering(self):
        actor_counts = {"A": 3, "B": 2, "C": 1}
        result = _build_full_table({}, {}, {}, {}, {}, actor_counts, 6)
        assert [r["rank"] for r in result] == [1, 2, 3]
