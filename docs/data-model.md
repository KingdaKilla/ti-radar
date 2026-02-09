# Datenmodell — TI-Radar

## Ueberblick

Zwei SQLite-Datenbanken mit FTS5-Volltextsuche. Patent-Anmelder koennen optional in normalisierte Tabellen migriert werden (siehe `applicants` / `patent_applicants`).

| Datenbank | Quelle | Inhalt | Groesse |
|-----------|--------|--------|---------|
| `patents.db` | EPO DOCDB Bulk (XML) | Patente weltweit | ~840 MB pro ZIP (von 150) |
| `cordis.db` | CORDIS Bulk (JSON) | EU-Projekte + Organisationen | ~433 MB |

## patents.db

### Tabelle: patents

Bewusst denormalisiert — CPC-Codes und Applicants als kommaseparierte Strings. Keine Joins noetig fuer Aggregationen.

```sql
CREATE TABLE patents (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_number  TEXT UNIQUE,        -- "EP1234567A1"
    country             TEXT,               -- "DE", "FR", "US"
    title               TEXT,               -- Englischer Titel (bevorzugt)
    publication_date    TEXT,               -- "2021-03-15" (ISO 8601)
    applicant_names     TEXT,               -- "SIEMENS AG, BOSCH GMBH"
    applicant_countries TEXT,               -- "DE, DE"
    cpc_codes           TEXT,               -- "G06N10/00, H01L27/00"
    family_id           TEXT                -- DOCDB Family ID
);

CREATE INDEX idx_patents_date    ON patents(publication_date);
CREATE INDEX idx_patents_country ON patents(country);
```

### Tabelle: patents_fts (FTS5 Volltextindex)

```sql
CREATE VIRTUAL TABLE patents_fts USING fts5(
    title,
    cpc_codes,
    content=patents,
    content_rowid=id
);
```

Suche via: `WHERE patents_fts MATCH 'quantum computing'`

### Tabelle: import_metadata

Tracking fuer Resume-Support beim Import.

```sql
CREATE TABLE import_metadata (
    zip_name    TEXT PRIMARY KEY,   -- "EP_DOCDB_001_A.zip"
    imported_at TEXT,               -- ISO 8601 Timestamp
    patent_count INTEGER            -- Anzahl importierter Patente
);
```

### Tabelle: applicants (normalisiert, optional)

Wird durch `scripts/migrate_applicants.py` erzeugt. Enthaelt jeden eindeutigen Anmelder-Namen mit normalisierter Variante (UPPER, Punkte/Kommas entfernt, Firmen-Suffixe wie LTD/GMBH/AG gestrippt).

```sql
CREATE TABLE applicants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_name        TEXT NOT NULL,           -- "SIEMENS AG"
    normalized_name TEXT NOT NULL            -- "SIEMENS"
);

CREATE UNIQUE INDEX idx_applicants_raw  ON applicants(raw_name);
CREATE INDEX        idx_applicants_norm ON applicants(normalized_name);
```

### Tabelle: patent_applicants (Verknuepfung, optional)

N:M-Beziehung zwischen Patenten und Anmeldern. Ermoeglicht korrekte Aufschluesselung von Multi-Anmelder-Patenten (z.B. "SIEMENS AG, BOSCH GMBH" wird zu zwei separaten Links).

```sql
CREATE TABLE patent_applicants (
    patent_id    INTEGER NOT NULL REFERENCES patents(id),
    applicant_id INTEGER NOT NULL REFERENCES applicants(id),
    PRIMARY KEY (patent_id, applicant_id)
);

CREATE INDEX idx_pa_applicant ON patent_applicants(applicant_id);
```

Migration ausfuehren: `python scripts/migrate_applicants.py` (inkrementell, sicher nach EPO-Re-Import).

`PatentRepository.top_applicants()` nutzt automatisch die normalisierten Tabellen wenn vorhanden, sonst Fallback auf `patents.applicant_names`.

## cordis.db

### Tabelle: projects

```sql
CREATE TABLE projects (
    id                   INTEGER PRIMARY KEY,  -- CORDIS Project ID
    framework            TEXT,                  -- "FP7", "H2020", "HORIZON"
    acronym              TEXT,                  -- "QCOMP"
    title                TEXT,
    objective            TEXT,                  -- Langbeschreibung
    start_date           TEXT,                  -- "2020-01-01"
    end_date             TEXT,                  -- "2023-12-31"
    status               TEXT,                  -- "SIGNED", "CLOSED"
    total_cost           REAL,                  -- Gesamtkosten (EUR)
    ec_max_contribution  REAL,                  -- EU-Foerderung (EUR)
    funding_scheme       TEXT,                  -- "RIA", "CSA", "CP"
    keywords             TEXT                   -- Kommaseparierte Keywords
);
```

### Tabelle: organizations

```sql
CREATE TABLE organizations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER REFERENCES projects(id),
    name        TEXT,                  -- "FRAUNHOFER-GESELLSCHAFT"
    country     TEXT,                  -- "DE"
    role        TEXT                   -- "coordinator", "partner"
);

CREATE INDEX idx_org_project ON organizations(project_id);
CREATE INDEX idx_org_country ON organizations(country);
```

### Tabelle: projects_fts (FTS5 Volltextindex)

```sql
CREATE VIRTUAL TABLE projects_fts USING fts5(
    title,
    objective,
    keywords,
    content=projects,
    content_rowid=id
);
```

## EPO DOCDB XML-Struktur

Die Quelldaten liegen als verschachtelte ZIPs vor:

```
04_Daten/Bulk-Downloads/EPO/
├── EP_DOCDB_001_A.zip        ← Aeusseres ZIP (1.4 GB)
│   └── Root/DOC/
│       ├── DOCDB_EP_AM_01.zip  ← Inneres ZIP (pro Land)
│       │   └── *.xml            ← Ein grosses XML pro Land
│       ├── DOCDB_EP_AP_01.zip
│       └── ...
├── EP_DOCDB_002_A.zip
└── ... (150 ZIPs, ~187 GB total)
```

XML-Namespace: `xmlns:exch="http://www.epo.org/exchange"`

Relevante Elemente:
- `<exch:exchange-document>` — Root-Element pro Patent
- `<exch:invention-title lang="en">` — Titel
- `<exch:patent-classifications>` → `<classification-symbol>` — CPC-Codes
- `<exch:parties>` → `<exch:applicants>` → `<exch:applicant>` — Anmelder

## Datenvolumen

| Metrik | Wert |
|--------|------|
| Patente pro ZIP (Durchschnitt) | ~2.2 Mio |
| Import-Geschwindigkeit | ~5,100 Patente/s |
| Import-Zeit pro ZIP | ~7.5 Min |
| CORDIS-Projekte | 80,510 |
| CORDIS-Organisationen | 438,867 |
| CORDIS-Import-Zeit | ~45s |
