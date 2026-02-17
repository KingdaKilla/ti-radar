# UC Evolution Design — Full Platform (Approach C)

**Date:** 2026-02-18
**Status:** Approved
**Scope:** Enhance 5 existing UCs + add 3 new UCs (UC6-UC8) + integrate 2 new APIs (Semantic Scholar, GLEIF)

---

## 1. Existing UC Enhancements

### UC1 Landscape — Geographic Drill-Down

**Unused data unlocked:** `patents.applicant_countries`, `organizations.city`

| Change | Data Source | Detail |
|--------|------------|--------|
| Inventor nationality | `patents.applicant_countries` (comma-separated) | Parse like CPC codes, aggregate by country |
| City-level granularity | `organizations.city` from CORDIS | City distribution for project orgs |
| Cross-border metric | `organizations.country` per project | Projects with orgs from 3+ countries |

Backend: New repo methods `PatentRepository.count_by_applicant_country()`, `CordisRepository.orgs_by_city()`.
Frontend: Interactive treemap (Recharts `Treemap`, already available) replacing static bar chart. Country > City > Actor hierarchy.

### UC2 Maturity — Patent Family Deduplication

**Unused data unlocked:** `patents.family_id` (indexed but never queried)

| Change | Detail |
|--------|--------|
| Unique invention count | Group by `family_id`, count distinct families instead of individual filings |
| Dual metric display | Show both "Patentanmeldungen" and "Erfindungsfamilien" |
| S-Curve accuracy | Family-based cumulative count avoids inflating early-stage duplicates |

Backend: New repo method `PatentRepository.count_families_by_year()` with `COUNT(DISTINCT family_id)`.
Frontend: Toggle or secondary line in S-Curve chart.

### UC3 Competitive — Role, SME & GLEIF Enrichment

**Unused data unlocked:** `organizations.role`, `organizations.sme`, `organizations.ec_contribution`

| Change | Detail |
|--------|--------|
| Coordinator vs. Partner | Parse `role` field, weight coordinators higher or show as separate metric |
| SME indicator | New "SME-Anteil" metric card from `sme` field |
| Per-org funding | `ec_contribution` shows who gets the most money (not just participation count) |
| GLEIF entity resolution | Merge name variants, add verified country/city (see Section 5) |

Backend: Extend `analyze_competitive()` with role/SME aggregation. GLEIF post-processing step.
Frontend: SME badge, coordinator count metric, verified name display.

### UC4 Funding — Instrument Breakdown

**Unused data unlocked:** `projects.funding_scheme`, `projects.end_date`, `organizations.ec_contribution`

| Change | Detail |
|--------|--------|
| Funding instrument types | Parse `funding_scheme` (RIA, CSA, MSCA, ERC, SME-Instrument) |
| Instrument stacked bar | Distribution by instrument type over time |
| Per-org funding | Top organizations by actual EU contribution received |
| Project duration | `end_date - start_date` average by instrument type |

Backend: New repo method `CordisRepository.funding_by_instrument()`. Duration calculation in use case.
Frontend: New stacked bar (instrument types), duration metric card.

### UC5 CPC Flow — No Changes

UC5 (Jaccard heatmap + chord diagram) is already mature. No enhancements planned.

---

## 2. UC6 — Geographic Intelligence (New)

**Goal:** Answer "Where is the technology being developed?" at country AND city level.

### Data Sources (all already in DBs)

| Source | Field | Granularity |
|--------|-------|-------------|
| `patents.country` | Filing country | Country |
| `patents.applicant_countries` | Inventor nationalities (comma-separated) | Country |
| `organizations.country` | CORDIS org country | Country |
| `organizations.city` | CORDIS org city | City |

### Backend

**New file:** `src/ti_radar/use_cases/geographic.py`

```python
async def analyze_geographic(
    technology: str, start_year: int, end_year: int
) -> tuple[GeographicPanel, list[str], list[str], list[str]]:
```

Sub-analyses:
- Country aggregation: merge patent filing countries + inventor countries + CORDIS org countries
- City aggregation: CORDIS `organizations.city` grouped by country
- Cross-border metric: projects with `COUNT(DISTINCT organizations.country) >= 3`
- Collaboration flows: country-pair co-occurrence from CORDIS project partnerships

New repo methods:
- `PatentRepository.count_by_applicant_country(query, start_year, end_year)` — parse comma-separated `applicant_countries`
- `CordisRepository.orgs_by_city(query, start_year, end_year, limit)` — city + country + count
- `CordisRepository.cross_border_projects(query, start_year, end_year)` — projects with 3+ countries
- `CordisRepository.country_collaboration_pairs(query, start_year, end_year, limit)` — country pairs by co-occurrence

### Schema

```python
class GeographicPanel(BaseModel):
    total_countries: int = 0
    total_cities: int = 0
    cross_border_share: float = 0.0
    country_distribution: list[dict[str, Any]] = []    # {country, patents, projects, total}
    city_distribution: list[dict[str, Any]] = []       # {city, country, count}
    collaboration_pairs: list[dict[str, Any]] = []     # {country_a, country_b, count}
```

### Frontend

**New file:** `frontend/src/components/GeographicPanel.jsx`

- Metric cards: "Laender aktiv", "Staedte aktiv", "Cross-Border-Anteil %"
- **Treemap** (Recharts `Treemap`): Country > City > Actors, sized by activity count
- **Collaboration flow table**: Top country pairs, project count, sorted descending
- Quellen-Fusszeile: "EPO DOCDB (Anmeldelaender), CORDIS (Organisationsstandorte)"

No new npm dependencies — Recharts `Treemap` already included.

---

## 3. UC7 — Research Impact (New, Semantic Scholar API)

**Goal:** Answer "How impactful is the academic research?" — citations, h-index, top papers, venues.

### Data Source: Semantic Scholar Academic Graph API

- **Endpoint:** `GET https://api.semanticscholar.org/graph/v1/paper/search`
- **Auth:** None required (1000 req/sec shared among unauthenticated users)
- **Fields:** `title,year,citationCount,venue,authors,fieldsOfStudy,publicationTypes,influentialCitationCount,referenceCount`
- **Pagination:** `offset` + `limit` (max 100 per request)
- **Rate limiting:** Conservative `asyncio.sleep(0.1)` between paginated requests

### Backend

**New file:** `src/ti_radar/infrastructure/adapters/semantic_scholar_adapter.py`

```python
class SemanticScholarAdapter:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search_papers(
        self, query: str, year_start: int, year_end: int, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Paginated paper search with year filtering."""

    async def count_by_year(
        self, query: str, year_start: int, year_end: int
    ) -> list[dict[str, Any]]:
        """Citation counts aggregated per year."""
```

- Uses `httpx.AsyncClient` (same as OpenAIRE adapter)
- Timeout: 10s per request
- Graceful degradation: returns empty list on failure

**New file:** `src/ti_radar/use_cases/research_impact.py`

```python
async def analyze_research_impact(
    technology: str, start_year: int, end_year: int
) -> tuple[ResearchImpactPanel, list[str], list[str], list[str]]:
```

Metrics (all deterministic):
- **Field h-index:** Largest h where h papers have >= h citations
- **Avg. citations/paper:** total_citations / paper_count
- **Influential citation ratio:** influential_citations / total_citations
- **Venue concentration:** Top-3 venues share of all papers
- **Citation trend:** citations per year
- **Top papers:** sorted by citationCount, top 10
- **Venue distribution:** top 8 venues by paper count
- **Publication types:** aggregate by publicationType

### Schema

```python
class ResearchImpactPanel(BaseModel):
    h_index: int = 0
    avg_citations: float = 0.0
    total_papers: int = 0
    influential_ratio: float = 0.0
    citation_trend: list[dict[str, Any]] = []       # {year, citations, paper_count}
    top_papers: list[dict[str, Any]] = []            # {title, venue, year, citations, authors_short}
    top_venues: list[dict[str, Any]] = []            # {venue, count, share}
    publication_types: list[dict[str, Any]] = []     # {type, count}
```

### Frontend

**New file:** `frontend/src/components/ResearchImpactPanel.jsx`

- Metric cards: h-index, avg citations, total papers, influential ratio
- **Citation trend** — Recharts `LineChart` (citations per year)
- **Top Papers** — compact sortable table (5-10 rows): title, venue, year, citations
- **Venue distribution** — horizontal `BarChart` (top 8)
- **Publication types** — badge row with counts
- Quellen-Fusszeile: "Semantic Scholar Academic Graph API; h-index (Hirsch, 2005)"

---

## 4. UC8 — Temporal Dynamics (New, from existing data)

**Goal:** Answer "How does the technology landscape evolve over time?" — actor entry/exit, programme transitions, field openness.

### Data Sources (all already in DBs)

| Source | Field | Purpose |
|--------|-------|---------|
| `patents` + `organizations` by year | Actor names per year | Entry/exit tracking |
| `projects.framework` | FP7, H2020, HORIZON | Programme transitions |
| `projects.funding_scheme` | RIA, CSA, ERC, MSCA | Instrument evolution |
| `patents.cpc_codes` by year | CPC sections per year | Technology breadth |

### Backend

**New file:** `src/ti_radar/use_cases/temporal.py`

```python
async def analyze_temporal(
    technology: str, start_year: int, end_year: int
) -> tuple[TemporalPanel, list[str], list[str], list[str]]:
```

Sub-analyses:

| Analysis | Method | Output |
|----------|--------|--------|
| Actor dynamics | Top 10 actors per year from patents + CORDIS | `actor_timeline: [{name, years_active, total}]` |
| New entrant rate | Actors appearing first time in year Y / total actors in Y | `float` per year |
| Persistence rate | Actors in both Y and Y-1 / actors in Y-1 | `float` per year |
| Programme evolution | Project count by framework per year | `[{year, fp7, h2020, horizon}]` |
| Instrument evolution | Project count by `funding_scheme` per year | `[{year, scheme, count}]` |
| Technology breadth | Unique CPC sections per year | `[{year, unique_sections}]` |

New repo methods:
- `PatentRepository.top_applicants_by_year(query, start_year, end_year, limit)` — actor + year + count
- `CordisRepository.orgs_by_year(query, start_year, end_year, limit)` — org + year + count
- `CordisRepository.projects_by_instrument_and_year(query, start_year, end_year)` — funding_scheme + year + count

### Schema

```python
class TemporalPanel(BaseModel):
    new_entrant_rate: float = 0.0
    persistence_rate: float = 0.0
    dominant_programme: str = ""
    actor_timeline: list[dict[str, Any]] = []            # {name, years_active: [int], total_count}
    programme_evolution: list[dict[str, Any]] = []        # {year, fp7, h2020, horizon}
    entrant_persistence_trend: list[dict[str, Any]] = []  # {year, new_entrant_rate, persistence_rate}
    instrument_evolution: list[dict[str, Any]] = []       # {year, scheme, count}
    technology_breadth: list[dict[str, Any]] = []         # {year, unique_cpc_sections}
```

### Frontend

**New file:** `frontend/src/components/TemporalPanel.jsx`

- Metric cards: New entrant rate (latest year), Persistence rate, Dominant programme
- **Actor timeline** — custom grid: rows = top 10 actors, columns = years, cells colored if active (styled divs, no new library)
- **Programme stacked area** — Recharts `AreaChart` (FP7/H2020/Horizon shares over time)
- **Entrant/Persistence dual line** — Recharts `LineChart` (two lines, inversely correlated = healthy field)
- Quellen-Fusszeile: "Akteur-Dynamik: EPO DOCDB + CORDIS; Rahmenprogramme: CORDIS"

Full width panel (like UC5) — actor timeline grid needs horizontal space.

---

## 5. GLEIF Integration — Entity Resolution

**Goal:** Resolve actor names to standardized legal entities. Enriches UC3, UC6, UC8.

### API: GLEIF LEI Lookup

- **Endpoint:** `GET https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]=...`
- **Auth:** None required
- **Rate limit:** 60 req/min
- **Returns:** LEI, legal name, jurisdiction, headquarters (city, country, region), status

### Backend

**New file:** `src/ti_radar/infrastructure/adapters/gleif_adapter.py`

```python
class GleifAdapter:
    BASE_URL = "https://api.gleif.org/api/v1"

    async def resolve_entity(self, name: str) -> dict[str, Any] | None:
        """Resolve a single entity name to GLEIF LEI record."""

    async def resolve_batch(self, names: list[str]) -> dict[str, dict[str, Any]]:
        """Resolve multiple names, using cache first."""
```

### Persistent Cache

**SQLite table `gleif_cache`** (in `patents.db`):

```sql
CREATE TABLE IF NOT EXISTS gleif_cache (
    raw_name TEXT PRIMARY KEY,
    lei TEXT,
    legal_name TEXT,
    country TEXT,
    city TEXT,
    resolved_at TEXT
);
```

- TTL: 90 days (check `resolved_at` before using cached entry)
- Lookup flow: check cache → if miss or expired → call API → write to cache
- Rate limiting: `asyncio.Semaphore(1)` + `asyncio.sleep(1.0)` between API calls

### Integration Points

| UC | How GLEIF enriches |
|----|-------------------|
| UC3 | Merge name variants ("SIEMENS AG" + "SIEMENS AKTIENGESELLSCHAFT" → one actor). Verified country for patent-only actors |
| UC6 | City-level data for patent applicants (currently only CORDIS orgs have city) |
| UC8 | Cleaner actor tracking (no false "new entrant" from name variants) |

### Graceful Degradation

- GLEIF resolution is a **post-processing enrichment**, not a dependency
- If API is down or rate-limited: skip, fall back to uppercased string matching (current behavior)
- Panel renders immediately with raw names, optional GLEIF enrichment applied when available
- First radar call for new technology: +5-10s for uncached actors. Subsequent calls: 0ms from cache

### Coverage Limitation

GLEIF covers ~2.5M legal entities. Universities and research institutes often lack LEIs. Resolution is best-effort — most effective for corporate actors (IBM, Siemens, Samsung, Bosch, etc.).

---

## 6. Dashboard Layout

### Panel Grid (8 panels, 2-column at md)

```
UC1 Landscape       | UC2 Maturity
UC3 Competitive     | UC4 Funding
UC6 Geographic      | UC7 Research Impact
UC8 Temporal (full width)
UC5 CPC Flow (full width)
```

Information hierarchy: overview (top) → deep analysis (bottom).

### API Integration

`radar.py` — extend `asyncio.gather()` from 5 to 8 parallel UCs:

```python
results = await asyncio.wait_for(
    asyncio.gather(
        analyze_landscape(...),
        analyze_maturity(...),
        analyze_competitive(...),      # includes GLEIF post-processing
        analyze_funding(...),
        analyze_cpc_flow(...),
        analyze_geographic(...),       # NEW
        analyze_research_impact(...),  # NEW (Semantic Scholar)
        analyze_temporal(...),         # NEW
        return_exceptions=True,
    ),
    timeout=30.0,
)
```

### Response Time Estimates

| Component | Current | After |
|-----------|---------|-------|
| Local SQLite (UC1-6, UC8) | ~60ms | ~80-100ms |
| OpenAIRE API (UC1) | ~500ms | ~500ms |
| Semantic Scholar API (UC7) | N/A | ~800-1500ms |
| GLEIF (UC3, cached) | N/A | 0ms |
| GLEIF (UC3, first time) | N/A | ~5-10s |
| **Total (cached)** | **~500ms** | **~1500ms** |

### Schema Addition to RadarResponse

```python
class RadarResponse(BaseModel):
    technology: str
    analysis_period: str
    maturity: MaturityPanel = MaturityPanel()
    landscape: LandscapePanel = LandscapePanel()
    competitive: CompetitivePanel = CompetitivePanel()
    funding: FundingPanel = FundingPanel()
    cpc_flow: CpcFlowPanel = CpcFlowPanel()
    geographic: GeographicPanel = GeographicPanel()          # NEW
    research_impact: ResearchImpactPanel = ResearchImpactPanel()  # NEW
    temporal: TemporalPanel = TemporalPanel()                # NEW
    explainability: ExplainabilityMetadata = ExplainabilityMetadata()
```

---

## 7. New Files Summary

| File | Type | Purpose |
|------|------|---------|
| `src/ti_radar/use_cases/geographic.py` | Backend | UC6 Geographic Intelligence |
| `src/ti_radar/use_cases/research_impact.py` | Backend | UC7 Research Impact |
| `src/ti_radar/use_cases/temporal.py` | Backend | UC8 Temporal Dynamics |
| `src/ti_radar/infrastructure/adapters/semantic_scholar_adapter.py` | Backend | Semantic Scholar API client |
| `src/ti_radar/infrastructure/adapters/gleif_adapter.py` | Backend | GLEIF API client + SQLite cache |
| `frontend/src/components/GeographicPanel.jsx` | Frontend | UC6 treemap + collaboration |
| `frontend/src/components/ResearchImpactPanel.jsx` | Frontend | UC7 citations + venues |
| `frontend/src/components/TemporalPanel.jsx` | Frontend | UC8 timeline + evolution |

Modified files: `schemas.py`, `radar.py`, `RadarGrid.jsx`, `config.py`, `patent_repo.py`, `cordis_repo.py`, `competitive.py`, `landscape.py`, `maturity.py`, `funding.py`

---

## 8. New Dependencies

| Dependency | Type | Already Available |
|------------|------|-------------------|
| Semantic Scholar API | External (free, no auth) | No — new adapter needed |
| GLEIF API | External (free, no auth, 60/min) | No — new adapter + cache needed |
| `httpx` | Python | Yes — already used for OpenAIRE |
| Recharts `Treemap` | npm | Yes — already in Recharts bundle |
| No new npm packages | — | All visualizations use existing libraries |
| No new Python packages | — | httpx + aiosqlite already available |

---

## 9. Test Strategy

| Test Type | Scope | Count (est.) |
|-----------|-------|-------------|
| Unit: geographic metrics | Cross-border %, country aggregation | ~10 |
| Unit: research impact metrics | h-index, avg citations, influential ratio, venue concentration | ~12 |
| Unit: temporal metrics | New entrant rate, persistence rate, technology breadth | ~10 |
| Unit: GLEIF cache | Cache hit/miss/expiry, name resolution | ~8 |
| Unit: Semantic Scholar parsing | Response parsing, pagination, error handling | ~8 |
| Integration: new repo methods | In-memory SQLite fixtures | ~12 |
| Integration: API endpoints | New panel fields in radar response | ~6 |
| **Total new tests** | | **~66** |
| **Existing tests** | | **228** |
| **Grand total** | | **~294** |
