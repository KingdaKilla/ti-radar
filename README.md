# TI-Radar — Technology Intelligence Radar

Ein interaktives Dashboard zur Analyse von Technologie-Reifegrad, Wettbewerbslandschaft und Foerderlandschaft auf Basis von EPO-Patentdaten und EU-CORDIS-Forschungsprojekten.

## Features

- **UC1 — Technologie-Landschaft**: Patentzahlen nach Jahr und Land, CPC-Klassifikations-Heatmap mit Chord-Diagramm
- **UC2 — Reifegrad-Analyse**: S-Kurven-Fit (Logistic + Gompertz), automatische Phasenklassifikation (Emerging/Growing/Mature/Saturation)
- **UC3 — Wettbewerbs-Analyse**: Top-Anmelder, HHI-Konzentrationsindex, Netzwerk-Graph, Akteur-Tabelle
- **UC4 — Foerderungs-Radar**: CORDIS-Foerdersummen (FP7/H2020/Horizon Europe), OpenAIRE-Publikationszahlen
- **UC5 — Technologiefluss**: CPC-Co-Klassifikations-Heatmap, Chord-Diagramm, Jaccard-Index
- **Explainability**: Transparenz-Leiste mit Datenquellen, Methoden und Warnungen (EU AI Act Art. 50)

## Schnellstart mit Docker

### Voraussetzungen

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Datenbanken herunterladen

Die Datenbanken sind als [GitHub Release](https://github.com/KingdaKilla/ti-radar/releases/tag/v1.0.0) verfuegbar:

| Datei | Groesse | Inhalt |
|-------|---------|--------|
| `patents_mini.db` | 139 MB | ~235.000 Patente (Solar Energy, Quantum Computing, Electric Vehicle, CRISPR) |
| `cordis.db` | 433 MB | Vollstaendige EU CORDIS Forschungsprojekte (FP7, H2020, Horizon Europe) |

```bash
# Datenbanken herunterladen und in data/ ablegen
mkdir -p data
# patents_mini.db als data/patents.db speichern (umbenennen!)
# cordis.db als data/cordis.db speichern
```

### Starten

```bash
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
Use-Case-Schicht (UC1-UC5 parallel)
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

Alle Rechte vorbehalten. Nutzung nur mit Genehmigung des Autors. Siehe [LICENSE](LICENSE).
