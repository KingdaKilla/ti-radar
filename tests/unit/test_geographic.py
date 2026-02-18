"""Unit-Tests fuer UC6 Geographic Intelligence."""

from ti_radar.domain.metrics import merge_country_data as _merge_country_data


class TestMergeCountryData:
    """Tests fuer Laender-Aggregation."""

    def test_merge_patent_and_cordis_countries(self):
        patent = [{"country": "DE", "count": 10}, {"country": "US", "count": 5}]
        cordis = [{"country": "DE", "count": 3}, {"country": "FR", "count": 7}]
        result = _merge_country_data(patent, cordis)
        de = next(r for r in result if r["country"] == "DE")
        assert de["patents"] == 10
        assert de["projects"] == 3
        assert de["total"] == 13

    def test_merge_empty_inputs(self):
        result = _merge_country_data([], [])
        assert result == []

    def test_merge_sorted_by_total(self):
        patent = [{"country": "DE", "count": 1}]
        cordis = [{"country": "FR", "count": 10}]
        result = _merge_country_data(patent, cordis)
        assert result[0]["country"] == "FR"

    def test_merge_patent_only(self):
        patent = [{"country": "DE", "count": 5}, {"country": "US", "count": 3}]
        result = _merge_country_data(patent, [])
        assert len(result) == 2
        assert result[0]["projects"] == 0

    def test_merge_cordis_only(self):
        cordis = [{"country": "FR", "count": 7}]
        result = _merge_country_data([], cordis)
        assert len(result) == 1
        assert result[0]["patents"] == 0
