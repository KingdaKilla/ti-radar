"""Unit-Tests fuer UC8 Temporal Dynamics."""

from ti_radar.use_cases.temporal import (
    _compute_actor_dynamics,
    _compute_technology_breadth,
    _compute_actor_timeline,
    _compute_programme_evolution,
)


class TestActorDynamics:
    def test_basic_entrant_rate(self):
        actors_by_year = {
            2020: {"A": 2, "B": 1},
            2021: {"A": 1, "B": 1, "C": 3},
        }
        result = _compute_actor_dynamics(actors_by_year)
        assert len(result) == 2
        y2021 = next(r for r in result if r["year"] == 2021)
        assert y2021["new_entrant_rate"] > 0
        assert abs(y2021["new_entrant_rate"] - 1 / 3) < 0.01

    def test_persistence_rate(self):
        actors_by_year = {
            2020: {"A": 2, "B": 1},
            2021: {"A": 1, "C": 3},
        }
        result = _compute_actor_dynamics(actors_by_year)
        y2021 = next(r for r in result if r["year"] == 2021)
        assert abs(y2021["persistence_rate"] - 0.5) < 0.01

    def test_empty(self):
        assert _compute_actor_dynamics({}) == []

    def test_single_year(self):
        result = _compute_actor_dynamics({2020: {"A": 1}})
        assert len(result) == 1
        assert result[0]["new_entrant_rate"] == 1.0

    def test_all_new_second_year(self):
        actors_by_year = {
            2020: {"A": 1},
            2021: {"B": 1, "C": 1},
        }
        result = _compute_actor_dynamics(actors_by_year)
        y2021 = next(r for r in result if r["year"] == 2021)
        assert y2021["new_entrant_rate"] == 1.0
        assert y2021["persistence_rate"] == 0.0


class TestTechnologyBreadth:
    def test_basic(self):
        cpc_by_year = {
            2020: ["G06N10/00", "H01L27/00"],
            2021: ["G06N10/00", "H01L27/00", "H04L9/08"],
        }
        result = _compute_technology_breadth(cpc_by_year)
        assert len(result) == 2
        assert result[0]["unique_cpc_sections"] == 2  # G, H
        assert result[1]["unique_cpc_sections"] == 2  # G, H

    def test_empty(self):
        assert _compute_technology_breadth({}) == []

    def test_multiple_sections(self):
        cpc_by_year = {
            2020: ["A01B1/00,B02C3/00,C03D4/00"],
        }
        result = _compute_technology_breadth(cpc_by_year)
        assert result[0]["unique_cpc_sections"] == 3  # A, B, C


class TestActorTimeline:
    def test_basic(self):
        actors_by_year = {
            2020: {"A": 5, "B": 3},
            2021: {"A": 2, "C": 1},
        }
        result = _compute_actor_timeline(actors_by_year, top_n=2)
        assert len(result) == 2
        assert result[0]["name"] == "A"
        assert result[0]["total_count"] == 7
        assert result[0]["years_active"] == [2020, 2021]

    def test_empty(self):
        assert _compute_actor_timeline({}) == []


class TestProgrammeEvolution:
    def test_basic(self):
        data = [
            {"scheme": "RIA", "year": 2020, "count": 5, "funding": 1000},
            {"scheme": "CSA", "year": 2020, "count": 3, "funding": 500},
            {"scheme": "RIA", "year": 2021, "count": 7, "funding": 2000},
        ]
        result = _compute_programme_evolution(data)
        assert len(result) == 2
        assert result[0]["year"] == 2020
        assert result[0]["RIA"] == 5
        assert result[0]["CSA"] == 3

    def test_empty(self):
        assert _compute_programme_evolution([]) == []
