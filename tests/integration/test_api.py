"""Integration-Tests fuer die FastAPI-Endpoints."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ti_radar.app import create_app


@pytest.fixture()
def _mock_dbs(tmp_path: Path):
    """Erstellt Mock-Datenbanken und patcht Settings."""
    patent_db = str(tmp_path / "patents.db")
    cordis_db = str(tmp_path / "cordis.db")

    # Patent-DB
    conn = sqlite3.connect(patent_db)
    conn.execute("""
        CREATE TABLE patents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publication_number TEXT, country TEXT, title TEXT,
            publication_date TEXT, applicant_names TEXT,
            applicant_countries TEXT, cpc_codes TEXT, family_id TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE patents_fts USING fts5(
            title, cpc_codes, content=patents, content_rowid=id
        )
    """)
    patents = [
        ("EP1001", "DE", "Quantum computing device", "2020-03-15", "SIEMENS AG", "DE", "G06N10/00", "F1"),
        ("EP1002", "US", "Quantum processor", "2021-06-01", "IBM CORP", "US", "G06N10/00", "F2"),
        ("EP1003", "DE", "Quantum computing chip", "2022-01-10", "SIEMENS AG", "DE", "G06N10/00", "F3"),
    ]
    for p in patents:
        conn.execute(
            "INSERT INTO patents (publication_number, country, title, publication_date, "
            "applicant_names, applicant_countries, cpc_codes, family_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", p
        )
    conn.execute("""
        INSERT INTO patents_fts (rowid, title, cpc_codes)
        SELECT id, title, cpc_codes FROM patents
    """)
    conn.commit()
    conn.close()

    # CORDIS-DB
    conn = sqlite3.connect(cordis_db)
    conn.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY, framework TEXT, acronym TEXT,
            title TEXT, objective TEXT, start_date TEXT, end_date TEXT,
            status TEXT, total_cost REAL, ec_max_contribution REAL,
            funding_scheme TEXT, keywords TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, name TEXT, country TEXT, role TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE projects_fts USING fts5(
            title, objective, keywords, content=projects, content_rowid=id
        )
    """)
    conn.execute(
        "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "H2020", "QCOMP", "Quantum Computing Platform",
         "Develop quantum computing", "2020-01-01", "2023-12-31",
         "CLOSED", 5000000, 4000000, "RIA", "quantum, computing"),
    )
    conn.execute(
        "INSERT INTO organizations (project_id, name, country, role) VALUES (?, ?, ?, ?)",
        (1, "TU MUNICH", "DE", "coordinator"),
    )
    conn.execute("""
        INSERT INTO projects_fts (rowid, title, objective, keywords)
        SELECT id, title, objective, keywords FROM projects
    """)
    conn.commit()
    conn.close()

    with patch.dict("os.environ", {
        "PATENTS_DB_PATH": patent_db,
        "CORDIS_DB_PATH": cordis_db,
    }):
        yield


@pytest.fixture()
def client(_mock_dbs):
    """FastAPI TestClient mit Mock-DBs."""
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def client_no_db():
    """FastAPI TestClient ohne Datenbanken."""
    with patch.dict("os.environ", {
        "PATENTS_DB_PATH": "/nonexistent/patents.db",
        "CORDIS_DB_PATH": "/nonexistent/cordis.db",
    }):
        app = create_app()
        yield TestClient(app)


class TestHealthEndpoint:
    """Tests fuer GET /health."""

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "data_sources" in data

    def test_health_shows_db_status(self, client: TestClient):
        response = client.get("/health")
        data = response.json()
        assert data["data_sources"]["patents_db"]["available"] is True
        assert data["data_sources"]["cordis_db"]["available"] is True


class TestMetadataEndpoint:
    """Tests fuer GET /api/v1/data/metadata."""

    def test_metadata_returns_200(self, client: TestClient):
        response = client.get("/api/v1/data/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "patents_db_available" in data
        assert "cordis_db_available" in data

    def test_metadata_no_db(self, client_no_db: TestClient):
        response = client_no_db.get("/api/v1/data/metadata")
        assert response.status_code == 200
        data = response.json()
        assert data["patents_db_available"] is False
        assert data["cordis_db_available"] is False


class TestRadarEndpoint:
    """Tests fuer POST /api/v1/radar."""

    def test_radar_returns_200(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "quantum computing",
            "years": 10,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["technology"] == "quantum computing"
        assert "maturity" in data
        assert "landscape" in data
        assert "competitive" in data
        assert "funding" in data
        assert "explainability" in data

    def test_radar_has_landscape_data(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "quantum",
            "years": 10,
        })
        data = response.json()
        assert data["landscape"]["total_patents"] > 0

    def test_radar_has_explainability(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "quantum",
            "years": 10,
        })
        data = response.json()
        expl = data["explainability"]
        assert expl["deterministic"] is True
        assert expl["query_time_ms"] >= 0
        assert len(expl["sources_used"]) > 0
        assert len(expl["methods"]) > 0

    def test_radar_invalid_technology(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "",
            "years": 10,
        })
        assert response.status_code == 422

    def test_radar_invalid_years(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "test",
            "years": 1,
        })
        assert response.status_code == 422

    def test_radar_default_years(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "quantum",
        })
        assert response.status_code == 200
        data = response.json()
        assert "analysis_period" in data

    def test_radar_no_results(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "nonexistent_technology_xyz_123",
            "years": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["landscape"]["total_patents"] == 0

    def test_radar_without_dbs(self, client_no_db: TestClient):
        response = client_no_db.post("/api/v1/radar", json={
            "technology": "quantum",
            "years": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["explainability"]["warnings"]) > 0

    def test_radar_analysis_period_format(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "quantum",
            "years": 5,
        })
        data = response.json()
        period = data["analysis_period"]
        parts = period.split("-")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_radar_maturity_has_scurve_fields(self, client: TestClient):
        response = client.post("/api/v1/radar", json={
            "technology": "quantum",
            "years": 10,
        })
        data = response.json()
        maturity = data["maturity"]
        # Neue Felder vorhanden (auch wenn leer bei wenig Daten)
        assert "maturity_percent" in maturity
        assert "r_squared" in maturity
        assert "saturation_level" in maturity
        assert "inflection_year" in maturity
        assert "s_curve_fitted" in maturity
        # time_series hat cumulative Feld
        if maturity["time_series"]:
            assert "cumulative" in maturity["time_series"][0]

    def test_radar_competitive_has_extended_fields(self, client: TestClient):
        """UC3 CompetitivePanel enthaelt Netzwerk/Tabellen-Felder."""
        response = client.post("/api/v1/radar", json={
            "technology": "quantum",
            "years": 10,
        })
        data = response.json()
        comp = data["competitive"]
        # Bestehende Felder
        assert "hhi_index" in comp
        assert "top_actors" in comp
        # Netzwerk + Tabelle (Listen, koennen leer sein bei Testdaten)
        assert "network_nodes" in comp
        assert "network_edges" in comp
        assert "full_actors" in comp
        assert isinstance(comp["network_nodes"], list)
        assert isinstance(comp["full_actors"], list)
