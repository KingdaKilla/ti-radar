#!/usr/bin/env python3
"""
CORDIS Bulk Data Import Script.

Imports FP7, H2020, and HORIZON Europe project data from CORDIS bulk downloads
into a local SQLite database. Adapted from Prototype 4.

Usage:
    python scripts/import_cordis_bulk.py \
        --source "../../04_Daten/Bulk-Downloads" \
        --output "data/cordis.db"

    # Skip publications for faster import:
    python scripts/import_cordis_bulk.py \
        --source "../../04_Daten/Bulk-Downloads" \
        --output "data/cordis.db" \
        --skip-publications
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import zipfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Metadaten ueber den Import
CREATE TABLE IF NOT EXISTS import_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    file_name TEXT NOT NULL,
    import_date TEXT NOT NULL,
    record_count INTEGER,
    cordis_update_date TEXT
);

-- Projekte (alle Framework-Programme vereint)
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    rcn INTEGER,
    framework TEXT NOT NULL,
    acronym TEXT,
    title TEXT NOT NULL,
    objective TEXT,
    keywords TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT,
    total_cost REAL,
    ec_max_contribution REAL,
    funding_scheme TEXT,
    topics TEXT,
    legal_basis TEXT,
    cordis_update_date TEXT
);

-- Organisationen (Projektteilnehmer)
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organisation_id INTEGER,
    project_id INTEGER,
    name TEXT NOT NULL,
    short_name TEXT,
    country TEXT,
    city TEXT,
    role TEXT,
    activity_type TEXT,
    sme TEXT,
    ec_contribution REAL,
    total_cost REAL
);

-- Publikationen (aus projectPublications)
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    title TEXT,
    authors TEXT,
    journal TEXT,
    publication_date TEXT,
    doi TEXT,
    open_access TEXT
);

-- Indizes fuer Suche
CREATE INDEX IF NOT EXISTS idx_projects_framework ON projects(framework);
CREATE INDEX IF NOT EXISTS idx_projects_dates ON projects(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_orgs_country ON organizations(country);
CREATE INDEX IF NOT EXISTS idx_orgs_project ON organizations(project_id);
CREATE INDEX IF NOT EXISTS idx_orgs_name ON organizations(name);
CREATE INDEX IF NOT EXISTS idx_pubs_project ON publications(project_id);
"""

FTS_SCHEMA_SQL = """
-- Volltextsuche fuer Keywords/Titles
CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
    title,
    objective,
    keywords,
    content='projects',
    content_rowid='id'
);

-- Trigger fuer automatische FTS-Updates
CREATE TRIGGER IF NOT EXISTS projects_ai AFTER INSERT ON projects BEGIN
    INSERT INTO projects_fts(rowid, title, objective, keywords)
    VALUES (new.id, new.title, new.objective, new.keywords);
END;

CREATE TRIGGER IF NOT EXISTS projects_ad AFTER DELETE ON projects BEGIN
    INSERT INTO projects_fts(projects_fts, rowid, title, objective, keywords)
    VALUES ('delete', old.id, old.title, old.objective, old.keywords);
END;

CREATE TRIGGER IF NOT EXISTS projects_au AFTER UPDATE ON projects BEGIN
    INSERT INTO projects_fts(projects_fts, rowid, title, objective, keywords)
    VALUES ('delete', old.id, old.title, old.objective, old.keywords);
    INSERT INTO projects_fts(rowid, title, objective, keywords)
    VALUES (new.id, new.title, new.objective, new.keywords);
END;
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect_framework(filename: str) -> str:
    """Detect framework programme from filename."""
    lower = filename.lower()
    if "fp7" in lower:
        return "FP7"
    if "h2020" in lower:
        return "H2020"
    if "horizon" in lower:
        return "HORIZON"
    return "UNKNOWN"


def _parse_float(value: Any) -> float | None:
    """Parse float value, returning None for invalid values."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def stream_json_array(zip_path: Path, json_filename: str) -> Generator[dict[str, Any], None, None]:
    """Stream JSON array from ZIP file."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(json_filename) as f:
            content = f.read().decode("utf-8")
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    yield from data
                else:
                    logger.warning(f"Expected array in {json_filename}, got {type(data)}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in {json_filename}: {e}")


# ---------------------------------------------------------------------------
# Import Functions
# ---------------------------------------------------------------------------

def import_projects(conn: sqlite3.Connection, zip_path: Path, framework: str) -> int:
    """Import projects from ZIP file."""
    cursor = conn.cursor()
    count = 0

    logger.info(f"Importing projects from {zip_path.name}...")

    for project in stream_json_array(zip_path, "project.json"):
        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO projects (
                    id, rcn, framework, acronym, title, objective, keywords,
                    start_date, end_date, status, total_cost, ec_max_contribution,
                    funding_scheme, topics, legal_basis, cordis_update_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.get("id"),
                    project.get("rcn"),
                    framework,
                    project.get("acronym"),
                    project.get("title", ""),
                    project.get("objective"),
                    project.get("keywords"),
                    project.get("startDate"),
                    project.get("endDate"),
                    project.get("status"),
                    _parse_float(project.get("totalCost")),
                    _parse_float(project.get("ecMaxContribution")),
                    project.get("fundingScheme"),
                    project.get("topics"),
                    project.get("legalBasis"),
                    project.get("contentUpdateDate"),
                ),
            )
            count += 1

            if count % 5000 == 0:
                logger.info(f"  Imported {count} projects...")
                conn.commit()

        except Exception as e:
            logger.warning(f"Error importing project {project.get('id')}: {e}")

    conn.commit()
    logger.info(f"  Total: {count} projects imported from {framework}")
    return count


def import_organizations(conn: sqlite3.Connection, zip_path: Path) -> int:
    """Import organizations from ZIP file."""
    cursor = conn.cursor()
    count = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        if "organization.json" not in zf.namelist():
            logger.info(f"  No organization.json in {zip_path.name}, skipping")
            return 0

    logger.info(f"Importing organizations from {zip_path.name}...")

    for org in stream_json_array(zip_path, "organization.json"):
        try:
            cursor.execute(
                """
                INSERT INTO organizations (
                    organisation_id, project_id, name, short_name, country,
                    city, role, activity_type, sme, ec_contribution, total_cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    org.get("organisationID"),
                    org.get("projectID"),
                    org.get("name", ""),
                    org.get("shortName"),
                    org.get("country"),
                    org.get("city"),
                    org.get("role"),
                    org.get("activityType"),
                    org.get("SME"),
                    _parse_float(org.get("ecContribution")),
                    _parse_float(org.get("totalCost")),
                ),
            )
            count += 1

            if count % 10000 == 0:
                logger.info(f"  Imported {count} organizations...")
                conn.commit()

        except Exception as e:
            logger.warning(f"Error importing org {org.get('organisationID')}: {e}")

    conn.commit()
    logger.info(f"  Total: {count} organizations imported")
    return count


def import_publications(conn: sqlite3.Connection, zip_path: Path) -> int:
    """Import publications from projectPublications ZIP file."""
    cursor = conn.cursor()
    count = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        pub_files = [f for f in zf.namelist() if f.endswith(".json")]
        if not pub_files:
            logger.info(f"  No JSON files in {zip_path.name}, skipping")
            return 0
        pub_file = pub_files[0]

    logger.info(f"Importing publications from {zip_path.name}...")

    for pub in stream_json_array(zip_path, pub_file):
        try:
            cursor.execute(
                """
                INSERT INTO publications (
                    project_id, title, authors, journal, publication_date, doi, open_access
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pub.get("projectID"),
                    pub.get("title"),
                    pub.get("authors"),
                    pub.get("journalTitle"),
                    pub.get("publicationDate"),
                    pub.get("doi"),
                    pub.get("openAccess"),
                ),
            )
            count += 1

            if count % 10000 == 0:
                logger.info(f"  Imported {count} publications...")
                conn.commit()

        except Exception as e:
            logger.warning(f"Error importing publication: {e}")

    conn.commit()
    logger.info(f"  Total: {count} publications imported")
    return count


# ---------------------------------------------------------------------------
# FTS Index
# ---------------------------------------------------------------------------

def rebuild_fts_index(conn: sqlite3.Connection) -> None:
    """Rebuild the FTS index from existing projects."""
    logger.info("Rebuilding FTS index...")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS projects_fts")
    cursor.execute("DROP TRIGGER IF EXISTS projects_ai")
    cursor.execute("DROP TRIGGER IF EXISTS projects_ad")
    cursor.execute("DROP TRIGGER IF EXISTS projects_au")

    cursor.execute("""
        CREATE VIRTUAL TABLE projects_fts USING fts5(
            title, objective, keywords,
            content='projects',
            content_rowid='id'
        )
    """)

    cursor.execute("""
        INSERT INTO projects_fts(rowid, title, objective, keywords)
        SELECT id, title, objective, keywords FROM projects
    """)

    cursor.executescript("""
        CREATE TRIGGER projects_ai AFTER INSERT ON projects BEGIN
            INSERT INTO projects_fts(rowid, title, objective, keywords)
            VALUES (new.id, new.title, new.objective, new.keywords);
        END;

        CREATE TRIGGER projects_ad AFTER DELETE ON projects BEGIN
            INSERT INTO projects_fts(projects_fts, rowid, title, objective, keywords)
            VALUES ('delete', old.id, old.title, old.objective, old.keywords);
        END;

        CREATE TRIGGER projects_au AFTER UPDATE ON projects BEGIN
            INSERT INTO projects_fts(projects_fts, rowid, title, objective, keywords)
            VALUES ('delete', old.id, old.title, old.objective, old.keywords);
            INSERT INTO projects_fts(rowid, title, objective, keywords)
            VALUES (new.id, new.title, new.objective, new.keywords);
        END;
    """)

    conn.commit()
    logger.info("FTS index rebuilt")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(source_dir: Path, output_db: Path, skip_publications: bool = False) -> None:
    """Main import function."""
    logger.info("Starting CORDIS bulk import")
    logger.info(f"  Source: {source_dir}")
    logger.info(f"  Output: {output_db}")

    output_db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(output_db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    logger.info("Creating database schema...")
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    # Find project ZIP files
    project_zips = sorted(source_dir.glob("cordis-*projects-json.zip"))
    if not project_zips:
        logger.error(f"No project ZIP files found in {source_dir}")
        sys.exit(1)

    logger.info(f"Found {len(project_zips)} project files to import")

    total_projects = 0
    total_orgs = 0
    total_pubs = 0

    for zip_path in project_zips:
        framework = detect_framework(zip_path.name)

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing {framework}: {zip_path.name}")

        project_count = import_projects(conn, zip_path, framework)
        total_projects += project_count

        org_count = import_organizations(conn, zip_path)
        total_orgs += org_count

        # Record metadata
        conn.execute(
            """
            INSERT INTO import_metadata (source, file_name, import_date, record_count)
            VALUES (?, ?, ?, ?)
            """,
            (framework, zip_path.name, datetime.now().isoformat(), project_count),
        )
        conn.commit()

    # Import publications (separate files)
    if not skip_publications:
        pub_zips = sorted(source_dir.glob("cordis-*projectPublications-json.zip"))
        for zip_path in pub_zips:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing publications: {zip_path.name}")
            pub_count = import_publications(conn, zip_path)
            total_pubs += pub_count

    # Rebuild FTS index
    rebuild_fts_index(conn)

    # Final statistics
    logger.info(f"\n{'=' * 60}")
    logger.info("Import complete!")
    logger.info(f"  Total projects:      {total_projects:,}")
    logger.info(f"  Total organizations: {total_orgs:,}")
    logger.info(f"  Total publications:  {total_pubs:,}")

    conn.close()
    db_size_mb = output_db.stat().st_size / (1024 * 1024)
    logger.info(f"  Database size:       {db_size_mb:.1f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CORDIS bulk data into SQLite")
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to directory containing CORDIS ZIP files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/cordis.db"),
        help="Output SQLite database path (default: data/cordis.db)",
    )
    parser.add_argument(
        "--skip-publications",
        action="store_true",
        help="Skip importing publications (faster)",
    )

    args = parser.parse_args()

    if not args.source.exists():
        logger.error(f"Source directory does not exist: {args.source}")
        sys.exit(1)

    main(args.source, args.output, args.skip_publications)
