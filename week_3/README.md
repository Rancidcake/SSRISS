# Week 3 Integration Assignment: High-Yield Central Aggregator & Entity Extraction

**Intern:** Mayank  
**Primary Institution:** Jawaharlal Nehru University (JNU), New Delhi (`https://www.jnu.ac.in`)  
**Aggregator Target:** JNU Central Events & Seminars Portal (`/jnuevents` & `/events-archive`)  
**Framework Status:** Production-grade, bounded, monitored aggregator with 69 unit/integration tests passing.  

---

## 1. Brief Summary & Pipeline Topology

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



## 2. Quickstart & Verification Commands

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

## 3. Key Architectural Safeguards

1. **Conservative Entity Resolution (False Split Over False Merge):**
   - Weak similarity (e.g., `A. Rao` vs `Prof. Ananya Rao`) is classified as `possible match requiring review` and never merged automatically into an authoritative identity claim.
   - Punctuation, honorific variants (`Dr.`, `Prof.`, `Amb.`), and case-insensitive matching are permitted for deduplication, but surname/initial overlaps require human confirmation.
2. **Listing Disappearance != Deletion:**
   - When an event is no longer visible on the immediate listing, its database record is retained and tagged with `not_seen_this_run`. Deletion is never inferred without stronger evidence.
3. **Bounded Frontier Ceilings:**
   - In accordance with the assignment guidelines, the crawler enforces hard ceilings (`max_items: 30`, `max_pages: 3`) to prove architecture without scraping entire university archives.
4. **Observable Operational Health:**
   - If a page is fetched but returns zero parsed items, the system raises `CRITICAL: Broken parser suspected` rather than silently reporting zero updates.
