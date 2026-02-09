#!/usr/bin/env python3
"""
Migration: Applicant-Namen aus denormalisiertem Feld in eigene Tabellen aufloesen.

Liest patents.applicant_names (kommasepariert), splittet, normalisiert
und befuellt die neuen Tabellen 'applicants' und 'patent_applicants'.

Inkrementell: setzt bei MAX(patent_id) fort — kein teurer NOT EXISTS-Scan.
Kein vorab-COUNT (zu langsam auf 75 GB), stattdessen Streaming mit Fortschritts-Schaetzung.

Usage:
    python scripts/migrate_applicants.py
    python scripts/migrate_applicants.py --db data/patents.db
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Laengste Suffixe zuerst, damit "CO LTD" vor "LTD" greift
CORPORATE_SUFFIXES = sorted(
    [
        " CO LTD", " LTD", " INC", " CORP", " CORPORATION",
        " GMBH", " AG", " SA", " SAS", " SE", " NV", " BV",
        " KK", " AB", " OY", " AS", " PLC", " LLC", " PTY",
        " & CO KG", " KG",
    ],
    key=len,
    reverse=True,
)


def normalize_applicant_name(name: str) -> str:
    """Firmenname normalisieren: UPPER, Punkte/Kommas entfernen, Suffix strippen."""
    name = name.upper().strip()
    name = name.replace(".", "").replace(",", "")
    for suffix in CORPORATE_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].rstrip()
            break
    return " ".join(name.split())


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_applicants_raw ON applicants(raw_name);
CREATE INDEX IF NOT EXISTS idx_applicants_norm ON applicants(normalized_name);

CREATE TABLE IF NOT EXISTS patent_applicants (
    patent_id INTEGER NOT NULL REFERENCES patents(id),
    applicant_id INTEGER NOT NULL REFERENCES applicants(id),
    PRIMARY KEY (patent_id, applicant_id)
);
CREATE INDEX IF NOT EXISTS idx_pa_applicant ON patent_applicants(applicant_id);
"""


def migrate(db_path: Path, batch_size: int = 50_000) -> None:
    """Migration ausfuehren (inkrementell, streaming ohne vorab-COUNT)."""
    logger.info("Starte Applicant-Migration: %s", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")

    # Schema anlegen
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    # Schnelle Metadaten: MAX-IDs (O(1) via Index)
    max_migrated = conn.execute(
        "SELECT COALESCE(MAX(patent_id), 0) FROM patent_applicants"
    ).fetchone()[0]

    max_patent_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) FROM patents"
    ).fetchone()[0]

    if max_migrated >= max_patent_id:
        logger.info("Alle Patente bereits migriert (max_patent_id=%d).", max_patent_id)
        conn.close()
        return

    # Geschaetzter Fortschritt (ohne teuren COUNT)
    remaining_id_range = max_patent_id - max_migrated
    logger.info(
        "Fortsetzen ab patent_id > %d (max=%d, ~%d IDs verbleibend)",
        max_migrated, max_patent_id, remaining_id_range,
    )

    # Applicant-Cache: nur bestehende Eintraege laden wenn vorhanden
    applicant_cache: dict[str, int] = {}
    if max_migrated > 0:
        logger.info("Lade Applicant-Cache (9M+ Eintraege, bitte warten) ...")
        t_cache = time.time()
        for row in conn.execute("SELECT raw_name, id FROM applicants"):
            applicant_cache[row[0]] = row[1]
        logger.info(
            "Applicant-Cache geladen: %d Eintraege in %.1fs",
            len(applicant_cache), time.time() - t_cache,
        )

    total_links = 0
    total_normalized = 0
    processed = 0
    t0 = time.time()

    current_min_id = max_migrated
    while True:
        rows = conn.execute(
            "SELECT id, applicant_names FROM patents "
            "WHERE id > ? AND applicant_names IS NOT NULL AND applicant_names != '' "
            "ORDER BY id LIMIT ?",
            (current_min_id, batch_size),
        ).fetchall()

        if not rows:
            break

        current_min_id = rows[-1][0]

        for patent_id, applicant_names_str in rows:
            names = [n.strip() for n in applicant_names_str.split(",") if n.strip()]
            for raw_name in names:
                # Applicant anlegen oder aus Cache holen
                if raw_name not in applicant_cache:
                    normalized = normalize_applicant_name(raw_name)
                    if normalized != raw_name.upper().strip():
                        total_normalized += 1
                    conn.execute(
                        "INSERT OR IGNORE INTO applicants (raw_name, normalized_name) "
                        "VALUES (?, ?)",
                        (raw_name, normalized),
                    )
                    row = conn.execute(
                        "SELECT id FROM applicants WHERE raw_name = ?",
                        (raw_name,),
                    ).fetchone()
                    applicant_cache[raw_name] = row[0]

                # Verknuepfung anlegen
                conn.execute(
                    "INSERT OR IGNORE INTO patent_applicants (patent_id, applicant_id) "
                    "VALUES (?, ?)",
                    (patent_id, applicant_cache[raw_name]),
                )
                total_links += 1

        conn.commit()
        processed += len(rows)
        elapsed = time.time() - t0
        rate = processed / elapsed if elapsed > 0 else 0
        pct = (current_min_id - max_migrated) / remaining_id_range * 100
        logger.info(
            "  %d Patente (%.0f/s) | id=%d (%.1f%%) | %d Applicants, %d Links",
            processed, rate, current_min_id, pct, len(applicant_cache), total_links,
        )

    elapsed = time.time() - t0
    logger.info("Migration abgeschlossen in %.1fs", elapsed)
    logger.info("  Verarbeitete Patente:     %d", processed)
    logger.info("  Einzigartige Applicants:  %d", len(applicant_cache))
    logger.info("  Davon normalisiert:       %d", total_normalized)
    logger.info("  Neue Patent-Applicant Links: %d", total_links)

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate applicant_names to normalized tables")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/patents.db"),
        help="Path to patents.db (default: data/patents.db)",
    )

    args = parser.parse_args()

    if not args.db.exists():
        logger.error("Datenbank nicht gefunden: %s", args.db)
        raise SystemExit(1)

    migrate(args.db)
