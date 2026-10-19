# Week 3 Peer-Review: Saanvi's IIMA Central Aggregator

**Reviewer:** Mayank (SSRISS Intern — JNU Monitor)  
**Author Under Review:** Saanvi (SSRISS Intern — IISER Pune / IIMA Aggregator)  
**Target Under Review:** Indian Institute of Management Ahmedabad (`https://www.iima.ac.in/the-institute/events`)  
**Repository Location Reviewed:** `SSRISS_ASSIGNMENTS/Week_3`  
**Date:** October 2026  

---

## 1. Executive Summary & Review Scope

As part of the Week 3 paired review (**Saanvi ↔ Mayank**), I conducted an in-depth architectural and code review of Saanvi's central aggregator implementation for the Indian Institute of Management Ahmedabad (IIMA). 

Saanvi transitioned from her primary assigned institution (IISER Pune) to IIMA after discovering that IISER Pune's public event updates were heavily locked inside binary image posters and unstructured PDFs without a stable central listing. IIMA proved to be a model high-yield aggregator candidate, exposing structured semantic HTML cards for executive seminars, academic conferences, and research talks across multiple management centers.

The audit evaluates the implementation across all ten review questions specified in Section 11 of the Week 3 syllabus, concluding with three substantive technical recommendations.

---

## 2. Technical Evaluation against the 10 Syllabus Review Questions

### Question 1: Is the target genuinely high-yield?
**Assessment: YES (Outstanding Selection)**  
- *Analysis:* Saanvi's choice of `https://www.iima.ac.in/the-institute/events` is a quintessential high-yield surface. Rather than crawling isolated faculty directories or departmental subdomains, this single endpoint aggregates public lectures, management symposiums, and research workshops from across IIMA's centers (e.g., Centre for Management in Agriculture, Centre for Innovation Incubation and Entrepreneurship, Ashank Desai Centre for IT and Networked Economy). A single crawl provides institution-wide visibility.

### Question 2: Is scope clearly bounded?
**Assessment: YES (Strictly Enforced)**  
- *Analysis:* In [`02_scope/scope_filter.py`](file:///home/kresler/Downloads/SSRISS_ASSIGNMENTS-main/Week_3/assignments/02_scope/scope_filter.py), `UrlScopeFilter` bounds the crawl frontier to `allowed_hostname="www.iima.ac.in"` and allowed path prefixes `["/the-institute/events", "/news"]`. It explicitly excludes `/calendar`, `/search`, `/filter`, `/login`, and binary asset directories (`/sites/default/files`). Off-domain links are rejected (`allow_external=False`).

### Question 3: Could pagination loop indefinitely?
**Assessment: NO (Safe Bounded Traversal)**  
- *Analysis:* The adapter enforces both a hard pagination ceiling (`max_pages=3`) and a discovery item ceiling (`max_items=30`). Furthermore, the scope filter denies calendar parameter traps (e.g., query strings containing `month=`, `year=`, or `filter=`), preventing infinite calendar loops.

### Question 4: Are feeds/sitemaps treated as discovery rather than complete truth?
**Assessment: YES (Strict Layer Separation)**  
- *Analysis:* In [`01_discovery/unified_discovery.py`](file:///home/kresler/Downloads/SSRISS_ASSIGNMENTS-main/Week_3/assignments/01_discovery/unified_discovery.py), RSS feeds and XML sitemaps emit `DiscoveryRecord` tuples containing only candidate URLs and timestamps. They are treated strictly as pointers to frontier candidates. Full semantic records are extracted only in downstream detail parsing.

### Question 5: Are item URLs canonicalized consistently?
**Assessment: YES (Robust Normalization)**  
- *Analysis:* URL canonicalization lowercases the scheme and netloc, strips fragment anchors (`#...`), and eliminates marketing tracking parameters (`utm_source`, `utm_medium`, `fbclid`, `gclid`, `ref`). This guarantees that duplicate links with differing query tracking parameters map to the identical canonical database key.

### Question 6: Is a missing field handled without crashing?
**Assessment: YES (Graceful Degradation)**  
- *Analysis:* In [`05_extraction/entity_extractor.py`](file:///home/kresler/Downloads/SSRISS_ASSIGNMENTS-main/Week_3/assignments/05_extraction/entity_extractor.py), when optional fields (e.g., raw affiliation, chair name) are omitted on an event card, the fields gracefully resolve to `None` / `null` rather than throwing `AttributeError` or `KeyError`.

### Question 7: Are speakers/organizations supported by source text?
**Assessment: YES (Auditable Provenance)**  
- *Analysis:* Every extracted person and organization entity retains its verbatim `source_text` provenance attribute pointing directly to the exact HTML text line that justified the entity's extraction. No affiliations or ideologies are inferred.

### Question 8: Are uncertain identities merged too aggressively?
**Assessment: YES (Conservative Resolution Invariant)**  
- *Analysis:* In [`07_resolution/entity_matcher.py`](file:///home/kresler/Downloads/SSRISS_ASSIGNMENTS-main/Week_3/assignments/07_resolution/entity_matcher.py), Saanvi strictly enforces **False Split over False Merge**. Ambiguous initial-only matches (e.g., "A. Rao" vs "Prof. Ananya Rao") are flagged as `possible match requiring review` and never merged automatically.

### Question 9: Can you tell from logs whether zero new items means "nothing new" or "parser broken"?
**Assessment: YES (Distinct Diagnostic Signals)**  
- *Analysis:* In [`09_metrics/run_summary.py`](file:///home/kresler/Downloads/SSRISS_ASSIGNMENTS-main/Week_3/assignments/09_metrics/run_summary.py), the `diagnose_health()` method clearly distinguishes:
  - `HEALTHY: Source active (steady state, all unchanged)` when `pages_fetched > 0` and `unchanged > 0`.
  - `CRITICAL: Broken parser suspected` when `pages_fetched > 0` but `items_parsed == 0`.

### Question 10: Could this adapter run repeatedly without duplicating records?
**Assessment: YES (Deterministic Idempotency)**  
- *Analysis:* In [`04_incremental/incremental_store.py`](file:///home/kresler/Downloads/SSRISS_ASSIGNMENTS-main/Week_3/assignments/04_incremental/incremental_store.py), stable SHA-256 content hashes computed over sorted, non-volatile semantic fields allow repeated runs to correctly flag existing items as `UNCHANGED` without inserting duplicate rows.

---

## 3. Substantive Technical Review Comments & Recommendations

### Comment 1: Acronym Extraction Boundary in Organization Normalization
- **Observation:** In `entity_matcher.py`, `_normalize_org` extracts parenthetical acronyms using the regex `r"\(([^)]+)\)$"`. If an organization string contains an explanatory parenthetical note rather than an acronym (e.g., `"Centre for Innovation (Main Campus)"`), the code checks `if len(inner) <= 6 and inner.isalpha():`.
- **Potential Edge Case:** While `len <= 6` prevents long descriptions from matching, a city abbreviation or 4-letter word in parentheses (e.g., `"Department of Economics (Pune)"` or `"(East)"`) could be misclassified as an acronym `pune` or `east`.
- **Recommendation:** Add an additional heuristic verifying that the extracted acronym string actually matches the computed initialism of the preceding organization title, or check against a known whitelist of institutional acronyms.

### Comment 2: Handling Subdomain Variations for Institutional Landing Pages
- **Observation:** In `scope_filter.py`, the `allowed_hostname` is hard-coded to `"www.iima.ac.in"`.
- **Potential Issue:** Like JNU (`jnu.ac.in` vs `www.jnu.ac.in`), IIMA frequently hosts specialized research centers or conferences on subdomains (e.g., `ciie.iima.ac.in` or `execed.iima.ac.in`). If central events link directly to these center subdomains, the current strict hostname check will reject them.
- **Recommendation:** Introduce an `allowed_subdomains: bool` flag or allow wildcard regexes (e.g., `r"^([a-z0-9-]+\.)?iima\.ac\.in$"`) to permit legitimate on-campus research center subdomains while continuing to block off-domain links.

### Comment 3: Incremental State Table Integration
- **Observation:** In Assignment 10 (`CentralAggregatorAdapter`), incremental hashes are tracked in a dedicated table `item_hashes` initialized inside the relational store connection.
- **Commendation:** This clean architectural separation keeps relational entity data (`items`, `people`, `organizations`) pristine while maintaining cryptographic change-detection state in a lightweight companion table. The two-phase run demonstration (`run_integration.py`) cleanly proves zero database churn during steady-state monitoring.

---

## 4. Overall Peer Review Conclusion

Saanvi's Week 3 submission is an exceptional piece of data engineering. The codebase is thoroughly tested (160+ unit tests), strictly obeys the conservative entity resolution guidelines, and provides crystal-clear observability for operational monitoring. All required deliverables and architectural invariants have been comprehensively met.
