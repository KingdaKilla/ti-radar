"""CPC-Technologiefluss: Co-Klassifikations-Analyse via Jaccard-Index."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any


def normalize_cpc(code: str, level: int = 4) -> str:
    """CPC-Code auf ein bestimmtes Hierarchie-Level kuerzen.

    Level 4 = Subklasse (z.B. 'H01L'), Level 3 = Klasse (z.B. 'H01').
    """
    clean = code.strip().replace(" ", "")
    return clean[:level] if len(clean) >= level else clean


def extract_cpc_sets(
    cpc_strings: list[str], level: int = 4
) -> list[set[str]]:
    """Aus kommaseparierten CPC-Strings pro Patent eine Menge normalisierter Codes erzeugen."""
    result: list[set[str]] = []
    for raw in cpc_strings:
        if not raw:
            continue
        codes = {normalize_cpc(c, level) for c in raw.split(",") if c.strip()}
        if len(codes) >= 2:
            result.append(codes)
    return result


def extract_cpc_sets_with_years(
    patent_rows: list[dict[str, str | int]], level: int = 4
) -> list[tuple[set[str], int]]:
    """CPC-Sets + Jahr aus patent_rows extrahieren."""
    result: list[tuple[set[str], int]] = []
    for row in patent_rows:
        raw = str(row.get("cpc_codes", ""))
        year = int(row.get("year", 0))
        if not raw or year == 0:
            continue
        codes = {normalize_cpc(c, level) for c in raw.split(",") if c.strip()}
        if len(codes) >= 2:
            result.append((codes, year))
    return result


def build_cooccurrence(
    patent_sets: list[set[str]], top_n: int = 15
) -> tuple[list[str], list[list[float]], int]:
    """Co-Occurrence-Matrix und Jaccard-Normalisierung berechnen.

    Returns:
        (labels, jaccard_matrix, total_connections)
    """
    # Haeufigste CPC-Codes ermitteln
    code_counter: Counter[str] = Counter()
    for codes in patent_sets:
        for code in codes:
            code_counter[code] += 1

    top_codes = [code for code, _ in code_counter.most_common(top_n)]
    if len(top_codes) < 2:
        return top_codes, [], 0

    n = len(top_codes)
    code_index = {code: i for i, code in enumerate(top_codes)}

    # Co-Occurrence zaehlen
    pair_counts: Counter[tuple[int, int]] = Counter()
    code_patent_sets: dict[int, set[int]] = {i: set() for i in range(n)}

    for patent_id, codes in enumerate(patent_sets):
        relevant = [code_index[c] for c in codes if c in code_index]
        for idx in relevant:
            code_patent_sets[idx].add(patent_id)
        for a, b in combinations(sorted(relevant), 2):
            pair_counts[(a, b)] += 1

    # Jaccard-Matrix berechnen
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    total_connections = 0

    for (a, b), count in pair_counts.items():
        if count < 1:
            continue
        union_size = len(code_patent_sets[a] | code_patent_sets[b])
        jaccard = count / union_size if union_size > 0 else 0.0
        matrix[a][b] = round(jaccard, 4)
        matrix[b][a] = round(jaccard, 4)
        total_connections += 1

    return top_codes, matrix, total_connections


def build_cooccurrence_with_years(
    patent_data: list[tuple[set[str], int]], top_n: int = 15
) -> tuple[list[str], list[list[float]], int, dict[str, Any]]:
    """Co-Occurrence mit Jahr-Tracking fuer Frontend-seitige Neuberechnung.

    Returns:
        (labels, jaccard_matrix, total_connections, year_data)
    """
    # Alle CPC-Sets (ohne Jahr) fuer Gesamt-Matrix
    patent_sets = [codes for codes, _ in patent_data]

    # Haeufigste CPC-Codes ermitteln
    code_counter: Counter[str] = Counter()
    for codes in patent_sets:
        for code in codes:
            code_counter[code] += 1

    # Alle CPC-Codes sortiert nach Haeufigkeit (fuer year_data)
    all_codes = [code for code, _ in code_counter.most_common()]
    top_codes = all_codes[:top_n]
    if len(top_codes) < 2:
        return top_codes, [], 0, {}

    n = len(top_codes)
    code_index = {code: i for i, code in enumerate(top_codes)}

    # Co-Occurrence zaehlen (Gesamt + pro Jahr)
    pair_counts: Counter[tuple[int, int]] = Counter()
    code_patent_sets: dict[int, set[int]] = {i: set() for i in range(n)}

    # Year-level tracking (alle Codes, nicht nur top_n)
    all_code_set = set(all_codes)
    pair_counts_by_year: dict[int, dict[str, int]] = {}
    cpc_counts_by_year: dict[int, dict[str, int]] = {}
    years_seen: set[int] = set()

    for patent_id, (codes, year) in enumerate(patent_data):
        years_seen.add(year)

        # Year-level CPC counts (alle Codes)
        if year not in cpc_counts_by_year:
            cpc_counts_by_year[year] = {}
        for code in codes:
            if code in all_code_set:
                cpc_counts_by_year[year][code] = cpc_counts_by_year[year].get(code, 0) + 1

        # Year-level pair counts (alle Codes)
        if year not in pair_counts_by_year:
            pair_counts_by_year[year] = {}
        relevant_all = sorted(c for c in codes if c in all_code_set)
        for ca, cb in combinations(relevant_all, 2):
            key = f"{ca}|{cb}"
            pair_counts_by_year[year][key] = pair_counts_by_year[year].get(key, 0) + 1

        # Gesamt-Matrix (nur top_n)
        relevant = [code_index[c] for c in codes if c in code_index]
        for idx in relevant:
            code_patent_sets[idx].add(patent_id)
        for ia, ib in combinations(sorted(relevant), 2):
            pair_counts[(ia, ib)] += 1

    # Jaccard-Matrix berechnen (Gesamt)
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    total_connections = 0

    for (ia, ib), count in pair_counts.items():
        if count < 1:
            continue
        union_size = len(code_patent_sets[ia] | code_patent_sets[ib])
        jaccard = count / union_size if union_size > 0 else 0.0
        matrix[ia][ib] = round(jaccard, 4)
        matrix[ib][ia] = round(jaccard, 4)
        total_connections += 1

    sorted_years = sorted(years_seen)
    year_data: dict[str, Any] = {
        "min_year": sorted_years[0] if sorted_years else 0,
        "max_year": sorted_years[-1] if sorted_years else 0,
        "all_labels": all_codes,
        "pair_counts": {
            str(y): pair_counts_by_year.get(y, {}) for y in sorted_years
        },
        "cpc_counts": {
            str(y): cpc_counts_by_year.get(y, {}) for y in sorted_years
        },
    }

    return top_codes, matrix, total_connections, year_data


# Farben fuer CPC-Sektionen (A-H + Y)
CPC_COLORS: dict[str, str] = {
    "A": "#ef4444",  # rot
    "B": "#f97316",  # orange
    "C": "#eab308",  # gelb
    "D": "#22c55e",  # gruen
    "E": "#06b6d4",  # cyan
    "F": "#3b82f6",  # blau
    "G": "#8b5cf6",  # violett
    "H": "#ec4899",  # pink
    "Y": "#6b7280",  # grau
}


def assign_colors(labels: list[str]) -> list[str]:
    """Farben basierend auf CPC-Sektion (erster Buchstabe) zuweisen."""
    return [CPC_COLORS.get(label[0], "#9ca3af") if label else "#9ca3af" for label in labels]
