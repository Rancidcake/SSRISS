# Week 3 Integration Assignment: High-Yield Central Aggregator & Entity Extraction

**Intern:** Mayank  
**Primary Institution:** Jawaharlal Nehru University (JNU), New Delhi (`https://www.jnu.ac.in`)  
**Aggregator Target:** JNU Central Events & Seminars Portal (`/jnuevents` & `/events-archive`)  
**Framework Status:** Production-grade, bounded, monitored aggregator with 69 unit/integration tests passing.  

---

## 1. Executive Summary & Pipeline Topology

Week 3 shifts the monitoring architecture from individual departmental scrapers to a **high-yield central aggregator** that discovers, filters, classifies, relationally models, and observes campus updates across multiple university schools and autonomous research units.

The completed end-to-end pipeline implements the following deterministic architecture:

```text
SOURCE CONFIG 
     ↓ [Base URL, Allowed Subdomains, Ceilings, Rate Limits]
SCHEDULED RUN 
     ↓ [Run metadata, timestamps, audit logging]
DISCOVERY ADAPTER 
     ↓ [HTML/RSS/Sitemap normalization into DiscoveredItem]
SCOPE CONTROL 
     ↓ [Regex allow/deny, canonicalization, trap prevention]
NEW / CHANGED ITEM CANDIDATES 
     ↓ [SHA-256 content hashes, first_seen_at / last_seen_at]
FETCH + PARSE 
     ↓ [DOM extraction of structured cards/detail pages]
NORMALIZE 
     ↓ [Clean whitespace, absolute URLs, ISO-8601 timestamps]
EXPLICIT ENTITY EXTRACTION 
     ↓ [Conservative regex parsing, raw provenance preserved]
ITEM + ENTITY RELATIONSHIPS 
     ↓ [Normalized items, people, organizations, join tables]
DATABASE (SQLite)
     ↓ [ACID transactions, foreign keys, composite unique constraints]
HEALTH / COVERAGE SUMMARY 
     ↓ [Diagnostic metrics, coverage %, parser health diagnosis]
```

### Pipeline Execution Stages

1. **SOURCE CONFIG:** Defines host allowlists (`www.jnu.ac.in`), allowed path prefixes (`/node`, `/jnuevents`, `/events-archive`), denylist rules (`/user`, `/login`, `/admin`, `/calendar`), and crawl ceilings (maximum 30 items, 3 pages).
2. **SCHEDULED RUN:** Coordinates invocation cycles with ISO-8601 UTC timestamps and audit logging.
3. **DISCOVERY ADAPTER:** Ingests HTML listings, RSS 2.0 feeds, and XML sitemaps, emitting uniform `DiscoveryRecord` objects.
4. **SCOPE CONTROL:** Enforces canonicalization (lowercasing host, stripping fragments `#...`, stripping marketing query parameters `utm_*`, `fbclid`), blocks binary assets (`.pdf`, `.zip`), and drops calendar navigation traps (`?month=`, `year=`).
5. **INCREMENTAL CHANGE DETECTION:** Computes SHA-256 cryptographic hashes over normalized semantic fields (excluding volatile timestamps and shifting table counters); classifies candidates into `NEW`, `CHANGED`, `UNCHANGED`, and tracks `NOT_SEEN_THIS_RUN` without destructive deletion.
6. **CONTENT ROUTER:** Classifies candidate items into `event`, `announcement`, `faculty`, `pdf_document`, `external_link`, or `unknown` based on structural evidence without topic bias. Preserves unknown types in discovery logs.
7. **EXPLICIT ENTITY EXTRACTION:** Extracts people (speakers, chairs, moderators, panelists) and organizations (departments, schools, societies) strictly from explicit surface field markers with verbatim `source_text` provenance.
8. **RELATIONAL STORAGE:** Maps events, people, and organizations into normalized relational tables (`items`, `people`, `organizations`, `item_people`, `item_organizations`) with composite unique keys.
9. **HEALTH & COVERAGE OBSERVABILITY:** Generates structured run metrics (items discovered, parsed, new, changed, unchanged, failed) and coverage percentages (dates, speakers, organizations), diagnosing operational status (Healthy vs Broken Parser vs Inactive Source).

---

## 2. Deliverables Matrix (All 16 Requirements)

| # | Deliverable | Location | Description |
|---|---|---|---|
| **1** | **Aggregator Candidate Matrix** | [`assignments/00_candidates/jnu_aggregators.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/00_candidates/jnu_aggregators.md) | Evaluates 3 institutional surfaces (JNU Events, JNU Notices, Departmental Faculty Page) across yield, structure, updates, and accessibility. |
| **2** | **Chosen Source Rationale** | [`assignments/00_candidates/jnu_aggregators.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/00_candidates/jnu_aggregators.md) | Criteria-based justification for selecting JNU Central Events (`/jnuevents`) as primary target. |
| **3** | **Feed/Sitemap/Listing Discovery** | [`assignments/01_discovery/findings.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/01_discovery/findings.md)<br>[`assignments/01_discovery/unified_discovery.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/01_discovery/unified_discovery.py) | Inspection scripts (`inspect_feed.py`, `inspect_sitemap.py`) and unified multi-format discovery engine with local fixtures. |
| **4** | **URL Scope Rules** | [`assignments/02_scope/scope_cases.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/02_scope/scope_cases.md)<br>[`assignments/02_scope/scope_filter.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/02_scope/scope_filter.py) | Host boundary validation, path allow/denylists, tracking-parameter stripping, binary filters, and trap guards. |
| **5** | **Discovery Adapter** | [`assignments/03_interface/aggregator_discovery.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/03_interface/aggregator_discovery.py) | `BaseDiscoveryAdapter` and concrete adapters emitting canonical discovery records. |
| **6** | **Incremental Collection & Change Detection** | [`assignments/04_incremental/run_state_notes.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/04_incremental/run_state_notes.md)<br>[`assignments/04_incremental/incremental_store.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/04_incremental/incremental_store.py) | Cryptographic SHA-256 content hashing, lifecycle timestamps (`first_seen_at`, `last_seen_at`), and `not_seen_this_run` semantics without deletion. |
| **7** | **Content Router** | [`assignments/08_routing/router_notes.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/08_routing/router_notes.md)<br>[`assignments/08_routing/content_router.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/08_routing/content_router.py) | Structural classification into `event`, `announcement`, `faculty`, `pdf_document`, `external_link`, `unknown` without topic bias. |
| **8** | **Detail Parser** | [`assignments/10_adapter/central_aggregator_adapter.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/10_adapter/central_aggregator_adapter.py) | Dedicated event item parsing logic extracting title, date, venue, abstract, speaker, and organizer sections. |
| **9** | **Person Entity Extraction** | [`assignments/05_extraction/extraction_notes.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/05_extraction/extraction_notes.md)<br>[`assignments/05_extraction/entity_extractor.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/05_extraction/entity_extractor.py) | Parses speakers, chairs, panelists, and raw affiliations strictly from explicit text with verbatim provenance. |
| **10** | **Organization Entity Extraction** | [`assignments/05_extraction/extraction_notes.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/05_extraction/extraction_notes.md)<br>[`assignments/05_extraction/entity_extractor.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/05_extraction/entity_extractor.py) | Extracts schools, centres, and partner organizations without inferring unstated affiliations. |
| **11** | **Entity Relationship Schema** | [`assignments/06_entities/entity_schema.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/06_entities/entity_schema.md)<br>[`assignments/06_entities/entity_relational_store.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/06_entities/entity_relational_store.py) | Relational SQLite schema with composite keys `(item_id, person_id, role)` and index-backed checkpoint queries. |
| **12** | **Tests and Fixtures** | All `assignments/*/test_*.py` and `fixtures/` | 10 independent test suites with offline HTML/RSS/XML/JSON fixtures covering 69 test cases with 100% pass rate. |
| **13** | **Logs** | [`assignments/10_adapter/aggregator.log`](file:///home/kresler/Documents/SSRISS/week_3/assignments/10_adapter/aggregator.log)<br>[`assignments/12_integration/integration_run.log`](file:///home/kresler/Documents/SSRISS/week_3/assignments/12_integration/integration_run.log) | Structured audit log records with timestamps, log levels, run phases, scope decisions, and extraction counts. |
| **14** | **Run Metrics** | [`assignments/09_metrics/run_summary_notes.md`](file:///home/kresler/Documents/SSRISS/week_3/assignments/09_metrics/run_summary_notes.md)<br>[`assignments/09_metrics/run_summary.py`](file:///home/kresler/Documents/SSRISS/week_3/assignments/09_metrics/run_summary.py) | Structured run health summary distinguishing healthy steady-state runs from broken parsers. |
| **15** | **README** | [`week_3/README.md`](file:///home/kresler/Documents/SSRISS/week_3/README.md) | This complete integration guide, architectural breakdown, and execution documentation. |
| **16** | **Peer-Review Notes** | [`week_3/peer_review_notes.md`](file:///home/kresler/Documents/SSRISS/week_3/peer_review_notes.md) | Paired architectural review of Saanvi's IIMA aggregator addressing all 10 syllabus review questions. |

---

## 3. Quickstart & Verification Commands

### Run End-to-End Integration Demonstration
Executes a two-phase ingestion cycle (initial ingestion followed by incremental re-crawl) and prints relational queries:
```bash
.venv/bin/python week_3/assignments/12_integration/run_integration.py
```

### Run Entire Week 3 Automated Test Suite
Executes all 69 unit and integration test suites:
```bash
.venv/bin/python -m pytest week_3/assignments/ -v
```

---

## 4. Key Architectural Safeguards

1. **Conservative Entity Resolution (False Split Over False Merge):**
   - Weak similarity (e.g., `A. Rao` vs `Prof. Ananya Rao`) is classified as `possible match requiring review` and never merged automatically into an authoritative identity claim.
   - Punctuation, honorific variants (`Dr.`, `Prof.`, `Amb.`), and case-insensitive matching are permitted for deduplication, but surname/initial overlaps require human confirmation.
2. **Listing Disappearance != Deletion:**
   - When an event is no longer visible on the immediate listing, its database record is retained and tagged with `not_seen_this_run`. Deletion is never inferred without stronger evidence.
3. **Bounded Frontier Ceilings:**
   - In accordance with the assignment guidelines, the crawler enforces hard ceilings (`max_items: 30`, `max_pages: 3`) to prove architecture without scraping entire university archives.
4. **Observable Operational Health:**
   - If a page is fetched but returns zero parsed items, the system raises `CRITICAL: Broken parser suspected` rather than silently reporting zero updates.
