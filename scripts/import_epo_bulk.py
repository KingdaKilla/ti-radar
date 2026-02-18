#!/usr/bin/env python3
"""
EPO DOCDB Bulk Data Import Script.

Imports patent data from EPO DOCDB XML bulk downloads (150 ZIPs, ~187 GB)
into a local SQLite database. Handles nested ZIP-in-ZIP structure:

    Outer ZIP -> Root/DOC/*.zip (inner ZIPs per country) -> XML

Usage:
    python scripts/import_epo_bulk.py \
        --source "../../04_Daten/Bulk-Downloads/EPO" \
        --output "data/patents.db"

    # Resume after interruption (skips already-processed ZIPs):
    python scripts/import_epo_bulk.py \
        --source "../../04_Daten/Bulk-Downloads/EPO" \
        --output "data/patents.db"

    # Process only specific outer ZIPs:
    python scripts/import_epo_bulk.py \
        --source "../../04_Daten/Bulk-Downloads/EPO" \
        --output "data/patents.db" \
        --filter "001"
"""

from __future__ import annotations

import argparse
import io
import logging
import re
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# EPO DOCDB XML namespace
NS = {"exch": "http://www.epo.org/exchange"}

# Firmenrechtliche Suffixe fuer Normalisierung (laengste zuerst)
_CORPORATE_SUFFIXES = sorted(
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
    for suffix in _CORPORATE_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].rstrip()
            break
    return " ".join(name.split())


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
    duration_seconds REAL
);

-- Patente (denormalisiert: CPC-Codes und Applicants kommasepariert)
CREATE TABLE IF NOT EXISTS patents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_number TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    doc_number TEXT NOT NULL,
    kind TEXT,
    title TEXT,
    publication_date TEXT,
    family_id TEXT,
    applicant_names TEXT,
    applicant_countries TEXT,
    cpc_codes TEXT,
    ipc_codes TEXT
);

-- Indizes fuer schnelle Suche
CREATE INDEX IF NOT EXISTS idx_patents_country ON patents(country);
CREATE INDEX IF NOT EXISTS idx_patents_date ON patents(publication_date);
CREATE INDEX IF NOT EXISTS idx_patents_family ON patents(family_id);

-- Normalisierte Applicant-Tabellen
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

-- Normalisierte CPC-Codes (Level 4) fuer SQL-native Jaccard-Berechnung
CREATE TABLE IF NOT EXISTS patent_cpc (
    patent_id  INTEGER NOT NULL,
    cpc_code   TEXT    NOT NULL,
    pub_year   INTEGER NOT NULL,
    PRIMARY KEY (patent_id, cpc_code)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_pc_cpc      ON patent_cpc(cpc_code);
CREATE INDEX IF NOT EXISTS idx_pc_year     ON patent_cpc(pub_year);
CREATE INDEX IF NOT EXISTS idx_pc_cpc_year ON patent_cpc(cpc_code, pub_year);
"""

FTS_SCHEMA_SQL = """
-- Volltextsuche fuer Titel und CPC-Codes
CREATE VIRTUAL TABLE IF NOT EXISTS patents_fts USING fts5(
    title,
    cpc_codes,
    content='patents',
    content_rowid='id'
);

-- Trigger fuer automatische FTS-Updates
CREATE TRIGGER IF NOT EXISTS patents_ai AFTER INSERT ON patents BEGIN
    INSERT INTO patents_fts(rowid, title, cpc_codes)
    VALUES (new.id, new.title, new.cpc_codes);
END;

CREATE TRIGGER IF NOT EXISTS patents_ad AFTER DELETE ON patents BEGIN
    INSERT INTO patents_fts(patents_fts, rowid, title, cpc_codes)
    VALUES ('delete', old.id, old.title, old.cpc_codes);
END;

CREATE TRIGGER IF NOT EXISTS patents_au AFTER UPDATE ON patents BEGIN
    INSERT INTO patents_fts(patents_fts, rowid, title, cpc_codes)
    VALUES ('delete', old.id, old.title, old.cpc_codes);
    INSERT INTO patents_fts(rowid, title, cpc_codes)
    VALUES (new.id, new.title, new.cpc_codes);
END;
"""


# ---------------------------------------------------------------------------
# XML Parsing Helpers
# ---------------------------------------------------------------------------

def extract_patent(doc: ET.Element) -> dict[str, str] | None:
    """Extract basic fields from a single <exch:exchange-document> element."""
    country = doc.get("country", "")
    doc_number = doc.get("doc-number", "")
    kind = doc.get("kind", "")
    date_publ = doc.get("date-publ", "")
    family_id = doc.get("family-id", "")

    if not country or not doc_number:
        return None

    pub_number = f"{country}{doc_number}{kind}"

    biblio = doc.find("exch:bibliographic-data", NS)
    if biblio is None:
        return None

    # Title (prefer English, fallback to first available)
    title = ""
    titles = biblio.findall("exch:invention-title", NS)
    for t in titles:
        if t.get("lang") == "en":
            title = (t.text or "").strip()
            break
    if not title and titles:
        title = (titles[0].text or "").strip()

    # CPC classifications
    cpc_list: list[str] = []
    pat_class = biblio.find("exch:patent-classifications", NS)
    if pat_class is not None:
        for pc in pat_class.findall("patent-classification"):
            symbol = pc.find("classification-symbol")
            if symbol is not None and symbol.text:
                code = symbol.text.strip()
                if code and code not in cpc_list:
                    cpc_list.append(code)

    # IPC classifications (IPCR format)
    ipc_list: list[str] = []
    ipcr_block = biblio.find("exch:classifications-ipcr", NS)
    if ipcr_block is not None:
        for ipcr in ipcr_block.findall("classification-ipcr"):
            text_elem = ipcr.find("text")
            if text_elem is not None and text_elem.text:
                # Fixed-width: first ~15 chars are the IPC symbol
                ipc_code = text_elem.text[:15].strip()
                if ipc_code and ipc_code not in ipc_list:
                    ipc_list.append(ipc_code)

    # Applicants (docdb format only, has country info)
    applicant_names: list[str] = []
    applicant_countries: list[str] = []
    parties = biblio.find("exch:parties", NS)
    if parties is not None:
        applicants = parties.find("exch:applicants", NS)
        if applicants is not None:
            for app in applicants.findall("exch:applicant", NS):
                if app.get("data-format") != "docdb":
                    continue
                name_elem = app.find("exch:applicant-name/name", NS)
                if name_elem is not None and name_elem.text:
                    name = name_elem.text.strip()
                    if name and name not in applicant_names:
                        applicant_names.append(name)
                res_country = app.find("residence/country")
                if res_country is not None and res_country.text:
                    c = res_country.text.strip()
                    if c:
                        applicant_countries.append(c)

    # Format publication_date from YYYYMMDD to YYYY-MM-DD
    pub_date = ""
    if len(date_publ) == 8:
        pub_date = f"{date_publ[:4]}-{date_publ[4:6]}-{date_publ[6:8]}"
    elif date_publ:
        pub_date = date_publ

    return {
        "publication_number": pub_number,
        "country": country,
        "doc_number": doc_number,
        "kind": kind,
        "title": title,
        "publication_date": pub_date,
        "family_id": family_id,
        "applicant_names": ", ".join(applicant_names),
        "applicant_countries": ", ".join(applicant_countries),
        "cpc_codes": ", ".join(cpc_list),
        "ipc_codes": ", ".join(ipc_list),
    }


# Regex to match HTML/named entities not valid in XML (keep &amp; &lt; &gt; &apos; &quot;)
_ENTITY_RE = re.compile(rb"&(?!amp;|lt;|gt;|apos;|quot;|#)([a-zA-Z][a-zA-Z0-9]*);")


def _sanitize_xml(xml_bytes: bytes) -> bytes:
    """Replace undefined HTML entities with empty string so XML parser succeeds."""
    return _ENTITY_RE.sub(b"", xml_bytes)


def parse_xml_stream(xml_bytes: bytes) -> list[dict[str, str]]:
    """Parse XML bytes and extract all patent documents using iterparse."""
    patents: list[dict[str, str]] = []
    tag = f"{{{NS['exch']}}}exchange-document"

    xml_bytes = _sanitize_xml(xml_bytes)
    context = ET.iterparse(io.BytesIO(xml_bytes), events=("end",))
    for event, elem in context:
        if elem.tag == tag:
            patent = extract_patent(elem)
            if patent:
                patents.append(patent)
            elem.clear()

    return patents


# ---------------------------------------------------------------------------
# ZIP Processing
# ---------------------------------------------------------------------------

def get_processed_zips(conn: sqlite3.Connection) -> set[str]:
    """Get set of already-processed outer ZIP filenames for resume support."""
    cursor = conn.execute("SELECT DISTINCT file_name FROM import_metadata")
    return {row[0] for row in cursor.fetchall()}


def process_inner_zip(inner_zip_bytes: bytes) -> list[dict[str, str]]:
    """Process a single inner ZIP (contains one XML file)."""
    with zipfile.ZipFile(io.BytesIO(inner_zip_bytes)) as inner_zf:
        xml_files = [f for f in inner_zf.namelist() if f.endswith(".xml")]
        if not xml_files:
            return []
        xml_bytes = inner_zf.read(xml_files[0])
        return parse_xml_stream(xml_bytes)


def _insert_applicants(
    cursor: sqlite3.Cursor,
    patent_id: int,
    applicant_names_str: str,
    applicant_cache: dict[str, int],
) -> None:
    """Einzelne Applicants in normalisierte Tabellen einfuegen."""
    if not applicant_names_str:
        return
    for raw_name in applicant_names_str.split(", "):
        raw_name = raw_name.strip()
        if not raw_name:
            continue
        if raw_name not in applicant_cache:
            normalized = normalize_applicant_name(raw_name)
            cursor.execute(
                "INSERT OR IGNORE INTO applicants (raw_name, normalized_name) VALUES (?, ?)",
                (raw_name, normalized),
            )
            row = cursor.execute(
                "SELECT id FROM applicants WHERE raw_name = ?", (raw_name,)
            ).fetchone()
            applicant_cache[raw_name] = row[0]
        cursor.execute(
            "INSERT OR IGNORE INTO patent_applicants (patent_id, applicant_id) VALUES (?, ?)",
            (patent_id, applicant_cache[raw_name]),
        )


def _normalize_cpc(code: str, level: int = 4) -> str:
    """CPC-Code auf Hierarchie-Level kuerzen (identisch zu domain/cpc_flow.py)."""
    clean = code.strip().replace(" ", "")
    return clean[:level] if len(clean) >= level else clean


def _insert_cpc_codes(
    cursor: sqlite3.Cursor,
    patent_id: int,
    cpc_codes_str: str,
    pub_date: str,
) -> None:
    """CPC-Codes normalisiert in patent_cpc Tabelle einfuegen."""
    if not cpc_codes_str or not pub_date or len(pub_date) < 4:
        return
    try:
        pub_year = int(pub_date[:4])
    except ValueError:
        return
    codes = {
        _normalize_cpc(c)
        for c in cpc_codes_str.split(",")
        if c.strip()
    }
    # Nur Patente mit >= 2 distinkten CPC-Codes (Jaccard braucht Paare)
    if len(codes) < 2:
        return
    for code in codes:
        cursor.execute(
            "INSERT OR IGNORE INTO patent_cpc (patent_id, cpc_code, pub_year) "
            "VALUES (?, ?, ?)",
            (patent_id, code, pub_year),
        )


def process_outer_zip(
    conn: sqlite3.Connection,
    zip_path: Path,
    batch_size: int = 10_000,
    applicant_cache: dict[str, int] | None = None,
) -> int:
    """Process one outer ZIP file with all its inner ZIPs."""
    total = 0
    cursor = conn.cursor()
    start_time = time.time()
    if applicant_cache is None:
        applicant_cache = {}

    logger.info(f"Opening {zip_path.name} ({zip_path.stat().st_size / 1_073_741_824:.1f} GB)...")

    with zipfile.ZipFile(zip_path, "r") as outer_zf:
        inner_zips = sorted([
            f for f in outer_zf.namelist()
            if f.startswith("Root/DOC/") and f.endswith(".zip")
        ])
        logger.info(f"  Found {len(inner_zips)} inner ZIPs")

        for i, inner_name in enumerate(inner_zips, 1):
            try:
                inner_bytes = outer_zf.read(inner_name)
                patents = process_inner_zip(inner_bytes)

                for p in patents:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO patents (
                            publication_number, country, doc_number, kind,
                            title, publication_date, family_id,
                            applicant_names, applicant_countries,
                            cpc_codes, ipc_codes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            p["publication_number"],
                            p["country"],
                            p["doc_number"],
                            p["kind"],
                            p["title"],
                            p["publication_date"],
                            p["family_id"],
                            p["applicant_names"],
                            p["applicant_countries"],
                            p["cpc_codes"],
                            p["ipc_codes"],
                        ),
                    )

                    # Normalisierte Tabellen befuellen
                    patent_id = cursor.lastrowid
                    if patent_id:  # nur bei tatsaechlichem INSERT (nicht IGNORE)
                        _insert_applicants(
                            cursor, patent_id, p["applicant_names"], applicant_cache,
                        )
                        _insert_cpc_codes(
                            cursor, patent_id, p["cpc_codes"], p["publication_date"],
                        )

                total += len(patents)

                if total % batch_size < len(patents):
                    conn.commit()
                    elapsed = time.time() - start_time
                    rate = total / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"  [{i}/{len(inner_zips)}] {total:,} patents "
                        f"({rate:,.0f}/s) - {inner_name.split('/')[-1]}"
                    )

            except Exception as e:
                logger.warning(f"  Error processing {inner_name}: {e}")

    conn.commit()
    duration = time.time() - start_time

    # Record metadata
    cursor.execute(
        """
        INSERT INTO import_metadata (source, file_name, import_date, record_count, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("EPO-DOCDB", zip_path.name, datetime.now().isoformat(), total, round(duration, 1)),
    )
    conn.commit()

    logger.info(f"  Done: {total:,} patents in {duration:.0f}s")
    return total


# ---------------------------------------------------------------------------
# FTS Index
# ---------------------------------------------------------------------------

def rebuild_fts_index(conn: sqlite3.Connection) -> None:
    """Rebuild the FTS index from existing patents."""
    logger.info("Rebuilding FTS index...")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS patents_fts")
    cursor.execute("DROP TRIGGER IF EXISTS patents_ai")
    cursor.execute("DROP TRIGGER IF EXISTS patents_ad")
    cursor.execute("DROP TRIGGER IF EXISTS patents_au")

    cursor.execute("""
        CREATE VIRTUAL TABLE patents_fts USING fts5(
            title, cpc_codes,
            content='patents',
            content_rowid='id'
        )
    """)

    cursor.execute("""
        INSERT INTO patents_fts(rowid, title, cpc_codes)
        SELECT id, title, cpc_codes FROM patents
    """)

    cursor.executescript("""
        CREATE TRIGGER patents_ai AFTER INSERT ON patents BEGIN
            INSERT INTO patents_fts(rowid, title, cpc_codes)
            VALUES (new.id, new.title, new.cpc_codes);
        END;

        CREATE TRIGGER patents_ad AFTER DELETE ON patents BEGIN
            INSERT INTO patents_fts(patents_fts, rowid, title, cpc_codes)
            VALUES ('delete', old.id, old.title, old.cpc_codes);
        END;

        CREATE TRIGGER patents_au AFTER UPDATE ON patents BEGIN
            INSERT INTO patents_fts(patents_fts, rowid, title, cpc_codes)
            VALUES ('delete', old.id, old.title, old.cpc_codes);
            INSERT INTO patents_fts(rowid, title, cpc_codes)
            VALUES (new.id, new.title, new.cpc_codes);
        END;
    """)

    conn.commit()
    logger.info("FTS index rebuilt")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(source_dir: Path, output_db: Path, zip_filter: str | None = None) -> None:
    """Main import function."""
    logger.info("Starting EPO DOCDB bulk import")
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

    # Find outer ZIPs
    outer_zips = sorted(source_dir.glob("docdb_xml_bck_*.zip"))
    if not outer_zips:
        logger.error(f"No DOCDB ZIP files found in {source_dir}")
        sys.exit(1)

    if zip_filter:
        outer_zips = [z for z in outer_zips if zip_filter in z.name]
        logger.info(f"Filtered to {len(outer_zips)} ZIPs matching '{zip_filter}'")

    # Resume support: skip already-processed ZIPs
    processed = get_processed_zips(conn)
    remaining = [z for z in outer_zips if z.name not in processed]

    if len(remaining) < len(outer_zips):
        logger.info(
            f"Resuming: {len(outer_zips) - len(remaining)} ZIPs already processed, "
            f"{len(remaining)} remaining"
        )

    if not remaining:
        logger.info("All ZIPs already processed. Nothing to do.")
        conn.close()
        return

    logger.info(f"Processing {len(remaining)} outer ZIP files...")

    grand_total = 0
    import_start = time.time()

    for i, zip_path in enumerate(remaining, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"[{i}/{len(remaining)}] {zip_path.name}")
        count = process_outer_zip(conn, zip_path)
        grand_total += count

    # Rebuild FTS index
    rebuild_fts_index(conn)

    # Final statistics
    total_in_db = conn.execute("SELECT COUNT(*) FROM patents").fetchone()[0]
    total_duration = time.time() - import_start

    logger.info(f"\n{'=' * 60}")
    logger.info("Import complete!")
    logger.info(f"  New patents imported:  {grand_total:,}")
    logger.info(f"  Total patents in DB:   {total_in_db:,}")
    logger.info(f"  Duration:              {total_duration / 60:.1f} min")

    conn.close()
    db_size_mb = output_db.stat().st_size / (1024 * 1024)
    logger.info(f"  Database size:         {db_size_mb:.1f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import EPO DOCDB bulk data into SQLite")
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to directory containing DOCDB ZIP files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/patents.db"),
        help="Output SQLite database path (default: data/patents.db)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Only process ZIPs containing this string (e.g. '001' for first ZIP)",
    )

    args = parser.parse_args()

    if not args.source.exists():
        logger.error(f"Source directory does not exist: {args.source}")
        sys.exit(1)

    main(args.source, args.output, args.filter)
