# Architektur — TI-Radar (Technology Intelligence Radar)

## Ueberblick

TI-Radar implementiert ein Technology Intelligence Dashboard als Single-Page Application mit einem FastAPI-Backend und React-Frontend. Ein einzelner API-Endpoint fuehrt alle acht Use Cases parallel aus und liefert ein komplettes Dashboard-Objekt zurueck.

### Architekturprinzipien

1. **Deterministische Analyse**: Alle Berechnungen (CAGR, HHI, Martini-John, S-Curve-Fit, Jaccard, h-Index) sind reine Funktionen ohne Seiteneffekte — reproduzierbar, auditierbar, testbar.
2. **Graceful Degradation**: Jeder Use Case laeuft unabhaengig. Faellt eine Datenquelle aus (z.B. Semantic Scholar Rate Limit), liefern die anderen Use Cases trotzdem Ergebnisse.
3. **Explainability by Design**: Jede Response enthaelt Metadaten ueber verwendete Quellen, Methoden und Warnungen (EU AI Act Art. 50, Limited Risk).
4. **Lokale Daten zuerst**: 187 GB EPO-Patentdaten und CORDIS-Projekte in lokalen SQLite-Datenbanken — keine API-Abhaengigkeit fuer Kernfunktionalitaet.

## Schichtenarchitektur

```
┌──────────────────────────────────────────────────────────────┐
│                     API-Schicht (api/)                        │
│  radar.py ── POST /api/v1/radar (ein Endpoint, alle 8 UCs)  │
│  data.py  ── GET /health, GET /api/v1/data/metadata          │
│  schemas.py ── Pydantic Models (RadarRequest, RadarResponse)  │
├──────────────────────────────────────────────────────────────┤
│                  Use-Case-Schicht (use_cases/)                │
│  landscape.py   ── UC1: Technologie-Landschaft               │
│  maturity.py    ── UC2: Reifegrad-Analyse (S-Curve)          │
│  competitive.py ── UC3: Wettbewerbs-Analyse (HHI, Netzwerk)  │
│  funding.py     ── UC4: Foerderungs-Radar (CAGR, Programme)  │
│  cpc_flow.py    ── UC5: Technologiefluss (Jaccard)           │
│  geographic.py  ── UC6: Geografie (Laender, Kooperationen)   │
│  research_impact.py ── UC7: Forschungsimpact (h-Index)       │
│  temporal.py    ── UC8: Temporale Dynamik (Akteur-Persistenz)│
├──────────────────────────────────────────────────────────────┤
│                   Domain-Schicht (domain/)                     │
│  metrics.py ── Reine Funktionen: cagr(), hhi_index(),         │
│                martini_john_ratio(), classify_maturity_phase() │
│  scurve.py  ── S-Curve: logistic + gompertz, fit_best_model() │
│  cpc_flow.py── CPC-Co-Klassifikation, Jaccard-Index           │
│  cpc_descriptions.py ── CPC-Klassen/Subklassen-Bibliothek     │
├──────────────────────────────────────────────────────────────┤
│              Infrastruktur-Schicht (infrastructure/)          │
│  repositories/patent_repo.py ── SQLite patents.db (FTS5)      │
│  repositories/cordis_repo.py ── SQLite cordis.db (FTS5)       │
│  adapters/openaire_adapter.py ── OpenAIRE API (Publikationen) │
│  adapters/semantic_scholar_adapter.py ── Semantic Scholar API  │
│  adapters/gleif_adapter.py ── GLEIF LEI Lookup (SQLite-Cache)  │
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
         ┌──────┬──────┬─────┼─────┬──────┬──────┬──────┐
         v      v      v     v     v      v      v      v
       UC1    UC2    UC3   UC4   UC5    UC6    UC7    UC8
      land.  matur. comp. fund. cpc   geo.  research temp.
         │      │      │     │     │      │      │      │
         v      v      v     v     v      v      v      v
    ┌────────────────────────────────────────────────────┐
    │  PatentRepository  │  CordisRepository             │
    │  (FTS5 Volltext)   │  (FTS5 Volltext)              │
    ├────────────────────┼───────────────────────────────┤
    │  patents.db        │  cordis.db                    │
    │  (EPO DOCDB)       │  (CORDIS)                     │
    └────────────────────┴───────────────────────────────┘
              │                              │
              v                              v
    ┌────────────────┐  ┌──────────────┐  ┌─────────┐
    │ OpenAIRE API   │  │ Semantic     │  │ GLEIF   │
    │ (UC1: Publik.) │  │ Scholar (UC7)│  │ (UC3)   │
    └────────────────┘  └──────────────┘  └─────────┘
                             │
                             v
                    ┌─────────────────┐
                    │  RadarResponse   │
                    │  + Explainability│
                    └─────────────────┘
```

## Parallelisierung

Der Radar-Endpoint nutzt `asyncio.gather()` auf zwei Ebenen:

1. **Aeussere Ebene**: Alle 8 Use Cases parallel (`radar.py`)
2. **Innere Ebene**: Innerhalb jedes UC laufen Datenbank-Queries parallel (z.B. `landscape.py` fuehrt `count_by_year` und `count_by_country` gleichzeitig aus)

Ergebnis: ~60ms fuer alle 8 Use Cases bei lokalen Datenquellen, ~500ms mit externen APIs.

## Frontend-Architektur

```
App.jsx
├── SearchBar.jsx                ── Technologie + Jahre-Selektor
├── RadarGrid.jsx                ── Dashboard Grid Layout (8 Panels)
│   ├── LandscapePanel.jsx       ── UC1: YoY-Wachstumsraten + Laender (Europa-Fokus)
│   ├── MaturityPanel.jsx        ── UC2: S-Curve + Phase-Badge + Reifegrad%
│   ├── CompetitivePanel.jsx     ── UC3: BarChart + Netzwerk + Tabelle + HHI
│   ├── FundingPanel.jsx         ── UC4: PieChart + Stacked BarChart + Instrumente
│   ├── CpcFlowPanel.jsx         ── UC5: Heatmap + ChordDiagram (Jaccard)
│   ├── GeographicPanel.jsx      ── UC6: Laender-BarChart (Europa-Fokus) + Kooperationen
│   ├── ResearchImpactPanel.jsx  ── UC7: Zitationstrend + Papers + Venues
│   └── TemporalPanel.jsx        ── UC8: Akteur-Dynamik + Programme + Breite
├── ForceGraph.jsx               ── D3.js Force-Directed (Akteur-Netzwerk)
├── ChordDiagram.jsx             ── D3.js Chord-Diagramm (CPC-Verflechtung)
├── ActorTable.jsx               ── Sortierbare Datentabelle (UC3)
├── DownloadButton.jsx           ── CSV-Export pro Panel
├── ExplainabilityBar.jsx        ── Expandierbare Transparenz-Leiste
└── MetricCard.jsx               ── Wiederverwendbare KPI-Karte
```

State Management: `useRadar` Custom Hook mit `useState` und `useCallback`. Kein Redux — ein einzelner API-Call liefert den gesamten State.

## Konfiguration

Zentral via `config.py` (Pydantic Settings):

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `PATENTS_DB_PATH` | `data/patents.db` | Pfad zur EPO-Datenbank |
| `CORDIS_DB_PATH` | `data/cordis.db` | Pfad zur CORDIS-Datenbank |
| `GLEIF_CACHE_DB_PATH` | `data/gleif_cache.db` | GLEIF-Cache-Datenbank |
| `EPO_OPS_CONSUMER_KEY` | `""` | EPO API Key (Fallback) |
| `OPENAIRE_ACCESS_TOKEN` | `""` | OpenAIRE API Token |

Verfuegbarkeit wird dynamisch via `@property` geprueft (`patents_db_available`, `cordis_db_available`).
