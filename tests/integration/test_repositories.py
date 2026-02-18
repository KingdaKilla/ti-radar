"""Integration-Tests fuer Patent- und CORDIS-Repositories mit In-Memory SQLite."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from ti_radar.infrastructure.repositories.cordis_repo import CordisRepository
from ti_radar.infrastructure.repositories.patent_repo import PatentRepository


@pytest.fixture()
def patent_db(tmp_path: Path) -> str:
    """Erstellt eine temporaere Patent-DB mit Testdaten und FTS5."""
    db_path = str(tmp_path / "patents.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE patents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publication_number TEXT,
            country TEXT,
            title TEXT,
            publication_date TEXT,
            applicant_names TEXT,
            applicant_countries TEXT,
            cpc_codes TEXT,
            family_id TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE patents_fts USING fts5(
            title, cpc_codes, content=patents, content_rowid=id
        )
    """)

    patents = [
        ("EP1001", "DE", "Quantum computing device", "2020-03-15", "SIEMENS AG", "DE", "G06N10/00", "F1"),
        ("EP1002", "DE", "Quantum processor chip", "2020-07-20", "SIEMENS AG", "DE", "G06N10/00,H01L27/00", "F2"),
        ("EP1003", "FR", "Quantum gate circuit", "2021-01-10", "THALES SA", "FR", "G06N10/00", "F3"),
        ("EP1004", "US", "Quantum error correction", "2021-06-01", "IBM CORP", "US", "G06N10/00", "F4"),
        ("EP1005", "DE", "Solar cell efficiency improvement", "2020-05-01", "FRAUNHOFER", "DE", "H01L31/00", "F5"),
        ("EP1006", "JP", "Solar panel manufacturing", "2021-03-15", "PANASONIC", "JP", "H01L31/00", "F6"),
        ("EP1007", "DE", "Quantum key distribution", "2022-01-01", "SIEMENS AG", "DE", "H04L9/08", "F7"),
        ("EP1008", "FR", "Quantum sensor array", "2022-06-15", "THALES SA", "FR", "G01N21/00", "F8"),
        ("EP1009", "US", "Quantum computing method", "2023-01-20", "GOOGLE LLC", "US", "G06N10/00", "F9"),
        ("EP1010", "DE", "Quantum machine learning", "2023-08-10", "SAP SE", "DE", "G06N10/00", "F10"),
    ]

    for p in patents:
        conn.execute(
            "INSERT INTO patents (publication_number, country, title, publication_date, "
            "applicant_names, applicant_countries, cpc_codes, family_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            p,
        )

    # FTS5 befuellen
    conn.execute("""
        INSERT INTO patents_fts (rowid, title, cpc_codes)
        SELECT id, title, cpc_codes FROM patents
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def patent_db_normalized(tmp_path: Path) -> str:
    """Patent-DB mit normalisierten Applicant-Tabellen und Multi-Applicant-Daten."""
    db_path = str(tmp_path / "patents_norm.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE patents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publication_number TEXT,
            country TEXT,
            title TEXT,
            publication_date TEXT,
            applicant_names TEXT,
            applicant_countries TEXT,
            cpc_codes TEXT,
            family_id TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE patents_fts USING fts5(
            title, cpc_codes, content=patents, content_rowid=id
        )
    """)

    # Multi-Applicant Patente: EP2001 hat zwei Anmelder
    patents = [
        ("EP2001", "DE", "Quantum computing device", "2020-03-15",
         "SIEMENS AG, BOSCH GMBH", "DE, DE", "G06N10/00", "F1"),
        ("EP2002", "DE", "Quantum processor chip", "2020-07-20",
         "SIEMENS AG", "DE", "G06N10/00", "F2"),
        ("EP2003", "FR", "Quantum gate circuit", "2021-01-10",
         "THALES SA", "FR", "G06N10/00", "F3"),
        ("EP2004", "DE", "Quantum sensor array", "2022-11-15",
         "BOSCH GMBH", "DE", "G06N10/00", "F4"),
    ]

    for p in patents:
        conn.execute(
            "INSERT INTO patents (publication_number, country, title, publication_date, "
            "applicant_names, applicant_countries, cpc_codes, family_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            p,
        )

    conn.execute("""
        INSERT INTO patents_fts (rowid, title, cpc_codes)
        SELECT id, title, cpc_codes FROM patents
    """)

    # Normalisierte Applicant-Tabellen
    conn.execute("""
        CREATE TABLE applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_name TEXT NOT NULL,
            normalized_name TEXT NOT NULL
        )
    """)
    conn.execute("CREATE UNIQUE INDEX idx_applicants_raw ON applicants(raw_name)")
    conn.execute("CREATE INDEX idx_applicants_norm ON applicants(normalized_name)")

    conn.execute("""
        CREATE TABLE patent_applicants (
            patent_id INTEGER NOT NULL REFERENCES patents(id),
            applicant_id INTEGER NOT NULL REFERENCES applicants(id),
            PRIMARY KEY (patent_id, applicant_id)
        )
    """)
    conn.execute("CREATE INDEX idx_pa_applicant ON patent_applicants(applicant_id)")

    # Applicants einfuegen
    applicants = [
        (1, "SIEMENS AG", "SIEMENS"),
        (2, "BOSCH GMBH", "BOSCH"),
        (3, "THALES SA", "THALES"),
    ]
    for a in applicants:
        conn.execute("INSERT INTO applicants (id, raw_name, normalized_name) VALUES (?, ?, ?)", a)

    # Verknuepfungen: EP2001 hat SIEMENS + BOSCH
    links = [
        (1, 1),  # EP2001 -> SIEMENS
        (1, 2),  # EP2001 -> BOSCH
        (2, 1),  # EP2002 -> SIEMENS
        (3, 3),  # EP2003 -> THALES
        (4, 2),  # EP2004 -> BOSCH
    ]
    for patent_id, applicant_id in links:
        conn.execute(
            "INSERT INTO patent_applicants (patent_id, applicant_id) VALUES (?, ?)",
            (patent_id, applicant_id),
        )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def cordis_db(tmp_path: Path) -> str:
    """Erstellt eine temporaere CORDIS-DB mit Testdaten und FTS5."""
    db_path = str(tmp_path / "cordis.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            framework TEXT,
            acronym TEXT,
            title TEXT,
            objective TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            total_cost REAL,
            ec_max_contribution REAL,
            funding_scheme TEXT,
            keywords TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT,
            country TEXT,
            role TEXT,
            city TEXT,
            sme TEXT,
            ec_contribution REAL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE projects_fts USING fts5(
            title, objective, keywords, content=projects, content_rowid=id
        )
    """)

    projects = [
        (1, "H2020", "QCOMP", "Quantum Computing Platform",
         "Develop quantum computing for EU", "2019-01-01", "2022-12-31",
         "CLOSED", 5000000, 4000000, "RIA", "quantum, computing"),
        (2, "H2020", "QSENS", "Quantum Sensor Network",
         "Build quantum sensor infrastructure", "2020-03-01", "2023-02-28",
         "CLOSED", 3000000, 2500000, "RIA", "quantum, sensor"),
        (3, "HORIZON", "QNET", "Quantum Internet Pilot",
         "Quantum networking pilot project", "2022-01-01", "2025-12-31",
         "SIGNED", 8000000, 7000000, "RIA", "quantum, internet, network"),
        (4, "FP7", "SOLAR1", "Solar Energy Innovation",
         "Solar panel research project", "2012-01-01", "2015-12-31",
         "CLOSED", 2000000, 1500000, "CP", "solar, energy, photovoltaic"),
        (5, "H2020", "QALGO", "Quantum Algorithm Design",
         "Quantum algorithms for optimization", "2021-06-01", "2024-05-31",
         "SIGNED", 4000000, 3500000, "RIA", "quantum, algorithm"),
    ]

    for p in projects:
        conn.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", p
        )

    orgs = [
        (1, "TU MUNICH", "DE", "coordinator", "Munich", "no", 2000000),
        (1, "CNRS", "FR", "partner", "Paris", "no", 1500000),
        (2, "THALES SA", "FR", "coordinator", "Paris", "no", 1200000),
        (2, "FRAUNHOFER", "DE", "partner", "Berlin", "no", 800000),
        (3, "KPN NV", "NL", "coordinator", "The Hague", "no", 3000000),
        (3, "TU DELFT", "NL", "partner", "Delft", "no", 2000000),
        (3, "CNRS", "FR", "partner", "Paris", "no", 1500000),
        (4, "FRAUNHOFER", "DE", "coordinator", "Berlin", "no", 1500000),
        (5, "ETH ZURICH", "CH", "coordinator", "Zurich", "no", 2000000),
        (5, "TU MUNICH", "DE", "partner", "Munich", "no", 1000000),
    ]

    for project_id, name, country, role, city, sme, ec_contribution in orgs:
        conn.execute(
            "INSERT INTO organizations (project_id, name, country, role, city, sme, ec_contribution) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, name, country, role, city, sme, ec_contribution),
        )

    conn.execute("""
        INSERT INTO projects_fts (rowid, title, objective, keywords)
        SELECT id, title, objective, keywords FROM projects
    """)
    conn.commit()
    conn.close()
    return db_path


# --- PatentRepository ---


class TestPatentRepository:
    """Tests fuer Patent-Repository mit In-Memory-DB."""

    async def test_count_by_year(self, patent_db: str):
        repo = PatentRepository(patent_db)
        result = await repo.count_by_year("quantum")
        assert len(result) > 0
        assert all("year" in r and "count" in r for r in result)
        total = sum(r["count"] for r in result)
        assert total == 8  # 8 Quantum-Patente

    async def test_count_by_year_with_range(self, patent_db: str):
        repo = PatentRepository(patent_db)
        result = await repo.count_by_year("quantum", start_year=2021, end_year=2022)
        total = sum(r["count"] for r in result)
        assert total == 4  # EP1003 (2021), EP1004 (2021), EP1007 (2022), EP1008 (2022)

    async def test_count_by_country(self, patent_db: str):
        repo = PatentRepository(patent_db)
        result = await repo.count_by_country("quantum")
        assert len(result) > 0
        countries = {r["country"] for r in result}
        assert "DE" in countries

    async def test_top_applicants(self, patent_db: str):
        repo = PatentRepository(patent_db)
        result = await repo.top_applicants("quantum")
        assert len(result) > 0
        # SIEMENS AG hat 3 Quantum-Patente
        top = result[0]
        assert top["name"] == "SIEMENS AG"
        assert top["count"] == 3

    async def test_total_count(self, patent_db: str):
        repo = PatentRepository(patent_db)
        total = await repo.total_count()
        assert total == 10

    async def test_search_no_results(self, patent_db: str):
        repo = PatentRepository(patent_db)
        result = await repo.count_by_year("nonexistent_technology_xyz")
        assert result == []

    async def test_search_solar(self, patent_db: str):
        repo = PatentRepository(patent_db)
        result = await repo.count_by_year("solar")
        total = sum(r["count"] for r in result)
        assert total == 2

    async def test_search_by_technology(self, patent_db: str):
        repo = PatentRepository(patent_db)
        result = await repo.search_by_technology("quantum", limit=5)
        assert len(result) <= 5
        assert len(result) > 0

    async def test_top_applicants_normalized(self, patent_db_normalized: str):
        """Normalisierte Tabellen: Multi-Applicant korrekt aufgeschluesselt."""
        repo = PatentRepository(patent_db_normalized)
        result = await repo.top_applicants("quantum")
        assert len(result) > 0
        names = {r["name"] for r in result}
        # Normalisierte Namen (Suffix gestrippt)
        assert "SIEMENS" in names
        assert "BOSCH" in names
        # SIEMENS: EP2001 + EP2002 = 2, BOSCH: EP2001 + EP2004 = 2
        counts = {r["name"]: r["count"] for r in result}
        assert counts["SIEMENS"] == 2
        assert counts["BOSCH"] == 2
        assert counts["THALES"] == 1

    async def test_top_applicants_fallback_denormalized(self, patent_db: str):
        """Ohne normalisierte Tabellen wird Fallback auf denormalisiertes Feld genutzt."""
        repo = PatentRepository(patent_db)
        # patent_db hat keine applicants/patent_applicants Tabellen
        assert not await repo._has_applicant_tables()
        result = await repo.top_applicants("quantum")
        assert len(result) > 0
        # Fallback: applicant_names als Ganzes, SIEMENS AG hat 3 Patente
        top = result[0]
        assert top["name"] == "SIEMENS AG"
        assert top["count"] == 3

    async def test_get_last_full_year_before_november(self, patent_db: str):
        """Letztes Datum vor November -> Vorjahr zurueckgeben."""
        repo = PatentRepository(patent_db)
        # patent_db max date ist 2023-08-10 (< November)
        result = await repo.get_last_full_year()
        assert result == 2022

    async def test_get_last_full_year_november(self, patent_db_normalized: str):
        """Letztes Datum ab November -> dieses Jahr zurueckgeben."""
        repo = PatentRepository(patent_db_normalized)
        # patent_db_normalized max date ist 2022-11-15 (>= November)
        result = await repo.get_last_full_year()
        assert result == 2022

    async def test_get_last_full_year_empty(self, tmp_path: Path):
        """Leere DB -> None zurueckgeben."""
        db_path = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE patents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publication_number TEXT, country TEXT, title TEXT,
                publication_date TEXT, applicant_names TEXT,
                applicant_countries TEXT, cpc_codes TEXT, family_id TEXT
            )
        """)
        conn.commit()
        conn.close()
        repo = PatentRepository(db_path)
        result = await repo.get_last_full_year()
        assert result is None

    async def test_count_families_by_year(self, patent_db: str):
        """Distinct family_id count per year."""
        repo = PatentRepository(patent_db)
        result = await repo.count_families_by_year("quantum")
        assert len(result) > 0
        assert all("year" in r and "count" in r for r in result)
        total = sum(r["count"] for r in result)
        assert total == 8

    async def test_count_by_applicant_country(self, patent_db: str):
        """Parse comma-separated applicant_countries and aggregate."""
        repo = PatentRepository(patent_db)
        result = await repo.count_by_applicant_country("quantum")
        assert len(result) > 0
        countries = {r["country"] for r in result}
        assert "DE" in countries
        assert "US" in countries
        assert "FR" in countries

    async def test_top_applicants_by_year(self, patent_db: str):
        """Top applicants with year breakdown."""
        repo = PatentRepository(patent_db)
        result = await repo.top_applicants_by_year("quantum")
        assert len(result) > 0
        assert all("name" in r and "year" in r and "count" in r for r in result)
        siemens = [r for r in result if r["name"] == "SIEMENS AG"]
        assert len(siemens) >= 2


# --- CordisRepository ---


class TestCordisRepository:
    """Tests fuer CORDIS-Repository mit In-Memory-DB."""

    async def test_count_by_year(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.count_by_year("quantum")
        assert len(result) > 0
        total = sum(r["count"] for r in result)
        assert total == 4  # 4 Quantum-Projekte

    async def test_count_by_country(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.count_by_country("quantum")
        assert len(result) > 0
        countries = {r["country"] for r in result}
        assert "DE" in countries
        assert "FR" in countries

    async def test_top_organizations(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.top_organizations("quantum")
        assert len(result) > 0
        names = {r["name"] for r in result}
        assert "TU MUNICH" in names or "CNRS" in names

    async def test_funding_by_year(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.funding_by_year("quantum")
        assert len(result) > 0
        total_funding = sum(float(r["funding"]) for r in result)
        assert total_funding > 0

    async def test_funding_by_programme(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.funding_by_programme("quantum")
        assert len(result) > 0
        programmes = {r["programme"] for r in result}
        assert "H2020" in programmes

    async def test_total_count(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        total = await repo.total_count()
        assert total == 5

    async def test_search_no_results(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.count_by_year("nonexistent_technology_xyz")
        assert result == []

    async def test_search_projects(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.search_projects("quantum", limit=3)
        assert len(result) <= 3
        assert len(result) > 0

    async def test_funding_by_year_with_range(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.funding_by_year("quantum", start_year=2020, end_year=2021)
        assert len(result) > 0
        for r in result:
            assert 2020 <= int(r["year"]) <= 2021

    async def test_get_last_full_year(self, cordis_db: str):
        """CORDIS max start_date ist 2022-01-01 → Monat 01 < 11 → Vorjahr 2021."""
        repo = CordisRepository(cordis_db)
        result = await repo.get_last_full_year()
        assert result == 2021

    async def test_get_last_full_year_empty(self, tmp_path: Path):
        """Leere DB → None."""
        db_path = str(tmp_path / "empty_cordis.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY, framework TEXT, acronym TEXT,
                title TEXT, objective TEXT, start_date TEXT, end_date TEXT,
                status TEXT, total_cost REAL, ec_max_contribution REAL,
                funding_scheme TEXT, keywords TEXT
            )
        """)
        conn.commit()
        conn.close()
        repo = CordisRepository(db_path)
        result = await repo.get_last_full_year()
        assert result is None

    async def test_funding_by_year_and_programme(self, cordis_db: str):
        """Korrekte Gruppierung pro Jahr und Programm."""
        repo = CordisRepository(cordis_db)
        result = await repo.funding_by_year_and_programme("quantum")
        assert len(result) > 0
        # Jeder Eintrag hat year, programme, funding, count
        for r in result:
            assert "year" in r
            assert "programme" in r
            assert "funding" in r
            assert "count" in r
            assert r["programme"] in ("H2020", "HORIZON", "FP7", "UNKNOWN")
        # H2020 quantum: 3 Projekte (QCOMP 2019, QSENS 2020, QALGO 2021)
        h2020_entries = [r for r in result if r["programme"] == "H2020"]
        assert len(h2020_entries) >= 1
        h2020_total = sum(r["count"] for r in h2020_entries)
        assert h2020_total == 3

    async def test_co_participation(self, cordis_db: str):
        """Co-Partizipation: Org-Paare in denselben Projekten."""
        repo = CordisRepository(cordis_db)
        result = await repo.co_participation("quantum")
        assert len(result) > 0
        # QCOMP (project 1) hat TU MUNICH + CNRS => ein Paar
        pairs = {(r["actor_a"], r["actor_b"]) for r in result}
        # Entweder (TU MUNICH, CNRS) oder umgekehrt
        has_qcomp_pair = any(
            ("TU MUNICH" in p and "CNRS" in p) for p in pairs
        )
        assert has_qcomp_pair

    async def test_co_participation_no_results(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.co_participation("nonexistent_xyz")
        assert result == []

    async def test_organizations_with_programme(self, cordis_db: str):
        """Org -> Programme Mapping fuer Sankey."""
        repo = CordisRepository(cordis_db)
        result = await repo.organizations_with_programme("quantum")
        assert len(result) > 0
        # Jeder Eintrag hat name, programme, count
        for r in result:
            assert "name" in r
            assert "programme" in r
            assert "count" in r

    async def test_top_organizations_with_country(self, cordis_db: str):
        """Top-Orgs mit Land-Info."""
        repo = CordisRepository(cordis_db)
        result = await repo.top_organizations_with_country("quantum")
        assert len(result) > 0
        # Jeder Eintrag hat name, country, count
        for r in result:
            assert "name" in r
            assert "country" in r
            assert "count" in r
        # TU MUNICH ist DE
        tu = [r for r in result if r["name"] == "TU MUNICH"]
        if tu:
            assert tu[0]["country"] == "DE"


class TestCordisNewMethods:
    """Tests fuer neue CORDIS-Repository-Methoden."""

    async def test_orgs_by_city(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.orgs_by_city("quantum")
        assert isinstance(result, list)
        # Fixture hat city-Werte, also sollten Ergebnisse kommen
        assert len(result) > 0
        assert all("city" in r and "country" in r and "count" in r for r in result)

    async def test_cross_border_projects(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.cross_border_projects("quantum")
        assert "total_projects" in result
        assert "cross_border_count" in result
        assert "cross_border_share" in result
        assert result["total_projects"] > 0

    async def test_cross_border_with_threshold_2(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.cross_border_projects("quantum", min_countries=2)
        assert result["cross_border_count"] > 0

    async def test_country_collaboration_pairs(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.country_collaboration_pairs("quantum")
        assert len(result) > 0
        assert all("country_a" in r and "country_b" in r and "count" in r for r in result)

    async def test_orgs_by_year(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.orgs_by_year("quantum")
        assert len(result) > 0
        assert all("name" in r and "year" in r and "count" in r for r in result)

    async def test_funding_by_instrument(self, cordis_db: str):
        repo = CordisRepository(cordis_db)
        result = await repo.funding_by_instrument("quantum")
        assert len(result) > 0
        assert all("scheme" in r and "year" in r and "count" in r for r in result)
        schemes = {r["scheme"] for r in result}
        assert "RIA" in schemes


class TestPatentCoApplicants:
    """Tests fuer Patent-Co-Anmelder (normalisierte Tabellen noetig)."""

    async def test_co_applicants_normalized(self, patent_db_normalized: str):
        """EP2001 hat SIEMENS + BOSCH => mindestens ein Co-Applicant-Paar."""
        repo = PatentRepository(patent_db_normalized)
        result = await repo.co_applicants("quantum")
        assert len(result) > 0
        # SIEMENS-BOSCH Paar muss vorhanden sein
        has_pair = any(
            ("SIEMENS" in r["actor_a"] and "BOSCH" in r["actor_b"])
            or ("BOSCH" in r["actor_a"] and "SIEMENS" in r["actor_b"])
            for r in result
        )
        assert has_pair

    async def test_co_applicants_returns_empty_without_tables(self, patent_db: str):
        """Ohne normalisierte Tabellen: leere Liste."""
        repo = PatentRepository(patent_db)
        result = await repo.co_applicants("quantum")
        assert result == []

    async def test_applicants_with_cpc_sections(self, patent_db: str):
        """Anmelder mit CPC-Codes (denormalisiert)."""
        repo = PatentRepository(patent_db)
        result = await repo.applicants_with_cpc_sections("quantum")
        assert len(result) > 0
        for r in result:
            assert "applicant_names" in r
            assert "cpc_codes" in r
            assert "count" in r
