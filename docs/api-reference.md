# API-Referenz — Prototype 5

## Basis-URL

- Entwicklung: `http://localhost:8000`
- Frontend-Proxy: Vite leitet `/api` und `/health` automatisch an `:8000` weiter

## Endpoints

### POST /api/v1/radar

Fuehrt alle vier Use Cases parallel aus und liefert ein komplettes Dashboard-Objekt.

**Request Body:**

```json
{
  "technology": "quantum computing",
  "years": 10
}
```

| Feld | Typ | Pflicht | Constraints | Beschreibung |
|------|-----|---------|-------------|--------------|
| `technology` | `string` | Ja | 1-200 Zeichen | Technologie-Suchbegriff (FTS5) |
| `years` | `int` | Nein | 3-30, Default: 10 | Analysezeitraum in Jahren |

**Response (200 OK):**

```json
{
  "technology": "quantum computing",
  "analysis_period": "2016-2026",
  "landscape": {
    "total_patents": 1234,
    "total_projects": 56,
    "total_publications": 0,
    "time_series": [
      {"year": 2016, "patents": 80, "projects": 3},
      {"year": 2017, "patents": 95, "projects": 5}
    ],
    "top_countries": [
      {"country": "DE", "patents": 300, "projects": 15, "total": 315},
      {"country": "FR", "patents": 200, "projects": 10, "total": 210}
    ]
  },
  "maturity": {
    "phase": "Mature",
    "phase_de": "Ausgereift",
    "confidence": 0.95,
    "cagr": -2.21,
    "martini_john_ratio": 1.117,
    "maturity_percent": 96.0,
    "saturation_level": 1109.04,
    "inflection_year": 2021.02,
    "r_squared": 0.9977,
    "time_series": [
      {"year": 2016, "patents": 6, "projects": 19, "total": 25, "cumulative": 25},
      {"year": 2017, "patents": 8, "projects": 24, "total": 32, "cumulative": 57}
    ],
    "s_curve_fitted": [
      {"year": 2016, "fitted": 18.3},
      {"year": 2017, "fitted": 52.7}
    ],
    "forecast": []
  },
  "competitive": {
    "hhi_index": 1250.5,
    "concentration_level": "Low",
    "top_3_share": 0.35,
    "top_actors": [
      {"name": "SIEMENS AG", "count": 45, "share": 0.12},
      {"name": "FRAUNHOFER", "count": 38, "share": 0.10}
    ]
  },
  "funding": {
    "total_funding_eur": 45000000.0,
    "funding_cagr": 12.3,
    "avg_project_size": 3500000.0,
    "by_programme": [
      {"programme": "H2020", "funding": 30000000.0, "projects": 8},
      {"programme": "HORIZON", "funding": 15000000.0, "projects": 3}
    ],
    "time_series": [
      {"year": 2019, "funding": 5000000.0, "projects": 2}
    ]
  },
  "explainability": {
    "sources_used": ["EPO DOCDB (lokal)", "CORDIS (lokal)"],
    "methods": ["FTS5-Volltextsuche", "CAGR ueber 8 Jahre", "HHI-Index"],
    "deterministic": true,
    "warnings": [],
    "query_time_ms": 51
  }
}
```

**Fehler (422 Unprocessable Entity):**

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "technology"],
      "msg": "String should have at least 1 character"
    }
  ]
}
```

### GET /health

Service Health Check mit Datenbank-Status.

**Response (200 OK):**

```json
{
  "status": "healthy",
  "timestamp": "2026-02-06T14:30:00.000000",
  "data_sources": {
    "patents_db": {
      "available": true,
      "path": "data/patents.db",
      "size_mb": 840.3
    },
    "cordis_db": {
      "available": true,
      "path": "data/cordis.db",
      "size_mb": 433.1
    },
    "epo_api": "not_configured",
    "openaire_api": "public_access"
  }
}
```

### GET /api/v1/data/metadata

Metadaten ueber verfuegbare Datenquellen.

**Response (200 OK):**

```json
{
  "patents_db_available": true,
  "cordis_db_available": true,
  "epo_api_configured": false,
  "openaire_configured": false
}
```

## Explainability-Felder

Jede Radar-Response enthaelt ein `explainability`-Objekt:

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `sources_used` | `string[]` | Verwendete Datenquellen |
| `methods` | `string[]` | Angewandte Analyse-Methoden |
| `deterministic` | `bool` | `true` = keine LLM-Komponente, reproduzierbar |
| `warnings` | `string[]` | Datenqualitaets-Warnungen |
| `query_time_ms` | `int` | Gesamte Antwortzeit in Millisekunden |
