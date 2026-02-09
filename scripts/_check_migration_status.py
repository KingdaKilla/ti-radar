"""Temporary script to check migration status."""
import sqlite3, os

db_path = "data/patents.db"
if not os.path.exists(db_path):
    print("patents.db existiert NICHT")
    raise SystemExit(0)

conn = sqlite3.connect(db_path)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Vorhandene Tabellen:", [t[0] for t in tables])

has_applicants = any(t[0] == "applicants" for t in tables)
has_pa = any(t[0] == "patent_applicants" for t in tables)

print(f"applicants Tabelle: {'EXISTS' if has_applicants else 'FEHLT'}")
print(f"patent_applicants Tabelle: {'EXISTS' if has_pa else 'FEHLT'}")

if has_applicants:
    count = conn.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]
    print(f"applicants Eintraege: {count}")

if has_pa:
    count = conn.execute("SELECT COUNT(*) FROM patent_applicants").fetchone()[0]
    print(f"patent_applicants Eintraege: {count}")

total = conn.execute("SELECT COUNT(*) FROM patents").fetchone()[0]
print(f"Gesamt Patente: {total}")

with_names = conn.execute("SELECT COUNT(*) FROM patents WHERE applicant_names IS NOT NULL AND applicant_names != ''").fetchone()[0]
print(f"Patente mit applicant_names: {with_names}")

if has_pa:
    not_migrated = conn.execute(
        "SELECT COUNT(*) FROM patents p "
        "WHERE p.applicant_names IS NOT NULL AND p.applicant_names != '' "
        "AND NOT EXISTS (SELECT 1 FROM patent_applicants pa WHERE pa.patent_id = p.id)"
    ).fetchone()[0]
    print(f"Noch NICHT migriert: {not_migrated}")

conn.close()
