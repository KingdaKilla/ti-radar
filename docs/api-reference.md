# API-Referenz — TI-Radar

## Basis-URL

- Entwicklung: `http://localhost:8000`
- Frontend-Proxy: Vite leitet `/api` und `/health` automatisch an `:8000` weiter

## Endpoints

### POST /api/v1/radar

Fuehrt alle acht Use Cases parallel aus und liefert ein komplettes Dashboard-Objekt.

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
      {"year": 2016, "patents": 80, "projects": 3, "patents_growth": null, "projects_growth": null}
    ],
    "top_countries": [
      {"country": "DE", "patents": 300, "projects": 15, "total": 315}
    ]
  },
  "maturity": {
    "phase": "Mature",
    "phase_de": "Ausgereift",
    "confidence": 0.95,
    "cagr": -2.21,
    "maturity_percent": 96.0,
    "saturation_level": 1109.04,
    "inflection_year": 2021.02,
    "r_squared": 0.9977,
    "time_series": [...],
    "s_curve_fitted": [...]
  },
  "competitive": {
    "hhi_index": 1250.5,
    "concentration_level": "Low",
    "top_3_share": 0.35,
    "top_actors": [
      {"name": "SIEMENS AG", "count": 45, "share": 0.12}
    ],
    "network_nodes": [{"id": 0, "name": "Siemens", "count": 45, "type": "both"}],
    "network_edges": [{"source": 0, "target": 1, "weight": 5}],
    "full_actors": [
      {"rank": 1, "name": "SIEMENS AG", "patents": 30, "projects": 15, "total": 45, "share": 0.12, "country": "DE", "is_sme": false, "is_coordinator": true}
    ]
  },
  "funding": {
    "total_funding_eur": 45000000.0,
    "funding_cagr": 12.3,
    "avg_project_size": 3500000.0,
    "by_programme": [...],
    "time_series": [...],
    "instrument_breakdown": [
      {"instrument": "RIA", "count": 15, "funding": 20000000.0}
    ]
  },
  "cpc_flow": {
    "matrix": [[0.0, 0.41], [0.41, 0.0]],
    "labels": ["G06N", "G06F"],
    "colors": ["#4e79a7", "#f28e2b"],
    "total_patents_analyzed": 1799,
    "total_connections": 73,
    "cpc_level": 4,
    "year_data": {},
    "cpc_descriptions": {}
  },
  "geographic": {
    "total_countries": 25,
    "total_cities": 150,
    "cross_border_share": 0.45,
    "country_distribution": [
      {"country": "DE", "patents": 300, "projects": 15, "total": 315}
    ],
    "city_distribution": [
      {"city": "Berlin", "count": 42}
    ],
    "collaboration_pairs": [
      {"country_a": "DE", "country_b": "FR", "count": 18}
    ]
  },
  "research_impact": {
    "h_index": 12,
    "total_papers": 250,
    "avg_citations": 15.3,
    "influential_ratio": 0.08,
    "citation_trend": [
      {"year": 2020, "paper_count": 30, "citations": 450}
    ],
    "top_papers": [
      {"title": "...", "year": 2021, "citations": 150, "venue": "Nature"}
    ],
    "top_venues": [
      {"venue": "Nature", "count": 8}
    ],
    "publication_types": [
      {"type": "JournalArticle", "count": 180}
    ]
  },
  "temporal": {
    "new_entrant_rate": 0.35,
    "persistence_rate": 0.65,
    "dominant_programme": "HORIZON",
    "actor_timeline": [
      {"name": "SIEMENS AG", "years_active": 8, "total_count": 45}
    ],
    "programme_evolution": [
      {"year": 2020, "RIA": 5, "IA": 3, "CSA": 1}
    ],
    "entrant_persistence_trend": [
      {"year": 2020, "total_actors": 120, "new_entrant_rate": 0.35, "persistence_rate": 0.65}
    ],
    "technology_breadth": [
      {"year": 2020, "unique_cpc_sections": 6}
    ]
  },
  "explainability": {
    "sources_used": ["EPO DOCDB (lokal)", "CORDIS (lokal)", "Semantic Scholar"],
    "methods": ["FTS5-Volltextsuche", "CAGR", "HHI-Index", "S-Curve", "h-Index", "Jaccard"],
    "deterministic": true,
    "warnings": [],
    "query_time_ms": 60
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
  "timestamp": "2026-02-18T14:30:00.000000",
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

### GET /api/v1/suggestions

Autocomplete-Vorschlaege via FTS5-Prefix-Suche mit Ngram-Extraktion.

**Query Parameters:**

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `q` | `string` | `""` | Suchbegriff (min. 1 Zeichen) |
| `limit` | `int` | `8` | Max. Anzahl Vorschlaege |

**Response (200 OK):**

```json
["quantum computing", "quantum dots", "quantum key distribution"]
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
