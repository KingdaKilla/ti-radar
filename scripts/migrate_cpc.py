#!/usr/bin/env python3
"""
Migration: CPC-Codes aus denormalisiertem Feld in Junction-Tabelle aufloesen.

Liest patents.cpc_codes (kommasepariert), normalisiert auf Level 4 (Subklasse,
z.B. "H01L33/00" -> "H01L"), extrahiert pub_year aus publication_date und
befuellt die neue Tabelle 'patent_cpc'. Nur Patente mit >= 2 distinkten
CPC-Codes auf Level 4 werden aufgenommen (Voraussetzung fuer Jaccard-Berechnung).

Idempotent: DROP + CREATE bei jedem Lauf.

Usage:
    python scripts/migrate_cpc.py
    python scripts/migrate_cpc.py --db data/patents.db
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


# ---------------------------------------------------------------------------
# CPC-Normalisierung (identisch zu domain/cpc_flow.py:normalize_cpc)
# ---------------------------------------------------------------------------

def normalize_cpc(code: str, level: int = 4) -> str:
    """CPC-Code auf ein bestimmtes Hierarchie-Level kuerzen.

    Level 4 = Subklasse (z.B. 'H01L'), Level 3 = Klasse (z.B. 'H01').
    """
    clean = code.strip().replace(" ", "")
    return clean[:level] if len(clean) >= level else clean


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DROP_SQL = """
DROP INDEX IF EXISTS idx_pc_cpc;
DROP INDEX IF EXISTS idx_pc_year;
DROP INDEX IF EXISTS idx_pc_cpc_year;
DROP TABLE IF EXISTS patent_cpc;
"""

CREATE_SQL = """
CREATE TABLE patent_cpc (
    patent_id  INTEGER NOT NULL,
    cpc_code   TEXT    NOT NULL,
    pub_year   INTEGER NOT NULL,
    PRIMARY KEY (patent_id, cpc_code)
) WITHOUT ROWID;

CREATE INDEX idx_pc_cpc      ON patent_cpc(cpc_code);
CREATE INDEX idx_pc_year     ON patent_cpc(pub_year);
CREATE INDEX idx_pc_cpc_year ON patent_cpc(cpc_code, pub_year);
"""


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def migrate(db_path: Path, batch_size: int = 50_000) -> None:
    """CPC-Migration ausfuehren (idempotent, batch-weise)."""
    logger.info("Starte CPC-Migration: %s", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64 MB Cache

    # Schema: bestehende Tabelle + Indizes entfernen, neu anlegen
    logger.info("Erstelle patent_cpc Tabelle (DROP + CREATE) ...")
    conn.executescript(DROP_SQL)
    conn.executescript(CREATE_SQL)
    conn.commit()

    # Gesamtzahl fuer Fortschrittsanzeige (schnell via Index)
    total_patents = conn.execute(
        "SELECT COUNT(*) FROM patents "
        "WHERE cpc_codes IS NOT NULL AND cpc_codes != '' "
        "AND publication_date IS NOT NULL AND publication_date != ''"
    ).fetchone()[0]
    logger.info("Patente mit CPC-Codes und Datum: %d", total_patents)

    total_processed = 0
    total_inserted = 0
    total_skipped = 0
    current_min_id = 0
    t0 = time.time()

    while True:
        rows = conn.execute(
            "SELECT id, cpc_codes, publication_date FROM patents "
            "WHERE id > ? "
            "AND cpc_codes IS NOT NULL AND cpc_codes != '' "
            "AND publication_date IS NOT NULL AND publication_date != '' "
            "ORDER BY id LIMIT ?",
            (current_min_id, batch_size),
        ).fetchall()

        if not rows:
            break

        current_min_id = rows[-1][0]
        batch_rows: list[tuple[int, str, int]] = []

        for patent_id, cpc_codes_str, publication_date in rows:
            # pub_year extrahieren (erste 4 Zeichen, z.B. "2023-01-15" -> 2023)
            try:
                pub_year = int(publication_date[:4])
            except (ValueError, IndexError):
                total_skipped += 1
                continue

            # CPC-Codes normalisieren auf Level 4, Duplikate entfernen
            codes = {
                normalize_cpc(c)
                for c in cpc_codes_str.split(",")
                if c.strip()
            }

            # Nur Patente mit >= 2 distinkten CPC-Codes (Jaccard braucht Paare)
            if len(codes) < 2:
                total_skipped += 1
                continue

            for code in codes:
                batch_rows.append((patent_id, code, pub_year))

        # Batch einfuegen
        if batch_rows:
            conn.executemany(
                "INSERT OR IGNORE INTO patent_cpc (patent_id, cpc_code, pub_year) "
                "VALUES (?, ?, ?)",
                batch_rows,
            )

        conn.commit()
        total_processed += len(rows)
        total_inserted += len(batch_rows)

        elapsed = time.time() - t0
        rate = total_processed / elapsed if elapsed > 0 else 0
        pct = total_processed / total_patents * 100 if total_patents > 0 else 0
        logger.info(
            "  %d / %d Patente (%.1f%%, %.0f/s) | %d Zeilen eingefuegt, %d uebersprungen",
            total_processed, total_patents, pct, rate, total_inserted, total_skipped,
        )

    elapsed = time.time() - t0

    # Finale Statistiken
    row_count = conn.execute("SELECT COUNT(*) FROM patent_cpc").fetchone()[0]
    distinct_codes = conn.execute(
        "SELECT COUNT(DISTINCT cpc_code) FROM patent_cpc"
    ).fetchone()[0]
    distinct_patents = conn.execute(
        "SELECT COUNT(DISTINCT patent_id) FROM patent_cpc"
    ).fetchone()[0]
    year_range = conn.execute(
        "SELECT MIN(pub_year), MAX(pub_year) FROM patent_cpc"
    ).fetchone()

    conn.close()

    # Tabellengroesse schaetzen (DB-Datei)
    db_size_mb = db_path.stat().st_size / (1024 * 1024)

    logger.info("Migration abgeschlossen in %.1fs", elapsed)
    logger.info("  Verarbeitete Patente:       %d", total_processed)
    logger.info("  Uebersprungen (< 2 CPC):    %d", total_skipped)
    logger.info("  Patente in patent_cpc:       %d", distinct_patents)
    logger.info("  Zeilen in patent_cpc:        %d", row_count)
    logger.info("  Distinkte CPC-Codes:         %d", distinct_codes)
    logger.info("  Jahresbereich:               %d - %d", year_range[0], year_range[1])
    logger.info("  Datenbank-Groesse:           %.1f MB", db_size_mb)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CPC-Codes aus patents in normalisierte patent_cpc Tabelle migrieren"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/patents.db"),
        help="Pfad zur patents.db (default: data/patents.db)",
    )

    args = parser.parse_args()

    if not args.db.exists():
        logger.error("Datenbank nicht gefunden: %s", args.db)
        raise SystemExit(1)

    migrate(args.db)
