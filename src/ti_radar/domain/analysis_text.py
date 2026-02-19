"""Reine Funktionen fuer deterministische Analyse-Textgenerierung (UC1-UC8).

Alle Funktionen sind zustandslos und ohne I/O — testbar und auditierbar.
Template-basierte deutsche Texte, kein LLM erforderlich.
"""

from __future__ import annotations

from ti_radar.domain.models import (
    CompetitivePanel,
    CpcFlowPanel,
    FundingPanel,
    GeographicPanel,
    LandscapePanel,
    MaturityPanel,
    ResearchImpactPanel,
    TemporalPanel,
)


# ---------------------------------------------------------------------------
# Hilfsfunktionen (Formatierung)
# ---------------------------------------------------------------------------


def _fmt_int(value: int) -> str:
    """Integer mit deutschem Tausender-Punkt (1.234)."""
    return f"{value:,}".replace(",", ".")


def _fmt_pct(value: float, decimals: int = 1) -> str:
    """Prozent mit Komma (67,3%)."""
    return f"{value:.{decimals}f}".replace(".", ",") + "%"


def _fmt_eur(value: float) -> str:
    """Euro-Formatierung (1,2 Mrd. EUR / 345,6 Mio. EUR)."""
    if value >= 1e9:
        num = f"{value / 1e9:.1f}".replace(".", ",")
        return f"{num} Mrd. EUR"
    if value >= 1e6:
        num = f"{value / 1e6:.1f}".replace(".", ",")
        return f"{num} Mio. EUR"
    if value >= 1e3:
        num = f"{value / 1e3:.0f}"
        return f"{num} Tsd. EUR"
    return f"{value:.0f} EUR"


def _trend_word(cagr_value: float) -> str:
    """CAGR als qualitative Bewertung."""
    if cagr_value > 15:
        return "sehr starkes Wachstum"
    if cagr_value > 5:
        return "solides Wachstum"
    if cagr_value > 0:
        return "leichtes Wachstum"
    if cagr_value > -5:
        return "Stagnation"
    return "einen Rueckgang"


# ---------------------------------------------------------------------------
# UC1: Technology Landscape
# ---------------------------------------------------------------------------


def generate_landscape_text(panel: LandscapePanel) -> str:
    """Analysetext fuer UC1 — Technologie-Landschaft."""
    total = panel.total_patents + panel.total_projects + panel.total_publications
    if total == 0:
        return ""

    parts: list[str] = []

    # Satz 1: Gesamtaktivitaeten
    parts.append(
        f"Insgesamt wurden {_fmt_int(total)} Aktivitaeten identifiziert "
        f"({_fmt_int(panel.total_patents)} Patente, "
        f"{_fmt_int(panel.total_projects)} Projekte, "
        f"{_fmt_int(panel.total_publications)} Publikationen)."
    )

    # Satz 2: Dominante Quelle
    source_map = {
        "Patente": panel.total_patents,
        "Projekte": panel.total_projects,
        "Publikationen": panel.total_publications,
    }
    dominant_source = max(source_map, key=lambda k: source_map[k])
    dominant_share = source_map[dominant_source] / total * 100 if total > 0 else 0
    parts.append(
        f"Die dominante Quelle sind {dominant_source} "
        f"mit einem Anteil von {_fmt_pct(dominant_share)}."
    )

    # Satz 3: Top-Land
    if panel.top_countries:
        top = panel.top_countries[0]
        country_name = str(top.get("country", ""))
        country_total = int(top.get("total", 0))
        if country_name:
            parts.append(
                f"Das fuehrende Land ist {country_name} "
                f"mit {_fmt_int(country_total)} Aktivitaeten."
            )

    # Satz 4: Patent-Wachstumsrate (letzter Eintrag der Zeitreihe)
    if panel.time_series:
        last_entry = panel.time_series[-1]
        patents_growth = last_entry.get("patents_growth")
        if patents_growth is not None and patents_growth != 0:
            parts.append(
                f"Die Patentwachstumsrate im letzten erfassten Jahr betraegt "
                f"{_fmt_pct(float(patents_growth))}."
            )

    # Satz 5: Projekt-Wachstumsrate
    if panel.time_series:
        last_entry = panel.time_series[-1]
        projects_growth = last_entry.get("projects_growth")
        if projects_growth is not None and projects_growth != 0:
            parts.append(
                f"Die Projektwachstumsrate im letzten erfassten Jahr liegt bei "
                f"{_fmt_pct(float(projects_growth))}."
            )

    # Satz 6: Aktive Laender
    if panel.top_countries:
        parts.append(
            f"Es sind {_fmt_int(len(panel.top_countries))} Laender aktiv."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC2: Technology Maturity Assessment
# ---------------------------------------------------------------------------


def generate_maturity_text(panel: MaturityPanel) -> str:
    """Analysetext fuer UC2 — Reifegrad-Analyse (Gao et al. 2013)."""
    if not panel.phase:
        return ""

    parts: list[str] = []

    # Satz 1: Phase + Reifegrad-Prozent
    phase_label = panel.phase_de if panel.phase_de else panel.phase
    parts.append(
        f"Die Technologie befindet sich in der Phase \"{phase_label}\" "
        f"mit einem Reifegrad von {_fmt_pct(panel.maturity_percent)} "
        f"(Schwellenwerte nach Gao et al. 2013)."
    )

    # Satz 2: R²-Qualitaet + Modell
    if panel.r_squared > 0:
        if panel.r_squared >= 0.9:
            quality = "exzellente"
        elif panel.r_squared >= 0.7:
            quality = "gute"
        elif panel.r_squared >= 0.5:
            quality = "akzeptable"
        else:
            quality = "schwache"
        model_info = f" ({panel.fit_model})" if panel.fit_model else ""
        parts.append(
            f"Der S-Curve-Fit{model_info} zeigt eine {quality} "
            f"Anpassungsguete (R\u00b2 = {panel.r_squared:.3f})."
        )

    # Satz 3: CAGR + Trend
    if panel.cagr != 0:
        parts.append(
            f"Die jaehrliche Wachstumsrate (CAGR) betraegt {_fmt_pct(panel.cagr)} "
            f"und zeigt damit {_trend_word(panel.cagr)}."
        )

    # Satz 4: Wendepunkt
    if panel.inflection_year > 0:
        parts.append(
            f"Der Wendepunkt der S-Curve liegt bei {panel.inflection_year:.0f}."
        )

    # Satz 5: Konfidenz + Datenbasis
    if panel.confidence > 0:
        n_years = len(panel.time_series)
        total_patents = sum(
            int(ts.get("patents", 0)) for ts in panel.time_series
        )
        parts.append(
            f"Die Konfidenz der Analyse betraegt {_fmt_pct(panel.confidence * 100, 0)}, "
            f"basierend auf {n_years} Jahren und {_fmt_int(total_patents)} Patenten."
        )

    # Satz 6: Verbleibendes Potenzial
    if panel.maturity_percent >= 90:
        parts.append(
            "Die Saettigungsphase ist erreicht — das Wachstumspotenzial "
            "ist weitgehend ausgeschoepft."
        )
    elif panel.maturity_percent > 0:
        remaining = 90.0 - panel.maturity_percent
        parts.append(
            f"Bis zur Saettigungsgrenze (90%) verbleiben noch "
            f"{_fmt_pct(remaining)} Wachstumspotenzial."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC3: Competitive Intelligence
# ---------------------------------------------------------------------------


def generate_competitive_text(panel: CompetitivePanel) -> str:
    """Analysetext fuer UC3 — Wettbewerbs-Analyse (Garcia-Vega 2006)."""
    if not panel.top_actors:
        return ""

    parts: list[str] = []

    # Satz 1: HHI + Konzentration
    if panel.hhi_index > 0:
        level_map = {"Low": "gering", "Moderate": "moderat", "High": "hoch"}
        level_de = level_map.get(panel.concentration_level, panel.concentration_level)
        parts.append(
            f"Der HHI-Index betraegt {_fmt_int(int(panel.hhi_index))} "
            f"({level_de} Konzentration, Garcia-Vega 2006)."
        )

    # Satz 2: Top-Akteur
    top = panel.top_actors[0]
    top_name = str(top.get("name", ""))
    top_share = float(top.get("share", 0)) * 100
    if top_name:
        parts.append(
            f"Der fuehrende Akteur ist {top_name} "
            f"mit einem Marktanteil von {_fmt_pct(top_share)}."
        )

    # Satz 3: Top-3-Anteil
    if panel.top_3_share > 0:
        top3_pct = panel.top_3_share * 100
        if top3_pct > 50:
            interpretation = "eine deutliche Dominanz der drei groessten Akteure"
        elif top3_pct > 30:
            interpretation = "eine moderate Konzentration bei den Top-3-Akteuren"
        else:
            interpretation = "einen fragmentierten Markt"
        parts.append(
            f"Die Top-3-Akteure halten zusammen {_fmt_pct(top3_pct)} "
            f"— das zeigt {interpretation}."
        )

    # Satz 4: Gesamtanzahl Akteure
    total_actors = len(panel.full_actors) if panel.full_actors else len(panel.top_actors)
    parts.append(
        f"Insgesamt wurden {_fmt_int(total_actors)} Akteure identifiziert."
    )

    # Satz 5: Netzwerk-Stats
    if panel.network_nodes and panel.network_edges:
        parts.append(
            f"Das Kooperationsnetzwerk umfasst {_fmt_int(len(panel.network_nodes))} "
            f"Knoten und {_fmt_int(len(panel.network_edges))} Kanten."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC4: Funding Radar
# ---------------------------------------------------------------------------


def generate_funding_text(panel: FundingPanel) -> str:
    """Analysetext fuer UC4 — EU-Foerderungs-Analyse."""
    if panel.total_funding_eur <= 0:
        return ""

    parts: list[str] = []

    # Satz 1: Gesamtfoerderung
    parts.append(
        f"Die EU-Gesamtfoerderung belaeuft sich auf {_fmt_eur(panel.total_funding_eur)}."
    )

    # Satz 2: Projekte + Durchschnitt
    if panel.time_series:
        total_projects = sum(int(ts.get("projects", 0)) for ts in panel.time_series)
        if total_projects > 0:
            parts.append(
                f"Verteilt auf {_fmt_int(total_projects)} Projekte ergibt sich "
                f"eine durchschnittliche Projektgroesse von "
                f"{_fmt_eur(panel.avg_project_size)}."
            )

    # Satz 3: CAGR + Trend + Zeitraum
    if panel.funding_cagr != 0:
        period_info = f" ({panel.funding_cagr_period})" if panel.funding_cagr_period else ""
        parts.append(
            f"Die jaehrliche Wachstumsrate (CAGR) betraegt "
            f"{_fmt_pct(panel.funding_cagr)}{period_info} "
            f"und zeigt damit {_trend_word(panel.funding_cagr)}."
        )

    # Satz 4: Dominantes Programm
    if panel.by_programme:
        top_prog = panel.by_programme[0]
        prog_name = str(top_prog.get("programme", ""))
        prog_funding = float(top_prog.get("funding", 0))
        if prog_name:
            parts.append(
                f"Das dominierende Foerderprogramm ist {prog_name} "
                f"mit {_fmt_eur(prog_funding)}."
            )

    # Satz 5: Instrument-Breakdown (Top 2-3)
    if panel.instrument_breakdown:
        # Aggregiere Instrumente ueber alle Jahre
        instr_totals: dict[str, int] = {}
        for entry in panel.instrument_breakdown:
            instr = str(entry.get("instrument", ""))
            count = int(entry.get("count", 0))
            if instr:
                instr_totals[instr] = instr_totals.get(instr, 0) + count
        top_instruments = sorted(instr_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_instruments:
            instr_strs = [f"{name} ({_fmt_int(cnt)})" for name, cnt in top_instruments]
            parts.append(
                f"Die haeufigsten Foerderinstrumente sind {', '.join(instr_strs)}."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC5: CPC Flow
# ---------------------------------------------------------------------------


def generate_cpc_flow_text(panel: CpcFlowPanel) -> str:
    """Analysetext fuer UC5 — CPC-Technologiefluss (Jaccard-Index)."""
    if not panel.matrix or not panel.labels:
        return ""

    parts: list[str] = []

    # Satz 1: Patente + Verbindungen
    parts.append(
        f"Die Analyse umfasst {_fmt_int(panel.total_patents_analyzed)} Patente "
        f"mit {_fmt_int(panel.total_connections)} Co-Klassifikations-Verbindungen."
    )

    # Satz 2: CPC-Codes
    parts.append(
        f"Es wurden {_fmt_int(len(panel.labels))} CPC-Codes "
        f"auf Level {panel.cpc_level} identifiziert."
    )

    # Satz 3: Staerkste Verbindung (max off-diagonal)
    n = len(panel.matrix)
    max_val = 0.0
    max_i = 0
    max_j = 1
    for i in range(n):
        for j in range(i + 1, n):
            if panel.matrix[i][j] > max_val:
                max_val = panel.matrix[i][j]
                max_i = i
                max_j = j
    if max_val > 0 and max_i < len(panel.labels) and max_j < len(panel.labels):
        label_a = panel.labels[max_i]
        label_b = panel.labels[max_j]
        # CPC-Beschreibungen einbeziehen, falls vorhanden
        desc_a = panel.cpc_descriptions.get(label_a, "")
        desc_b = panel.cpc_descriptions.get(label_b, "")
        name_a = f"{label_a} ({desc_a})" if desc_a else label_a
        name_b = f"{label_b} ({desc_b})" if desc_b else label_b
        parts.append(
            f"Die staerkste Verbindung besteht zwischen {name_a} und {name_b} "
            f"(Jaccard = {max_val:.3f})."
        )

    # Satz 4: Durchschnittlicher Jaccard (non-zero off-diagonal)
    off_diag_values: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            if panel.matrix[i][j] > 0:
                off_diag_values.append(panel.matrix[i][j])
    if off_diag_values:
        avg_jaccard = sum(off_diag_values) / len(off_diag_values)
        parts.append(
            f"Der durchschnittliche Jaccard-Index (nicht-null) betraegt {avg_jaccard:.3f}."
        )

    # Satz 5: Interpretation
    if off_diag_values:
        avg_j = sum(off_diag_values) / len(off_diag_values)
        if avg_j > 0.3:
            parts.append(
                "Die hohe durchschnittliche Verflechtung deutet auf ein "
                "breites, interdisziplinaeres Technologiefeld hin."
            )
        elif avg_j > 0.1:
            parts.append(
                "Die moderate Verflechtung zeigt ein Technologiefeld "
                "mit erkennbaren Querbezuegen zwischen den CPC-Klassen."
            )
        else:
            parts.append(
                "Die geringe Verflechtung deutet auf ein "
                "spezialisiertes Technologiefeld mit wenig Ueberlappung hin."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC6: Geographic Intelligence
# ---------------------------------------------------------------------------


_EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "EL", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT",
    "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    # EEA
    "IS", "LI", "NO",
}


def generate_geographic_text(panel: GeographicPanel) -> str:
    """Analysetext fuer UC6 — Geografische Analyse."""
    if panel.total_countries == 0:
        return ""

    parts: list[str] = []

    # Satz 1: Laender + Staedte
    parts.append(
        f"Die Technologie ist in {_fmt_int(panel.total_countries)} Laendern "
        f"und {_fmt_int(panel.total_cities)} Staedten vertreten."
    )

    # Satz 2: Cross-Border-Anteil
    if panel.cross_border_share > 0:
        parts.append(
            f"Der Anteil grenzueberschreitender Projekte betraegt "
            f"{_fmt_pct(panel.cross_border_share * 100)}."
        )

    # Satz 3: Top-Land
    if panel.country_distribution:
        top = panel.country_distribution[0]
        country_name = str(top.get("country", ""))
        country_total = int(top.get("total", 0))
        if country_name:
            parts.append(
                f"Das fuehrende Land ist {country_name} "
                f"mit {_fmt_int(country_total)} Aktivitaeten."
            )

    # Satz 4: Top-Kooperationspaar
    if panel.collaboration_pairs:
        top_pair = panel.collaboration_pairs[0]
        pair_a = str(top_pair.get("country_a", ""))
        pair_b = str(top_pair.get("country_b", ""))
        pair_count = int(top_pair.get("count", 0))
        if pair_a and pair_b:
            parts.append(
                f"Die staerkste Kooperationsachse verlaeuft zwischen "
                f"{pair_a} und {pair_b} ({_fmt_int(pair_count)} gemeinsame Projekte)."
            )

    # Satz 5: Europa-Fokus (EU vs. non-EU in Top 10)
    if panel.country_distribution:
        top_10 = panel.country_distribution[:10]
        eu_count = sum(
            1 for c in top_10
            if str(c.get("country", "")).upper() in _EU_COUNTRIES
        )
        non_eu = len(top_10) - eu_count
        if eu_count > non_eu:
            parts.append(
                f"In den Top-10 dominieren EU-/EWR-Staaten "
                f"({eu_count} von {len(top_10)}), "
                f"was den europaeischen Fokus der Datenquellen widerspiegelt."
            )
        elif eu_count > 0:
            parts.append(
                f"In den Top-10 befinden sich {eu_count} EU-/EWR-Staaten "
                f"und {non_eu} Drittstaaten."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC7: Research Impact
# ---------------------------------------------------------------------------


def generate_research_impact_text(panel: ResearchImpactPanel) -> str:
    """Analysetext fuer UC7 — Forschungsimpact (Banks 2006, Valenzuela et al. 2015)."""
    if panel.total_papers == 0:
        return ""

    parts: list[str] = []

    # Satz 1: h-Index
    parts.append(
        f"Der h-Index des Technologiefeldes betraegt {panel.h_index} "
        f"(Topic-Level-Adaption nach Banks 2006)."
    )

    # Satz 2: Papers + Durchschnittszitationen
    parts.append(
        f"Basierend auf {_fmt_int(panel.total_papers)} Papers ergibt sich "
        f"ein Durchschnitt von {panel.avg_citations:.1f} Zitationen pro Paper."
    )

    # Satz 3: Influential Ratio
    if panel.influential_ratio > 0:
        parts.append(
            f"Der Anteil einflussreicher Zitationen betraegt "
            f"{_fmt_pct(panel.influential_ratio * 100)} "
            f"(Valenzuela et al. 2015 — experimentelle Metrik)."
        )

    # Satz 4: Top-Paper
    if panel.top_papers:
        top = panel.top_papers[0]
        title = str(top.get("title", ""))
        citations = int(top.get("citations", 0))
        if title:
            # Titel auf 80 Zeichen kuerzen
            short_title = title[:80] + "..." if len(title) > 80 else title
            parts.append(
                f"Das meistzitierte Paper ist \"{short_title}\" "
                f"mit {_fmt_int(citations)} Zitationen."
            )

    # Satz 5: Top-Venue
    if panel.top_venues:
        top_venue = panel.top_venues[0]
        venue_name = str(top_venue.get("venue", ""))
        venue_count = int(top_venue.get("count", 0))
        if venue_name:
            parts.append(
                f"Die fuehrende Publikationsquelle ist \"{venue_name}\" "
                f"mit {_fmt_int(venue_count)} Papers."
            )

    # Satz 6: Sampling-Hinweis
    if panel.total_papers >= 200:
        parts.append(
            "Hinweis: Die Analyse basiert auf einer Stichprobe der "
            "Top-200 relevantesten Papers — der h-Index ist eine Approximation."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC8: Temporal Dynamics
# ---------------------------------------------------------------------------


def generate_temporal_text(panel: TemporalPanel) -> str:
    """Analysetext fuer UC8 — Temporale Dynamik (Malerba & Orsenigo 1999)."""
    if not panel.entrant_persistence_trend:
        return ""

    parts: list[str] = []

    # Satz 1: New Entrant Rate
    parts.append(
        f"Die Neueintrittrate betraegt {_fmt_pct(panel.new_entrant_rate * 100)} "
        f"(Malerba & Orsenigo 1999)."
    )

    # Satz 2: Persistence Rate
    parts.append(
        f"Die Verbleibrate liegt bei {_fmt_pct(panel.persistence_rate * 100)}."
    )

    # Satz 3: Dominantes Programm
    if panel.dominant_programme:
        parts.append(
            f"Das dominierende Foerderinstrument ist {panel.dominant_programme}."
        )

    # Satz 4: Top-Akteur
    if panel.actor_timeline:
        top = panel.actor_timeline[0]
        name = str(top.get("name", ""))
        total_count = int(top.get("total_count", 0))
        if name:
            parts.append(
                f"Der aktivste Akteur ist {name} "
                f"mit {_fmt_int(total_count)} Aktivitaeten."
            )

    # Satz 5: Technologie-Breite Trend
    if len(panel.technology_breadth) >= 2:
        first = panel.technology_breadth[0]
        last = panel.technology_breadth[-1]
        first_sub = int(first.get("unique_cpc_subclasses", 0))
        last_sub = int(last.get("unique_cpc_subclasses", 0))
        if first_sub > 0 and last_sub > 0:
            if last_sub > first_sub:
                parts.append(
                    f"Die Technologie-Breite hat sich von {first_sub} auf "
                    f"{last_sub} CPC-Subklassen ausgeweitet — "
                    f"das Feld wird technologisch diverser."
                )
            elif last_sub < first_sub:
                parts.append(
                    f"Die Technologie-Breite hat sich von {first_sub} auf "
                    f"{last_sub} CPC-Subklassen verringert — "
                    f"das Feld konvergiert technologisch."
                )
            else:
                parts.append(
                    f"Die Technologie-Breite bleibt stabil bei "
                    f"{last_sub} CPC-Subklassen."
                )

    return " ".join(parts)
