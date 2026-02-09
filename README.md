# TI-Radar — Technology Intelligence Radar

Ein interaktives Dashboard zur Analyse von Technologie-Reifegrad, Wettbewerbslandschaft und Foerderlandschaft auf Basis von EPO-Patentdaten und EU-CORDIS-Forschungsprojekten.

## Features

- **UC1 — Technologie-Landschaft**: Patentzahlen nach Jahr und Land, CPC-Klassifikations-Heatmap mit Chord-Diagramm
- **UC2 — Reifegrad-Analyse**: S-Kurven-Fit (Logistic + Gompertz), automatische Phasenklassifikation (Emerging/Growing/Mature/Declining)
- **UC3 — Wettbewerbs-Analyse**: Top-Anmelder, HHI-Konzentrationsindex, Martini-John-Ratio, Newcomer-Erkennung
- **UC4 — Foerderungs-Radar**: CORDIS-Foerdersummen (FP7/H2020/Horizon Europe), OpenAIRE-Publikationszahlen
- **Explainability**: Transparenz-Leiste mit Datenquellen, Methoden und Warnungen (EU AI Act Art. 50)

## Schnellstart mit Docker

### Voraussetzungen

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Datenbanken (separat bereitgestellt):
  - `patents.db` (~78 GB) — EPO DOCDB Patentdaten
  - `cordis.db` (~430 MB) — EU CORDIS Forschungsprojekte

### Starten

```bash
# Datenbanken in data/ ablegen
mkdir -p data
# patents.db und cordis.db nach data/ kopieren

# Starten
docker compose up -d

# Dashboard oeffnen
# http://localhost:3000
```

Das System funktioniert auch ohne Datenbanken — es werden dann leere Panels mit Warnungen angezeigt.

### Stoppen

```bash
docker compose down
```

## Manuelle Installation (Entwicklung)

### Voraussetzungen

- Python >= 3.12
- Node.js >= 18

### Backend

```bash
pip install -e ".[dev]"
cp .env.example .env
uvicorn ti_radar.app:create_app --factory --port 8001 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard unter http://localhost:3000 (Vite proxied `/api` automatisch an das Backend).

## Daten importieren

Falls die Datenbanken nicht als Datei vorliegen, koennen sie aus den Rohdaten importiert werden:

### EPO-Patente

```bash
python scripts/import_epo_bulk.py \
  --source "<Pfad-zu-EPO-ZIPs>" \
  --output "data/patents.db"
```

### CORDIS-Projekte

```bash
python scripts/import_cordis_bulk.py \
  --source "<Pfad-zu-CORDIS-Daten>" \
  --output "data/cordis.db"
```

## Tests

```bash
pytest tests/ -v
```

## Architektur

```
Frontend (React + Vite)
    |
    | POST /api/v1/radar
    v
API-Schicht (FastAPI)
    |
    | asyncio.gather()
    v
Use-Case-Schicht (UC1-UC4 parallel)
    |
    v
Domain-Schicht (reine Funktionen: CAGR, HHI, S-Curve)
    |
    v
Infrastruktur (SQLite FTS5 + API-Adapter)
```

Weitere Details: [docs/architecture.md](docs/architecture.md)

## Umgebungsvariablen

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `PATENTS_DB_PATH` | `data/patents.db` | Pfad zur Patent-Datenbank |
| `CORDIS_DB_PATH` | `data/cordis.db` | Pfad zur CORDIS-Datenbank |
| `EPO_OPS_CONSUMER_KEY` | `""` | EPO API Key (optional, Fallback) |
| `OPENAIRE_ACCESS_TOKEN` | `""` | OpenAIRE Token (optional) |

## Lizenz

MIT
