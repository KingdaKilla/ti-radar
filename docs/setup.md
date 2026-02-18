# Setup-Anleitung — TI-Radar

## Voraussetzungen

- Python >= 3.12
- Node.js >= 18
- ~1 GB Speicher fuer Datenbanken (pro importiertem EPO-ZIP)

## Installation

### Backend

```bash
pip install -e ".[dev]"
```

Umgebungsvariablen werden ueber eine `.env`-Datei im Projektverzeichnis konfiguriert (siehe Abschnitt "Umgebungsvariablen"). API-Keys sind optional — die Hauptdaten kommen aus lokalen SQLite-Datenbanken.

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

### CPC-Normalisierung (optional, empfohlen)

Erstellt eine normalisierte `patent_cpc`-Tabelle fuer SQL-native Jaccard-Berechnung (UC5). Ohne diese Migration funktioniert UC5 trotzdem, nutzt aber einen Python-Fallback mit 10.000-Patent-Stichprobe.

```bash
python scripts/migrate_cpc.py --db data/patents.db
```

Das Script ist idempotent (DROP + CREATE) und benoetigt ~20 Minuten fuer die volle Datenbank (~330M Patente). Bei `patents_mini.db` dauert es nur wenige Sekunden.

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

## CI/CD (GitHub Actions)

Drei Workflows unter `.github/workflows/`:

| Workflow | Trigger (Pfad-Filter) | Jobs |
|----------|----------------------|------|
| `backend.yml` | `src/`, `tests/`, `pyproject.toml` | Ruff Lint, Mypy Type Check, Pytest (Coverage >= 60%) |
| `frontend.yml` | `frontend/` | `npm ci` + `vite build` + Verify `dist/index.html` |
| `docker.yml` | `Dockerfile.*`, `docker-compose.yml` | `docker compose build` |

Alle Workflows laufen auf `ubuntu-latest` bei Push/PR auf `master`. Keine GitHub Secrets noetig — Tests mocken externe APIs, Datenbanken sind nicht in CI erforderlich.

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
