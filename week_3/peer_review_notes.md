# Week 3 Peer Review: Saanvi's IIMA Central Aggregator

**Reviewer:** Mayank (SSRISS Intern – JNU Monitor)  
**Author:** Saanvi (SSRISS Intern – IISER Pune / IIMA Aggregator)  
**Target:** Indian Institute of Management Ahmedabad (IIMA)  
**Target URL:** https://www.iima.ac.in/the-institute/events  
**Repository:** `SSRISS_ASSIGNMENTS/Week_3`  
**Date:** October 2026

## 1. Overview

For the Week 3 peer review , I reviewed Saanvi's central aggregator implementation for IIM Ahmedabad.

Saanvi initially worked on IISER Pune but switched to IIMA after finding that many IISER Pune event announcements were published as image posters or PDFs, making them difficult to collect consistently. IIMA's central events page was a more suitable choice because it provides a single place to find information about seminars, conferences, research talks and other academic events.

The review covers all 10 questions from Section 11 of the Week 3 syllabus, followed by three technical comments on the implementation.

## 2. Review Against the 10 Syllabus Questions

### Question 1: Is the target genuinely high-yield?

**Assessment: Yes**

The IIMA events page is a good choice for a central aggregator. It brings together events from different parts of the institute, including public lectures, research seminars, workshops and management conferences. This means the crawler can discover events from multiple centres without having to start from separate departmental pages.

### Question 2: Is the scope clearly bounded?

**Assessment: Yes**

In `02_scope/scope_filter.py`, the `UrlScopeFilter` restricts crawling to `www.iima.ac.in` and the allowed paths `/the-institute/events` and `/news`.

It also excludes paths such as `/calendar`, `/search`, `/filter`, `/login` and `/sites/default/files`. External links are rejected because `allow_external=False`.

This keeps the crawler focused on relevant institute pages instead of allowing it to follow unrelated links.

### Question 3: Could pagination continue indefinitely?

**Assessment: No, based on the configured limits**

The adapter sets `max_pages=3` and `max_items=30`, which limits the number of pages and discovered items it can process. The scope filter also blocks certain calendar-related query parameters, including `month=`, `year=` and `filter=`.

These restrictions reduce the risk of the crawler getting stuck in repetitive pagination or calendar URLs.

### Question 4: Are feeds and sitemaps used for discovery rather than treated as complete data sources?

**Assessment: Yes**

In `01_discovery/unified_discovery.py`, RSS feeds and XML sitemaps produce `DiscoveryRecord` entries containing candidate URLs and timestamps.

These records are used to identify pages for further processing. The actual event details are extracted later by the relevant parsing components. This keeps discovery separate from extraction.

### Question 5: Are item URLs canonicalized consistently?

**Assessment: Yes**

The URL normalization logic lowercases the scheme and hostname, removes fragments and strips common tracking parameters such as `utm_source`, `utm_medium`, `fbclid`, `gclid` and `ref`.

This helps prevent the same page from being stored multiple times just because it was reached through links with different tracking parameters.

### Question 6: Does the extractor handle missing fields without crashing?

**Assessment: Yes**

In `05_extraction/entity_extractor.py`, optional fields such as affiliation or chair name can be missing without causing an exception. These fields resolve to `None` or `null` where appropriate.

This is useful because event pages do not always follow the same format or provide every detail.

### Question 7: Are extracted speakers and organizations supported by source text?

**Assessment: Yes**

The implementation stores a `source_text` attribute for extracted person and organization entities. This allows a reviewer to trace an extracted entity back to the text used to identify it.

The approach also avoids adding unsupported details about a person's affiliation or background.

### Question 8: Does entity resolution avoid merging uncertain identities?

**Assessment: Yes**

In `07_resolution/entity_matcher.py`, the matching logic follows a conservative approach that favours a possible false split over an incorrect merge.

For example, a name such as "A. Rao" is not automatically merged with "Prof. Ananya Rao" when the available information is insufficient. Such cases are flagged for manual review.

This is appropriate for an academic event aggregator, where different people may have similar names.

### Question 9: Can the logs distinguish between no new events and a broken parser?

**Assessment: Yes**

In `09_metrics/run_summary.py`, the `diagnose_health()` method uses the run statistics to identify different outcomes.

- `HEALTHY: Source active (steady state, all unchanged)` is reported when pages have been fetched and existing items are unchanged.
- `CRITICAL: Broken parser suspected` is reported when pages have been fetched but no items were parsed.

This distinction helps when checking whether the source has simply not changed or whether the extraction process needs attention.

### Question 10: Can the adapter run repeatedly without creating duplicate records?

**Assessment: Yes**

In `04_incremental/incremental_store.py`, the implementation uses SHA-256 hashes calculated from sorted, non-volatile semantic fields.

When an item has not changed, its hash remains the same and the record can be marked `UNCHANGED` rather than inserted again. The two-run demonstration in `run_integration.py` also shows how the adapter handles repeated runs.

## 3. Technical Comments and Recommendations

### Comment 1: Improving acronym detection in organization names

In `entity_matcher.py`, the `_normalize_org` method uses the regular expression `r"\(([^)]+)\)$"` to identify text inside parentheses at the end of an organization name.

The current check, `len(inner) <= 6 and inner.isalpha()`, helps identify short acronyms. However, it could also classify words such as "Pune" or "East" as acronyms in names like "Department of Economics (Pune)" or "Centre for Research (East)".

I suggest checking whether the text in parentheses matches the initials of the organization name. Another option is to compare it against a list of known institutional acronyms. Either approach would reduce incorrect organization matches.

### Comment 2: Handling institutional subdomains

In `scope_filter.py`, the allowed hostname is set to `www.iima.ac.in`.

This is restrictive if an event on the main IIMA website links to a legitimate research centre or conference hosted on a subdomain, such as `ciie.iima.ac.in` or `execed.iima.ac.in`. These URLs would be rejected under the current hostname rule.

I suggest adding an option to allow approved subdomains. For example, a hostname rule could accept `iima.ac.in` and its subdomains while continuing to reject unrelated domains.

The implementation should still apply the path and URL restrictions to prevent the crawler from expanding beyond the intended scope.

### Comment 3: Incremental state storage

In Assignment 10, `CentralAggregatorAdapter` tracks content hashes in a separate `item_hashes` table within the relational store.

I think keeping the hash state separate from the main `items`, `people` and `organizations` tables is a sensible design choice. It keeps change-detection data separate from the extracted records.

The two-run demonstration in `run_integration.py` is also useful for checking whether the adapter correctly identifies unchanged items on subsequent runs.

## 4. Overall Conclusion

Overall, Saanvi's submission addresses all 10 Week 3 review questions. The implementation has clear crawl limits, separates discovery from extraction, handles missing fields and uses conservative entity matching. Its incremental hashing and run diagnostics are also useful for repeated monitoring.

My main suggestions are to improve acronym detection, make the hostname rules configurable for approved IIMA subdomains and continue testing the incremental state handling across repeated runs.

The submission reports more than 160 unit tests. These provide a useful basis for checking the implementation, alongside the integration test and the three improvements noted above.
