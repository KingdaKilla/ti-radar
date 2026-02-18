# User Stories — TI-Radar

## Uebergreifende User Story

**Als** Technology Scout in einem Forschungsfoerderungsinstitut,
**moechte ich** durch Eingabe eines Technologiebegriffs ein umfassendes Dashboard erhalten, das Patente (EPO DOCDB), EU-Forschungsprojekte (CORDIS), Publikationen (OpenAIRE) und Zitationsdaten (Semantic Scholar) integriert,
**damit ich** datengestuetzt und reproduzierbar die strategische Positionierung einer Technologie im europaeischen Innovationsoekosystem bewerten kann — ohne auf LLM-generierte Interpretationen angewiesen zu sein.

**Akzeptanzkriterien:**
- Ein einzelner POST-Request (`/api/v1/radar`) liefert alle 8 Use Cases parallel (Antwortzeit < 500ms mit externen APIs)
- Alle Berechnungen sind deterministisch und reproduzierbar (`explainability.deterministic = true`)
- Das Dashboard zeigt Quellenangaben, Methoden und Datenvollstaendigkeits-Warnungen transparent an
- Unvollstaendige Datenjahre (z.B. 2025) werden visuell als grau hinterlegte Zone mit Hinweistooltip markiert

---

## UC1 — Technologie-Landschaft

**Als** Technology Scout,
**moechte ich** einen Ueberblick ueber die Aktivitaet einer Technologie anhand von Patenten, EU-Projekten und Publikationen erhalten,
**damit ich** erkennen kann, ob ein Technologiefeld waechst, stagniert oder schrumpft.

**Akzeptanzkriterien:**
- Anzeige der Gesamtzahlen: Patente (EPO DOCDB), Projekte (CORDIS), Publikationen (OpenAIRE)
- Zeitreihe mit normalisierten Year-over-Year-Wachstumsraten (Watts & Porter 1997) fuer alle drei Datentypen
- Umschaltbare Darstellung zwischen Wachstumsraten (%) und absoluten Werten
- Laenderverteilung mit EU/EEA-Fokus: europaeische Laender farbig oben, Nicht-EU grau unten
- CSV-Export der Zeitreihendaten (Jahr, Patente, Projekte, Publikationen, Wachstumsraten)
- Tooltip zeigt bei unvollstaendigen Jahren (ab `data_complete_until + 1`) einen Warnhinweis

**Datenquellen:** EPO DOCDB (lokal), CORDIS (lokal), OpenAIRE (API)
**Methoden:** YoY-Wachstumsrate = `((V_t - V_{t-1}) / V_{t-1}) * 100`

---

## UC2 — Technologie-Reifegrad

**Als** Technology Scout,
**moechte ich** den Reifegrad einer Technologie anhand einer S-Curve-Analyse auf Patent-Familien bestimmen,
**damit ich** einschaetzen kann, ob sich eine Technologie in der Entstehungs-, Wachstums-, Reife- oder Saettigungsphase befindet.

**Akzeptanzkriterien:**
- S-Curve-Fit (Logistik oder Gompertz, Modellselektion nach Franses 1994) auf kumulative Patent-Daten
- Phasenklassifikation nach Gao et al. (2013): Emerging (<10%), Growing (10-50%), Mature (50-90%), Saturation (>=90% der Saettigung)
- Anzeige von: Phase-Badge (farbig), Reifegrad (%), Konfidenz (R²), Wendepunkt-Jahr
- R²-Qualitaetslabel: Exzellent (>=0.9), Gut (>=0.7), Akzeptabel (>=0.5), Schwach (<0.5)
- Kumulative Darstellung mit S-Curve-Fit-Linie und farbigen Phasenbereichen
- Umschaltbar auf jaehrliche Balken-Darstellung
- CSV-Export (Jahr, Patente, Kumulativ, S-Curve-Fit)

**Datenquellen:** EPO DOCDB (lokal) — ausschliesslich Patent-Daten (Gao et al. 2013)
**Methoden:** Levenberg-Marquardt-Optimierung, `L / (1 + exp(-k*(x - x0)))`

---

## UC3 — Wettbewerbsanalyse

**Als** Technology Scout,
**moechte ich** die wichtigsten Akteure in einem Technologiefeld identifizieren und deren Marktkonzentration bewerten,
**damit ich** potenzielle Kooperationspartner, Wettbewerber und die Fragmentierung des Feldes einschaetzen kann.

**Akzeptanzkriterien:**
- HHI-Index (DOJ/FTC 2010; Garcia-Vega 2006) mit Konzentrations-Badge: Gering (<1500), Maessig (1500-2500), Hoch (>2500)
- Top-3-Anteil (Aktivitaetsanteil der drei groessten Akteure)
- Drei umschaltbare Ansichten:
  - **Diagramm**: Horizontales Balkendiagramm der Top-8-Akteure (klickbar fuer Cross-UC-Verlinkung zu UC4)
  - **Netzwerk**: Force-Directed-Graph (D3.js) der Akteur-Ko-Partizipation
  - **Tabelle**: Sortierbare Tabelle mit Rang, Name, Patente, Projekte, Gesamt, Anteil, Land, KMU-Status
- GLEIF-Integration fuer Unternehmens-Identifikation (LEI-Lookup mit SQLite-Cache, 90 Tage TTL)
- CSV-Export (Rang, Name, Patente, Projekte, Gesamt, Anteil%, Land)
- Klick auf einen Akteur uebertraegt die Auswahl an UC4 (Linked Brushing)

**Datenquellen:** EPO DOCDB (lokal), CORDIS (lokal), GLEIF (API, gecacht)
**Methoden:** HHI = `sum(s_i^2) * 10.000`, Ko-Partizipations-Netzwerk

---

## UC4 — Foerderungsradar

**Als** Technology Scout,
**moechte ich** die EU-Foerderung einer Technologie nach Programm (FP7, H2020, Horizon Europe), Volumen und Trend analysieren,
**damit ich** Foerderdynamiken und das finanzielle Engagement der EU in einem Technologiefeld bewerten kann.

**Akzeptanzkriterien:**
- Gesamtfoerderung (EUR), Projektanzahl, durchschnittliche Projektgroesse
- CAGR (Compound Annual Growth Rate) der Foerderung mit Formel-Tooltip
- Programmverteilung als farbiger Balken (FP7 gelb, H2020 grau, HORIZON koralle) mit EUR-Betraegen und Anteilen
- Gestapeltes Balkendiagramm: Foerderung pro Jahr aufgeschluesselt nach Programm
- Programme koennen einzeln ein-/ausgeblendet werden (Legende klickbar)
- Instrumenten-Aufschluesselung (RIA, IA, CSA etc.)
- Anzeige des in UC3 ausgewaehlten Akteurs (Cross-UC-Verlinkung)
- CSV-Export (Jahr, Projekte, Foerderung EUR)
- Tooltip zeigt Werte als "X M EUR" formatiert

**Datenquellen:** CORDIS (lokal)
**Methoden:** CAGR = `((V_f / V_i)^(1/n) - 1) * 100`

**Limitationen des CAGR:**
- **Endpunktsensitivitaet**: Der CAGR beruecksichtigt ausschliesslich den Anfangs- und Endwert des Berechnungszeitraums. Alle Zwischenjahre werden ignoriert. Ein atypisch hohes oder niedriges Start-/Endjahr verzerrt das Ergebnis erheblich.
- **Glaettungsannahme**: Der CAGR unterstellt ein konstantes jaehrliches Wachstum und bildet keine Strukturbrueche ab. EU-Foerderprogramme wechseln in diskreten Zyklen (FP7 2007-2013, H2020 2014-2020, Horizon Europe 2021-2027), was zu sprunghaften Foerderaenderungen fuehrt, die der CAGR nicht erfasst.
- **Null- und Negativwerte**: Foerderjahre ohne Daten (funding = 0) werden aus der Berechnung ausgeschlossen. Die Funktion gibt 0.0 zurueck, wenn Start- oder Endwert <= 0 ist, was bei jungen Technologien mit lueckenhafter Foerderung haeufig vorkommt.
- **Kurze Zeitraeume**: Bei weniger als 3 Perioden ist der CAGR statistisch nicht belastbar und kann zu Fehlinterpretationen fuehren.
- **Keine Volatilitaetsmessung**: Der CAGR liefert keine Information ueber die Streuung oder Stabilitaet der jaehrlichen Foerdersummen. Zwei Technologien mit identischem CAGR koennen voellig unterschiedliche Foerderverlaeufe aufweisen.
- **Datenvollstaendigkeit**: Der CAGR wird nur bis zum letzten vollstaendigen Datenjahr berechnet (`data_complete_until`), um Verzerrungen durch unvollstaendige Jahresdaten zu vermeiden. Der Berechnungszeitraum wird im Tooltip angezeigt.

---

## UC5 — Technologiefluss (CPC-Co-Klassifikation)

**Als** Technology Scout,
**moechte ich** die technologische Verflechtung eines Feldes anhand von CPC-Co-Klassifikationen analysieren,
**damit ich** erkennen kann, welche Technologiebereiche miteinander verschmelzen und wo Konvergenz stattfindet.

**Akzeptanzkriterien:**
- Jaccard-Aehnlichkeitsmatrix (Curran & Leker 2011) auf CPC-Level-4-Ebene (Yan & Luo 2019)
- Zwei Visualisierungen:
  - **Heatmap**: Farbintensitaet proportional zum Jaccard-Wert, Diagonale ausgegraut, CPC-Sektions-Farbcodes (A-H, Y)
  - **Chord-Diagramm** (D3.js): Bogendiagramm der CPC-Verflechtungen
- Interaktive Regler:
  - **CPC-Klassen-Anzahl**: Slider (2 bis max. 15) steuert, wie viele Top-CPC-Codes einbezogen werden
  - **Jahresbereich**: Zwei Dropdowns fuer Min-/Max-Jahr
- Frontend-seitige Jaccard-Neuberechnung bei Regler-Aenderung (Backend sendet `year_data` einmalig)
- Top-CPC-Paare als Badge-Liste mit Jaccard-Wert und Hover-Tooltip mit CPC-Beschreibungen
- CSV-Export (CPC A, Beschreibung A, CPC B, Beschreibung B, Jaccard)

**Datenquellen:** EPO DOCDB (lokal), Stichprobe max. 10.000 Patente
**Methoden:** Jaccard-Index = `|A ∩ B| / |A ∪ B|` (Jaccard 1901)

---

## UC6 — Geografie

**Als** Technology Scout,
**moechte ich** die raeumliche Verteilung von Patentaktivitaet und EU-Projekten visualisieren,
**damit ich** regionale Innovationszentren und internationale Kooperationsachsen identifizieren kann.

**Akzeptanzkriterien:**
- Gesamtzahl aktiver Laender und Staedte
- Cross-Border-Anteil (Anteil grenzueberschreitender Kooperationen)
- Laenderverteilung (bis zu 15 Laender) mit gestapeltem Balkendiagramm (Patente + Projekte)
- Europa-Fokus: EU/EEA-Laender farbig oben, Nicht-EU grau unten (Narin 1994; Luukkonen et al. 1993)
- Top-10-Kooperationsachsen als Fortschrittsbalken (Laenderpaar + Anzahl)
- Top-10-Staedte als Pill-Badges (CORDIS-Standorte)
- CSV-Export (Code, Land, Patente, Projekte, Gesamt, EU-Status)

**Datenquellen:** EPO DOCDB (lokal), CORDIS (lokal)
**Methoden:** Laenderzuordnung via Patent-Anmelderland + CORDIS-Projektkoordinatoren

---

## UC7 — Forschungsimpact

**Als** Technology Scout,
**moechte ich** den wissenschaftlichen Einfluss eines Technologiefelds anhand von Zitationsmetriken und Publikationsdaten bewerten,
**damit ich** die akademische Reife und die einflussreichsten Forschungsarbeiten identifizieren kann.

**Akzeptanzkriterien:**
- h-Index (Hirsch 2005) mit Formel-Tooltip, adaptiert auf Topic-Level (Banks 2006)
- Gesamtanzahl Papers, durchschnittliche Zitationen, Influential-Ratio (Valenzuela et al. 2015)
- Drei umschaltbare Ansichten:
  - **Trend**: Liniendiagramm mit Paper-Anzahl und Zitationen pro Jahr
  - **Papers**: Scrollbare Liste der Top-Papers (Titel, Venue, Jahr, Zitationen)
  - **Venues**: Horizontales Balkendiagramm der Top-Venues
- Publikationstyp-Aufschluesselung als Pill-Badges
- Informativer Leerzustand bei Semantic-Scholar-Rate-Limiting oder -Nichtverfuegbarkeit
- CSV-Export (Titel, Jahr, Zitationen, Venue)

**Datenquellen:** Semantic Scholar Academic Graph API (extern), Stichprobe Top-200 Papers
**Methoden:** h-Index = groesstes h, sodass h Papers >= h Zitationen haben

---

## UC8 — Temporale Dynamik

**Als** Technology Scout,
**moechte ich** die zeitliche Entwicklung der Akteursstruktur, Foerderinstrumente und technologischen Breite verfolgen,
**damit ich** Trends in der Akteursdynamik (Fluktuation vs. Stabilitaet) und technologische Diversifizierung erkennen kann.

**Akzeptanzkriterien:**
- Neueintrittsrate und Verbleibquote (Malerba & Orsenigo 1999) als KPI-Karten
- Dominantes Programm (haeufigster Foerderinstrumententyp)
- Drei umschaltbare Ansichten:
  - **Dynamik**: Flaechendiagramm (Akteure gesamt pro Jahr) + Liniendiagramm (Eintritts-/Verbleibrate %) + Top-6-Akteur-Ranking mit Fortschrittsbalken
  - **Programme**: Gestapeltes Balkendiagramm der Foerderinstrumente (RIA, IA, CSA etc.) pro Jahr, dynamisch extrahierte Top-8-Instrumente
  - **Breite**: Dual-Achsen-Flaechendiagramm — CPC-Sektionen A-H (links, gelb) + CPC-Subklassen Level 4 (rechts, gruen) ueber die Zeit (Leydesdorff et al. 2015)
- CSV-Export (Jahr, Akteure gesamt, Neueintrittsrate%, Verbleibrate%)

**Datenquellen:** EPO DOCDB (lokal), CORDIS (lokal)
**Methoden:** Akteur-Persistenzanalyse, CPC-Diversitaetsmessung

---

## Querschnittsfunktionen

### Datenvollstaendigkeit

**Als** Nutzer,
**moechte ich** klar erkennen, welche Datenjahre vollstaendig sind und welche noch unvollstaendig,
**damit ich** keine Fehlinterpretationen auf Basis unvollstaendiger Daten treffe.

- Backend ermittelt `data_complete_until` (letztes vollstaendiges Jahr) aus der Patent-DB
- Alle Zeitreihen-Charts markieren unvollstaendige Jahre mit grauer Hinterlegung und gestrichelter Linie ("unvollst.")
- Tooltip zeigt bei Hover auf unvollstaendige Jahre: "Daten ab [Jahr] unvollstaendig"

### Transparenz & Erklaerbarkeit (UC9)

**Als** Nutzer,
**moechte ich** nachvollziehen koennen, welche Datenquellen, Methoden und Annahmen einer Analyse zugrunde liegen,
**damit ich** die Ergebnisse bewerten und gegenueber Dritten verantworten kann.

- Expandierbare ExplainabilityBar am unteren Bildschirmrand
- Anzeige: verwendete Datenquellen, Methoden, Abfragezeit, Warnungen
- API-Alerts (Token-Ablauf, Fehler) in Rot/Gelb hervorgehoben
- Alle Panels zeigen Quellenfusszeilen mit Literaturverweisen

### Autocomplete & Suche

**Als** Nutzer,
**moechte ich** bei Eingabe eines Technologiebegriffs Vorschlaege aus den vorhandenen Daten erhalten,
**damit ich** passende Suchbegriffe schnell finden und Tippfehler vermeiden kann.

- FTS5-Prefix-Suche mit Ngram-Extraktion
- Debounce + Keyboard-Navigation (Pfeiltasten, Enter, Escape)
- Beispiel-Chips fuer Schnelleinstieg

### Cross-UC-Interaktion

**Als** Nutzer,
**moechte ich** in UC3 einen Akteur anklicken und in UC4 dessen Foerderhistorie sehen,
**damit ich** Zusammenhaenge zwischen Wettbewerbsposition und Foerderung erkennen kann.

- Klick auf Akteur-Balken in UC3 setzt `selectedActor`
- UC4 zeigt den ausgewaehlten Akteur als Badge und filtert ggf. Daten

### CSV-Export

**Als** Nutzer,
**moechte ich** die Daten jedes Use Case als CSV-Datei herunterladen koennen,
**damit ich** die Rohdaten in eigenen Werkzeugen (Excel, R, Python) weiterverarbeiten kann.

- Jedes Panel hat einen Download-Button im Header
- Export ueber Browser Blob API (kein Server-Roundtrip)

---

## Literaturverzeichnis

| Referenz | Verwendung |
|----------|-----------|
| Banks (2006) | h-Index auf Topic-Level (UC7) |
| Curran & Leker (2011) | CPC-Co-Klassifikation (UC5) |
| DOJ/FTC (2010) | HHI-Schwellenwerte (UC3) |
| Franses (1994) | Gompertz/Logistic-Modellselektion (UC2) |
| Gao et al. (2013) | S-Curve-Phasenklassifikation (UC2) |
| Garcia-Vega (2006) | HHI-Marktkonzentration (UC3) |
| Hirsch (2005) | h-Index-Definition (UC7) |
| Jaccard (1901) | Aehnlichkeitskoeffizient (UC5) |
| Lee et al. (2016) | Patent-Familien-Deduplizierung (UC2) |
| Leydesdorff et al. (2015) | Technologiebreite via CPC (UC8) |
| Luukkonen et al. (1993) | Internationale Kooperation (UC6) |
| Malerba & Orsenigo (1999) | Akteur-Dynamik (UC8) |
| Narin (1994) | Patent-Bibliometrie (UC6) |
| OECD (2009) | Patent-Familien (UC2) |
| Valenzuela et al. (2015) | Influential Citations (UC7) |
| Watts & Porter (1997) | YoY-Wachstumsraten (UC1) |
| Yan & Luo (2019) | CPC-Level-4-Analyse (UC5) |
