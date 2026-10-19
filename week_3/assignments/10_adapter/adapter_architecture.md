# Central Aggregator Architecture & Pipeline Design

**Author:** Mayank (SSRISS Intern)  
**Target:** Central Aggregator Architecture (JNU)  
**Assignment:** Assignment 10 — Central Aggregator Adapter  
**Date:** October 2026  

---

## 1. End-to-End Pipeline Architecture

The Central Aggregator synthesizes the entire Week 3 roadmap into a unified, deterministic pipeline:

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
DATABASE 
     ↓ [SQLite with foreign keys and composite unique keys]
HEALTH / COVERAGE SUMMARY 
     ↓ [Diagnostic metrics, coverage %, parser health diagnosis]
```

---

## 2. Component Synergy & Bounded Scope

1. **Discovery Interface (`aggregator_discovery.py`):**
   - Ingests HTML table listings, RSS 2.0 feeds, and XML sitemaps.
   - Emits uniform `DiscoveryRecord` dictionaries.
2. **Scope Filter (`scope_filter.py`):**
   - Canonicalizes URLs: lowercases scheme and host, normalizes `jnu.ac.in` to `www.jnu.ac.in`, strips fragments and tracking query params (`utm_*`, `fbclid`).
   - Traps blocked: rejects calendar loops (`?month=`), login/admin pages (`/user/login`), and binary assets (`.pdf`, `.zip`).
3. **Ceiling Controls:**
   - In strict compliance with Assignment 10, the crawl ceiling is bounded to **20–40 items** (default 30) or **2–5 pages** (default 3) to prevent unbounded crawl explosions.
4. **Content Classification (`content_router.py`):**
   - Directs discovered URLs into `event`, `announcement`, `faculty`, `pdf_document`, `external_link`, or `unknown`.
   - Preserves unknown types in discovery logs rather than forcing them into the wrong database schema.
5. **Explicit Entity Extraction (`entity_extractor.py`):**
   - Extracts speakers, chairs, and organizing departments strictly from unambiguous field markers and title structures.
   - Preserves exact `source_text` provenance for every extracted entity.
6. **Relational Database (`entity_relational_store.py`):**
   - Persists normalized entities into `people` and `organizations` tables.
   - Creates many-to-many relationships in `item_people` and `item_organizations` using composite unique constraints.
7. **Incremental Change Detection (`incremental_store.py`):**
   - Compares SHA-256 cryptographic hashes over normalized semantic fields.
   - Excludes volatile attributes (`fetched_at`, serial counters).
   - Preserves items absent from current listing as `not_seen_this_run` without deletion.
8. **Observability & Metrics (`run_summary.py`):**
   - Records items discovered, parsed, new, changed, unchanged, and failed.
   - Computes coverage percentages for dates, speakers, and organizations.
   - Distinguishes "source had no new content" from "parser broke".
