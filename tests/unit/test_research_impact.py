"""Unit-Tests fuer UC7 Research Impact."""

from ti_radar.use_cases.research_impact import (
    _compute_h_index,
    _compute_venue_distribution,
    _compute_citation_trend,
    _compute_top_papers,
    _compute_publication_types,
)


class TestHIndex:
    def test_basic(self):
        # 3 papers with 5, 3, 1 citations => h=2 (2 papers have >=2 citations)
        assert _compute_h_index([5, 3, 1]) == 2

    def test_all_high(self):
        assert _compute_h_index([10, 10, 10]) == 3

    def test_empty(self):
        assert _compute_h_index([]) == 0

    def test_single_nonzero(self):
        assert _compute_h_index([5]) == 1

    def test_single_zero(self):
        assert _compute_h_index([0]) == 0

    def test_zeros(self):
        assert _compute_h_index([0, 0, 0]) == 0

    def test_descending(self):
        # h=4: 4 papers with >=4 citations
        assert _compute_h_index([10, 8, 5, 4, 3, 1]) == 4


class TestVenueDistribution:
    def test_basic(self):
        papers = [
            {"venue": "Nature", "citationCount": 10},
            {"venue": "Nature", "citationCount": 5},
            {"venue": "Science", "citationCount": 3},
        ]
        result = _compute_venue_distribution(papers, top_n=2)
        assert len(result) == 2
        assert result[0]["venue"] == "Nature"
        assert result[0]["count"] == 2

    def test_empty(self):
        assert _compute_venue_distribution([], top_n=5) == []

    def test_filters_empty_venues(self):
        papers = [{"venue": "", "citationCount": 10}, {"venue": None, "citationCount": 5}]
        result = _compute_venue_distribution(papers, top_n=5)
        assert result == []

    def test_share_calculation(self):
        papers = [
            {"venue": "A", "citationCount": 0},
            {"venue": "A", "citationCount": 0},
            {"venue": "B", "citationCount": 0},
            {"venue": "B", "citationCount": 0},
        ]
        result = _compute_venue_distribution(papers, top_n=5)
        assert result[0]["share"] == 0.5


class TestCitationTrend:
    def test_basic(self):
        papers = [
            {"year": 2020, "citationCount": 10},
            {"year": 2020, "citationCount": 5},
            {"year": 2021, "citationCount": 3},
        ]
        result = _compute_citation_trend(papers)
        assert len(result) == 2
        y2020 = next(r for r in result if r["year"] == 2020)
        assert y2020["citations"] == 15
        assert y2020["paper_count"] == 2

    def test_empty(self):
        assert _compute_citation_trend([]) == []

    def test_missing_year(self):
        papers = [{"year": None, "citationCount": 10}]
        assert _compute_citation_trend(papers) == []


class TestTopPapers:
    def test_basic(self):
        papers = [
            {"title": "A", "venue": "V", "year": 2020, "citationCount": 5,
             "authors": [{"name": "X"}]},
            {"title": "B", "venue": "V", "year": 2021, "citationCount": 10,
             "authors": [{"name": "Y"}, {"name": "Z"}]},
        ]
        result = _compute_top_papers(papers, top_n=2)
        assert result[0]["title"] == "B"
        assert result[0]["citations"] == 10

    def test_authors_truncation(self):
        papers = [{"title": "A", "venue": "V", "year": 2020, "citationCount": 1,
                    "authors": [{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}]}]
        result = _compute_top_papers(papers, top_n=1)
        assert "et al." in result[0]["authors_short"]


class TestPublicationTypes:
    def test_basic(self):
        papers = [
            {"publicationTypes": ["JournalArticle"]},
            {"publicationTypes": ["JournalArticle", "Review"]},
            {"publicationTypes": ["Conference"]},
        ]
        result = _compute_publication_types(papers)
        assert result[0]["type"] == "JournalArticle"
        assert result[0]["count"] == 2

    def test_empty(self):
        assert _compute_publication_types([]) == []
