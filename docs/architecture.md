# Architektur — Prototype 5 (Technology Radar)

## Ueberblick

Prototype 5 implementiert ein Technology Radar Dashboard als Single-Page Application mit einem FastAPI-Backend und React-Frontend. Ein einzelner API-Endpoint fuehrt alle vier Use Cases parallel aus und liefert ein komplettes Dashboard-Objekt zurueck.

### Architekturprinzipien

1. **Deterministische Analyse**: Alle Berechnungen (CAGR, HHI, Martini-John, S-Curve-Fit, Phasenklassifikation) sind reine Funktionen ohne Seiteneffekte — reproduzierbar, auditierbar, testbar.
2. **Graceful Degradation**: Jeder Use Case laeuft unabhaengig. Faellt eine Datenquelle aus, liefern die anderen Use Cases trotzdem Ergebnisse.
3. **Explainability by Design**: Jede Response enthaelt Metadaten ueber verwendete Quellen, Methoden und Warnungen (EU AI Act Art. 50, Limited Risk).
4. **Lokale Daten zuerst**: 187 GB EPO-Patentdaten und CORDIS-Projekte in lokalen SQLite-Datenbanken — keine API-Abhaengigkeit fuer Kernfunktionalitaet.

## Schichtenarchitektur

```
┌──────────────────────────────────────────────────────────────┐
│                     API-Schicht (api/)                        │
│  radar.py ── POST /api/v1/radar (ein Endpoint, alle 4 UCs)  │
│  data.py  ── GET /health, GET /api/v1/data/metadata          │
│  schemas.py ── Pydantic Models (RadarRequest, RadarResponse)  │
├──────────────────────────────────────────────────────────────┤
│                  Use-Case-Schicht (use_cases/)                │
│  landscape.py  ── UC1: Technologie-Landschaft                 │
│  maturity.py   ── UC2: Reifegrad-Analyse                      │
│  competitive.py── UC3: Wettbewerbs-Analyse                    │
│  funding.py    ── UC4: Foerderungs-Radar                      │
├──────────────────────────────────────────────────────────────┤
│                   Domain-Schicht (domain/)                     │
│  metrics.py ── Reine Funktionen: cagr(), hhi_index(),         │
│                martini_john_ratio(), classify_maturity_phase() │
│  scurve.py  ── S-Curve: logistic_function(), fit_s_curve()    │
├──────────────────────────────────────────────────────────────┤
│              Infrastruktur-Schicht (infrastructure/)          │
│  repositories/patent_repo.py ── SQLite patents.db (FTS5)      │
│  repositories/cordis_repo.py ── SQLite cordis.db (FTS5)       │
│  adapters/  ── API-Fallbacks (EPO OPS, OpenAIRE, GLEIF)       │
└──────────────────────────────────────────────────────────────┘
```

## Datenfluss

```
                    ┌─────────────────┐
                    │  React Frontend  │
                    │  (Vite, :3000)   │
                    └────────┬────────┘
                             │ POST /api/v1/radar
                             │ { technology: "quantum", years: 10 }
                             v
                    ┌─────────────────┐
                    │  radar.py       │
                    │  (Orchestrator)  │
                    └────────┬────────┘
                             │ asyncio.gather()
              ┌──────┬───────┼───────┬──────┐
              v      v       v       v      │
          UC1      UC2     UC3     UC4      │
       landscape maturity compet. funding   │
              │      │       │       │      │
              v      v       v       v      │
         ┌────────────────────────────┐     │
         │  PatentRepository          │     │
         │  CordisRepository          │     │
         │  (FTS5 Volltext-Suche)     │     │
         └────────────────────────────┘     │
              │      │       │       │      │
              v      v       v       v      │
         ┌────────────────────────────┐     │
         │  patents.db  │  cordis.db  │     │
         │  (EPO DOCDB) │  (CORDIS)   │     │
         └────────────────────────────┘     │
                             │              │
                             v              │
                    ┌─────────────────┐     │
                    │  RadarResponse   │<────┘
                    │  + Explainability│
                    └─────────────────┘
```

## Parallelisierung

Der Radar-Endpoint nutzt `asyncio.gather()` auf zwei Ebenen:

1. **Aeussere Ebene**: Alle 4 Use Cases parallel (`radar.py:40-45`)
2. **Innere Ebene**: Innerhalb jedes UC laufen Datenbank-Queries parallel (z.B. `landscape.py` fuehrt `count_by_year` und `count_by_country` gleichzeitig aus)

Ergebnis: ~51ms fuer alle 4 Use Cases bei "solar energy" (gemessen auf lokaler Hardware).

## Frontend-Architektur

```
App.jsx
├── SearchBar.jsx         ── Technologie + Jahre-Selektor
├── RadarGrid.jsx         ── 2x2 Grid Layout
│   ├── MaturityPanel.jsx ── S-Curve LineChart (kumulativ + Fit)
│   ├── LandscapePanel.jsx── AreaChart + BarChart
│   ├── CompetitivePanel.jsx── BarChart (horizontal)
│   └── FundingPanel.jsx  ── PieChart + BarChart
├── ExplainabilityBar.jsx ── Expandierbare Transparenz-Leiste
└── MetricCard.jsx        ── Wiederverwendbare KPI-Karte
```

State Management: `useRadar` Custom Hook mit `useState` und `useCallback`. Kein Redux — ein einzelner API-Call liefert den gesamten State.

## Konfiguration

Zentral via `config.py` (Pydantic Settings):

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `PATENTS_DB_PATH` | `data/patents.db` | Pfad zur EPO-Datenbank |
| `CORDIS_DB_PATH` | `data/cordis.db` | Pfad zur CORDIS-Datenbank |
| `EPO_OPS_CONSUMER_KEY` | `""` | EPO API Key (Fallback) |
| `OPENAIRE_ACCESS_TOKEN` | `""` | OpenAIRE API Token |

Verfuegbarkeit wird dynamisch via `@property` geprueft (`patents_db_available`, `cordis_db_available`).
