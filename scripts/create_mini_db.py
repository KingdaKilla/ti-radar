"""Create a mini patent database with a few demo technologies.

Usage:
    python scripts/create_mini_db.py

Extracts patents matching demo queries from the full patents.db
into a smaller data/patents_mini.db (~50-150 MB).
"""

import sqlite3
import time
from pathlib import Path

SOURCE = Path("data/patents.db")
TARGET = Path("data/patents_mini.db")

DEMO_QUERIES = [
    "solar energy",
    "quantum computing",
    "electric vehicle",
    "CRISPR",
]


def main():
    if not SOURCE.exists():
        print(f"ERROR: {SOURCE} not found")
        return

    if TARGET.exists():
        TARGET.unlink()
        print(f"Removed existing {TARGET}")

    src = sqlite3.connect(str(SOURCE))
    dst = sqlite3.connect(str(TARGET))

    # Create schema in target
    dst.executescript("""
        CREATE TABLE patents (
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
        CREATE TABLE applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_name TEXT NOT NULL,
            normalized_name TEXT NOT NULL
        );
        CREATE TABLE patent_applicants (
            patent_id INTEGER NOT NULL REFERENCES patents(id),
            applicant_id INTEGER NOT NULL REFERENCES applicants(id),
            PRIMARY KEY (patent_id, applicant_id)
        );
    """)

    # Collect all matching patent IDs
    all_ids = set()
    src_cur = src.cursor()
    for q in DEMO_QUERIES:
        t0 = time.time()
        src_cur.execute(
            "SELECT rowid FROM patents_fts WHERE patents_fts MATCH ?", (q,)
        )
        ids = {row[0] for row in src_cur.fetchall()}
        all_ids |= ids
        print(f"  {q}: {len(ids):,} patents ({time.time()-t0:.1f}s)")

    print(f"\nTotal unique patents: {len(all_ids):,}")

    # Export patents in batches
    id_list = sorted(all_ids)
    BATCH = 10_000
    patent_count = 0
    t0 = time.time()

    for i in range(0, len(id_list), BATCH):
        batch = id_list[i : i + BATCH]
        placeholders = ",".join("?" * len(batch))
        src_cur.execute(
            f"SELECT * FROM patents WHERE id IN ({placeholders})", batch
        )
        rows = src_cur.fetchall()
        dst.executemany(
            "INSERT INTO patents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows
        )
        patent_count += len(rows)
        if (i // BATCH) % 5 == 0:
            print(f"  Patents: {patent_count:,} / {len(id_list):,}")

    dst.commit()
    print(f"  Patents done: {patent_count:,} ({time.time()-t0:.1f}s)")

    # Export applicants that are referenced
    print("\nExporting applicants...")
    t0 = time.time()
    for i in range(0, len(id_list), BATCH):
        batch = id_list[i : i + BATCH]
        placeholders = ",".join("?" * len(batch))
        src_cur.execute(
            f"SELECT * FROM patent_applicants WHERE patent_id IN ({placeholders})",
            batch,
        )
        rows = src_cur.fetchall()
        if rows:
            dst.executemany(
                "INSERT OR IGNORE INTO patent_applicants VALUES (?,?)", rows
            )

    dst.commit()

    # Get unique applicant IDs
    dst_cur = dst.cursor()
    dst_cur.execute("SELECT DISTINCT applicant_id FROM patent_applicants")
    app_ids = [row[0] for row in dst_cur.fetchall()]
    print(f"  Unique applicants referenced: {len(app_ids):,}")

    for i in range(0, len(app_ids), BATCH):
        batch = app_ids[i : i + BATCH]
        placeholders = ",".join("?" * len(batch))
        src_cur.execute(
            f"SELECT * FROM applicants WHERE id IN ({placeholders})", batch
        )
        rows = src_cur.fetchall()
        dst.executemany("INSERT OR IGNORE INTO applicants VALUES (?,?,?)", rows)

    dst.commit()
    print(f"  Applicants done ({time.time()-t0:.1f}s)")

    # Build FTS5 index
    print("\nBuilding FTS5 index...")
    t0 = time.time()
    dst.executescript("""
        CREATE VIRTUAL TABLE patents_fts USING fts5(
            title, cpc_codes,
            content='patents',
            content_rowid='id'
        );
        INSERT INTO patents_fts(patents_fts) VALUES('rebuild');
    """)
    print(f"  FTS5 done ({time.time()-t0:.1f}s)")

    # Create indexes
    print("Creating indexes...")
    dst.executescript("""
        CREATE INDEX IF NOT EXISTS idx_patents_pub_date ON patents(publication_date);
        CREATE INDEX IF NOT EXISTS idx_patents_country ON patents(country);
        CREATE INDEX IF NOT EXISTS idx_patents_family ON patents(family_id);
        CREATE INDEX IF NOT EXISTS idx_patent_applicants_app ON patent_applicants(applicant_id);
        CREATE INDEX IF NOT EXISTS idx_applicants_normalized ON applicants(normalized_name);
    """)

    # Vacuum
    print("Compacting (VACUUM)...")
    dst.execute("VACUUM")

    src.close()
    dst.close()

    size_mb = TARGET.stat().st_size / (1024 * 1024)
    print(f"\nDone! {TARGET}: {size_mb:.0f} MB")
    print(f"Demo queries: {', '.join(DEMO_QUERIES)}")


if __name__ == "__main__":
    main()
