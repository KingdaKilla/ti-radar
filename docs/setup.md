# Setup-Anleitung — TI-Radar

## Voraussetzungen

- Python >= 3.12
- Node.js >= 18
- ~1 GB Speicher fuer Datenbanken (pro importiertem EPO-ZIP)

## Installation

### Backend

```bash
pip install -e ".[dev]"
cp .env.example .env
```

### Frontend

```bash
cd frontend
npm install
```

## Datenbanken

Die Datenbanken sind als [GitHub Release](https://github.com/KingdaKilla/ti-radar/releases/tag/v1.0.0) verfuegbar:

- `patents_mini.db` (139 MB) — ~235.000 Patente fuer 4 Demo-Technologien
- `cordis.db` (433 MB) — Vollstaendige EU CORDIS Datenbank

Beide Dateien in den `data/`-Ordner legen (`patents_mini.db` als `patents.db` umbenennen).

### Eigene Daten importieren (optional)

```bash
# EPO-Patente (12-25 Stunden fuer alle 150 ZIPs)
python scripts/import_epo_bulk.py \
  --source "<Pfad-zu-EPO-ZIPs>" \
  --output "data/patents.db"

# CORDIS-Projekte (~45 Sekunden)
python scripts/import_cordis_bulk.py \
  --source "<Pfad-zu-CORDIS-Daten>" \
  --output "data/cordis.db"
```

## Starten

### Backend (Port 8000)

```bash
uvicorn ti_radar.app:create_app --factory --port 8000 --reload
```

**Wichtig:** Das `--factory` Flag ist erforderlich, da `create_app` eine Factory-Funktion ist.

### Frontend (Port 3000)

```bash
cd frontend
npm run dev
```

Vite proxied `/api` und `/health` automatisch an `:8000` — keine CORS-Probleme in der Entwicklung.

**Dashboard oeffnen:** http://localhost:3000

## Tests ausfuehren

```bash
# Alle Tests
pytest tests/ -v

# Mit Coverage
pytest tests/ -v --cov=ti_radar

# Nur Unit-Tests
pytest tests/unit/ -v

# Nur Integration-Tests
pytest tests/integration/ -v
```

## Linting & Type-Checking

```bash
ruff check src/
mypy src/
```

## Betrieb ohne Datenbanken

Das System funktioniert auch ohne importierte Daten — die Radar-Response enthaelt dann Warnungen wie "Patent-DB nicht verfuegbar" und liefert leere Panels. So kann die Anwendung sofort gestartet und getestet werden, waehrend der Import im Hintergrund laeuft.

## Umgebungsvariablen

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `PATENTS_DB_PATH` | `data/patents.db` | Pfad zur Patent-Datenbank |
| `CORDIS_DB_PATH` | `data/cordis.db` | Pfad zur CORDIS-Datenbank |
| `EPO_OPS_CONSUMER_KEY` | `""` | EPO API Key (optional, Fallback) |
| `EPO_OPS_CONSUMER_SECRET` | `""` | EPO API Secret |
| `CORDIS_API_KEY` | `""` | CORDIS API Key (optional) |
| `OPENAIRE_ACCESS_TOKEN` | `""` | OpenAIRE Token (optional) |
| `GLEIF_CACHE_DB_PATH` | `data/gleif_cache.db` | GLEIF-Cache-Datenbank |
