#!/usr/bin/env bash
# Erstellt retrospektiv 50 GitHub Issues mit Labels und weist sie dem TI-Radar Project Board zu.
# Einmalig ausfuehren, dann loeschen.
#
# Voraussetzungen:
#   gh auth status  (muss eingeloggt sein)
#   gh auth refresh -s read:project -s project  (Project-Scope noetig)

set -euo pipefail

GH="${GH:-gh}"
REPO="KingdaKilla/ti-radar"
PROJECT_NR=2

echo "=== Schritt 1: Labels erstellen ==="
declare -A LABELS=(
  ["infrastruktur"]="0075ca:Backend-Architektur, Config, Projektstruktur"
  ["datenimport"]="7057ff:Bulk-Import, Migrationen, DB-Schemas"
  ["use-case"]="e4e669:Implementierung einzelner Use Cases"
  ["frontend"]="a2eeef:React-Komponenten, Visualisierung"
  ["testing"]="008672:Unit-Tests, Integration-Tests"
  ["dokumentation"]="d876e3:Technische Docs, User Stories"
  ["bugfix"]="d73a4a:Fehlerbehebungen"
  ["deployment"]="0e8a16:Docker, Packaging, DevOps"
  ["querschnitt"]="fbca04:Cross-cutting: Export, Explainability"
)

for label in "${!LABELS[@]}"; do
  IFS=':' read -r color desc <<< "${LABELS[$label]}"
  $GH label create "$label" --color "$color" --description "$desc" --repo "$REPO" 2>/dev/null || echo "  Label '$label' existiert bereits"
done

echo ""
echo "=== Schritt 2: Issues erstellen ==="

# Array: "label|title|body"
ISSUES=(
  # --- Infrastruktur ---
  'infrastruktur|Projektstruktur und Build-System aufsetzen|Python-Paketstruktur mit pyproject.toml (setuptools, Python 3.12), editable install, Verzeichnisstruktur nach Schichtenarchitektur (api/, domain/, use_cases/, infrastructure/). Linting (ruff) und Type-Checking (mypy strict) konfiguriert.'
  'infrastruktur|FastAPI-Backend mit Factory Pattern implementieren|create_app() Factory-Funktion mit CORS-Konfiguration, Router-Registration und Health-Endpoint. Pydantic BaseSettings fuer .env-basierte Konfiguration (DB-Pfade, API-Keys, CORS-Origins).'
  'infrastruktur|React + Vite Frontend initialisieren|React SPA mit Vite, Tailwind CSS, Recharts und D3.js. Vite-Proxy von /api und /health auf Backend-Port 8000. Dark-Theme-Design.'
  'infrastruktur|Pydantic Request/Response-Schemas definieren|RadarRequest (technology + years), RadarResponse mit 8 Panel-Models und ExplainabilityMetadata. Alle Felder mit Defaults fuer Graceful Degradation.'
  'infrastruktur|Parallele Radar-Pipeline (asyncio.gather) implementieren|Zentraler POST /api/v1/radar-Endpoint fuehrt alle 8 Use Cases parallel via asyncio.gather mit 30s Timeout aus. Aggregation von Sources, Methods und Warnings in ExplainabilityMetadata.'
  'infrastruktur|Pydantic Settings und API-Key-Konfiguration|Alle 5 API-Quellen (EPO OPS, CORDIS, OpenAIRE, Semantic Scholar, GLEIF) ueber .env-Datei konfigurierbar. .env.example-Template, test_api_keys.py fuer Konnektivitaetstests.'

  # --- Datenimport ---
  'datenimport|EPO DOCDB Bulk-Import-Skript entwickeln|Import von 150 ZIPs EPO-Patentdaten in SQLite. Nested-ZIP-Handling (Outer ZIP -> Inner ZIPs -> XML), HTML-Entity-Sanitizing, Resume-Support via import_metadata-Tabelle. ~5100 Patente/Sekunde.'
  'datenimport|CORDIS Bulk-Import-Skript entwickeln|Import von CORDIS-Projektdaten (FP7, H2020, Horizon Europe) aus CSV/ZIP-Dateien in SQLite mit FTS5-Volltextsuche. ~45 Sekunden Gesamtimport.'
  'datenimport|Patent-Repository mit FTS5-Volltextsuche implementieren|PatentRepository mit async SQLite (aiosqlite), FTS5-Prefix-Suche, count_by_year(), count_families_by_year(), top_applicants(), get_last_full_year() fuer Datenvollstaendigkeit.'
  'datenimport|CORDIS-Repository mit FTS5-Volltextsuche implementieren|CordisRepository mit async SQLite, FTS5-Suche, count_by_year(), funding_by_year(), funding_by_programme(), top_participants(), get_last_full_year().'
  'datenimport|Applicant-Normalisierungsmigration|migrate_applicants.py fuer inkrementelle Normalisierung der Patent-Anmelder in separate applicants- und patent_applicants-Tabellen. Fallback auf denormalisierte Query.'
  'datenimport|CPC-Normalisierungsmigration fuer SQL-native Jaccard|migrate_cpc.py fuer idempotente Normalisierung der CPC-Codes in patent_cpc-Tabelle. Ermoeglicht SQL-native Jaccard-Berechnung ohne 10K-Sampling.'

  # --- Use Cases Backend ---
  'use-case|UC1 Technologie-Landschaft implementieren|Kombinierte Auswertung von Patenten (EPO), Projekten (CORDIS) und Publikationen (OpenAIRE) mit normalisierten YoY-Wachstumsraten (Watts und Porter 1997). Laenderverteilung mit Europa-Fokus.'
  'use-case|UC2 Technologie-Reifegrad mit S-Curve implementieren|S-Curve-Fitting via Levenberg-Marquardt auf kumulative Patent-Familien-Daten. Logistik- und Gompertz-Modell mit Modellselektion. Phasenklassifikation nach Gao et al. (2013).'
  'use-case|UC3 Wettbewerbsanalyse implementieren|Akteur-Ranking aus EPO-Anmeldern und CORDIS-Teilnehmern. HHI-Index, Top-3-Anteil, Ko-Partizipations-Netzwerk, Akteur-Datentabelle. GLEIF LEI-Lookup.'
  'use-case|UC4 Foerderungsradar implementieren|EU-Foerderungsanalyse aus CORDIS-Daten mit CAGR, Programmverteilung (FP7/H2020/HORIZON), Instrumenten-Aufschluesselung (RIA, IA, CSA), gestapelte Zeitreihe.'
  'use-case|UC5 CPC-Technologiefluss (Jaccard) implementieren|CPC-Co-Klassifikationsanalyse mit Jaccard-Index auf Level-4-CPC-Codes (Curran und Leker 2011). Jahr-granulare Daten, CPC-Beschreibungen (130 Klassen + 200 Subklassen).'
  'use-case|UC6 Geografie implementieren|Laenderverteilung (EPO + CORDIS) mit Cross-Border-Anteil, Top-Kooperationsachsen, Top-Staedte. Europa-Fokus mit EU/EEA-Sortierung.'
  'use-case|UC7 Forschungsimpact (Semantic Scholar) implementieren|h-Index (Hirsch 2005) auf Topic-Level via Semantic Scholar API. Zitationstrend, Top-Papers, Top-Venues, Influential-Ratio. Graceful Degradation bei Rate Limiting.'
  'use-case|UC8 Temporale Dynamik implementieren|Akteur-Persistenzanalyse (Malerba und Orsenigo 1999). Programm-Evolution (dynamische Top-8-Instrumente), Technologiebreite (CPC-Sektionen + Subklassen, Leydesdorff et al. 2015).'

  # --- Domain-Logik ---
  'infrastruktur|Deterministische Metriken (CAGR, HHI, Phase) implementieren|Reine Funktionen in domain/metrics.py: cagr(), hhi_index(), classify_maturity_phase(), s_curve_confidence(), merge_country_data(). Alle ohne Seiteneffekte.'
  'use-case|S-Curve-Fitting-Modul entwickeln|domain/scurve.py mit Logistik- und Gompertz-Funktionen, fit_best_model() fuer automatische Modellselektion nach R-Quadrat. Levenberg-Marquardt via scipy.optimize.curve_fit.'
  'use-case|CPC-Beschreibungsbibliothek erstellen|domain/cpc_descriptions.py mit 130 CPC-Klassen und 200 Subklassen-Beschreibungen. describe_cpc() mit Fallback-Kette (exakt -> Klasse -> Sektion).'
  'infrastruktur|API-Health-Monitoring (JWT-Expiry + Runtime-Failure)|domain/api_health.py mit check_jwt_expiry() und detect_runtime_failures(). 3-Tage-Vorwarnung bei Token-Ablauf, ApiAlert-Schema.'

  # --- Externe API-Adapter ---
  'infrastruktur|OpenAIRE-Adapter implementieren|openaire_adapter.py fuer Publikationszahlen pro Jahr via OpenAIRE Search API. Optionaler Access Token fuer hoehere Rate-Limits.'
  'infrastruktur|Semantic Scholar-Adapter implementieren|semantic_scholar_adapter.py fuer Paper-Suche, Zitationen, h-Index via Academic Graph API. Offset-Paginierung, x-api-key-Header.'
  'infrastruktur|GLEIF-Adapter mit SQLite-Cache implementieren|gleif_adapter.py fuer LEI-Lookup via GLEIF API. SQLite-Cache mit 90 Tage TTL (gleif_cache.db). Integriert in UC3.'

  # --- Frontend-Panels ---
  'frontend|UC1 LandscapePanel mit Zeitreihe und Laenderverteilung|Recharts-AreaChart mit YoY-Wachstumsraten, umschaltbar auf absolute Werte. Laender-BarChart mit EU-Fokus. Custom Tooltip, Laendernamen ausgeschrieben.'
  'frontend|UC2 MaturityPanel mit S-Curve-Visualisierung|Kumulatives Liniendiagramm mit S-Curve-Fit und farbigen Phasenbereichen. Umschaltbar auf Balken. Phase-Badge, R-Quadrat-Label, Wendepunkt-Jahr.'
  'frontend|UC3 CompetitivePanel mit drei Ansichten|Balkendiagramm (Top-8, klickbar), Force-Directed-Netzwerkgraph (D3.js), sortierbare Akteur-Tabelle. HHI-Badge, Top-3-Anteil, Formel-Tooltips.'
  'frontend|UC4 FundingPanel mit Programmverteilung|Programmverteilung als farbiger Balken (FP7/H2020/HORIZON). Gestapeltes Balkendiagramm mit klickbarer Legende. Instrumenten-Aufschluesselung. Cross-UC-Verlinkung.'
  'frontend|UC5 CpcFlowPanel mit Heatmap und Chord-Diagramm|Jaccard-Heatmap mit CPC-Farbcodes. D3.js Chord-Diagramm. Interaktive Regler (Slider + Dropdowns). Frontend-Jaccard-Neuberechnung. Top-CPC-Paare.'
  'frontend|UC6 GeographicPanel mit Europa-Fokus|Gestapeltes Laender-BarChart (Patente + Projekte) mit EU-Sortierung. Kooperationsachsen als Fortschrittsbalken. Staedte als Pill-Badges.'
  'frontend|UC7 ResearchImpactPanel mit drei Ansichten|Trend (Paper + Zitationen), Papers (scrollbare Top-Paper-Liste), Venues (horizontales Balkendiagramm). Publikationstyp-Badges. Leerzustand bei Rate Limiting.'
  'frontend|UC8 TemporalPanel mit drei Ansichten|Dynamik (Flaechendiagramm + Raten + Ranking), Programme (gestapelte Instrumente), Breite (Dual-Achsen CPC). toTitleCase() fuer Akteur-Namen.'

  # --- Querschnittsfunktionen ---
  'querschnitt|ExplainabilityBar mit API-Alerts implementieren|Expandierbare Transparenz-Leiste: Quellen, Methoden, Abfragezeit, Warnungen. API-Fehler rot, Warnungen gelb. Deterministisch-Badge.'
  'querschnitt|Autocomplete-Suche mit FTS5 und Debounce|GET /api/v1/suggestions mit FTS5-Prefix-Suche und Ngram-Extraktion. SearchBar mit Debounce, Keyboard-Navigation, Beispiel-Chips.'
  'querschnitt|CSV-Export fuer alle Panels|DownloadButton-Komponente und utils/export.js mit Browser Blob API. Jedes Panel exportiert Rohdaten als CSV.'
  'querschnitt|Cross-UC-Interaktion (Linked Brushing UC3 zu UC4)|Klick auf Akteur in UC3 setzt selectedActor-State. UC4 zeigt ausgewaehlten Akteur als Badge und filtert kontextuell.'
  'frontend|Responsive Dashboard-Layout (RadarGrid)|4x2 Grid: Row 1 UC1+UC2, Row 2 UC3+UC4 (verlinkt), Row 3 UC6+UC8, Row 4 UC5+UC7. Responsive Hoehen, Loading-Skeleton, Error-Retry.'
  'querschnitt|Datenvollstaendigkeit: Greyzone und Tooltip|Backend ermittelt data_complete_until. Zeitreihen-Charts markieren unvollstaendige Jahre mit grauer Hinterlegung und gestrichelter Linie.'
  'querschnitt|Quellen-Fusszeilen in allen Panels|Jedes Panel zeigt Fusszeile mit Datenquellen und Literaturverweisen. Konsistente Darstellung ueber alle 8 UCs.'

  # --- Testing ---
  'testing|Unit-Test-Suite aufbauen (385 Tests)|Unit-Tests fuer alle Module: metrics, cpc_flow, api_health, scurve, suggestions, schemas, API-Adapter, UC-spezifische Tests. pytest-asyncio mit asyncio_mode auto.'
  'testing|Integration-Tests mit FastAPI TestClient|test_api.py mit FastAPI TestClient fuer Radar-Endpoint. test_repositories.py mit In-Memory SQLite + FTS5-Fixtures. Graceful-Degradation-Tests.'

  # --- Bugfixes ---
  'bugfix|Tooltip-Dark-Theme-Fix (13 Instanzen)|Alle Recharts-Tooltips brauchten contentStyle, labelStyle und itemStyle gegen schwarzen Text auf dunklem Hintergrund. 13 betroffene Stellen korrigiert.'
  'bugfix|UC-Daten-Bugfixes (UC2 + UC7 + UC8)|UC2: dataKey count->patents. UC7: dataKey papers->paper_count, avg_citations->citations, Null-Safety. FTS5-Hyphen-Bug. UC8-Width-Crash. CAGR-Periodenberechnung.'
  'bugfix|CORS, Timeout und Null-Safety-Fixes|CORS-Konfiguration, 30s asyncio.gather-Timeout, Null-Safety mit Default-Werten. Y-Axis interval=0. Dead Code entfernt (SankeyDiagram, martini_john_ratio).'

  # --- Deployment & Doku ---
  'deployment|Docker Compose Packaging|Dockerfile.backend (python:3.12-slim), Dockerfile.frontend (node:20-alpine + nginx:alpine), docker-compose.yml, nginx.conf, .dockerignore. Port 3000.'
  'dokumentation|Technische Dokumentation erstellen|docs/architecture.md, docs/api-reference.md, docs/data-model.md, docs/setup.md. Schichtenarchitektur, Endpoints, SQLite-Schemas, Installation.'
  'dokumentation|User Stories dokumentieren|docs/user-stories.md mit detaillierten User Stories und Akzeptanzkriterien fuer alle 8 UCs plus Querschnittsfunktionen. 16 Literaturverweise.'
)

ISSUE_URLS=()

for entry in "${ISSUES[@]}"; do
  IFS='|' read -r label title body <<< "$entry"
  echo "  Erstelle: $title"
  url=$($GH issue create \
    --title "$title" \
    --body "$body" \
    --label "$label" \
    --repo "$REPO" 2>&1)
  ISSUE_URLS+=("$url")
  echo "    -> $url"
  sleep 0.5  # Rate-Limiting vermeiden
done

echo ""
echo "=== Schritt 3: Issues dem Project Board zuweisen ==="

for url in "${ISSUE_URLS[@]}"; do
  echo "  Weise zu: $url"
  $GH project item-add "$PROJECT_NR" --owner KingdaKilla --url "$url" 2>&1 || echo "    FEHLER bei $url"
  sleep 0.3
done

echo ""
echo "=== Fertig! ${#ISSUE_URLS[@]} Issues erstellt und dem Board zugewiesen ==="
