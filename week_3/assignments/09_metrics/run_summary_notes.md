# Source Health & Coverage Metrics — Diagnostic Notes

**Author:** Mayank (SSRISS Intern)  
**Target:** Central Aggregator Health Observability (JNU)  
**Assignment:** Assignment 9 — Run Summary  
**Date:** October 2026  

---

## 1. Operational Diagnostic Distinction

A monitoring system must answer a fundamental question after every scheduled execution:
> **Did the monitor find nothing because nothing happened, or because the scraper broke?**

### The Critical Distinguishing Metrics

```text
Scenario A: Steady State (Quiet Holiday / No New Events)
PAGES_FETCHED: 2
ITEMS_DISCOVERED: 24
ITEMS_PARSED: 24
NEW: 0
CHANGED: 0
UNCHANGED: 24
FAILED: 0
STATUS: HEALTHY: Source active (steady state, all unchanged)

Scenario B: Catastrophic Parser Failure (CMS Redesign / CSS Changed)
PAGES_FETCHED: 2
ITEMS_DISCOVERED: 0
ITEMS_PARSED: 0
NEW: 0
CHANGED: 0
UNCHANGED: 0
FAILED: 0
STATUS: CRITICAL: Broken parser suspected (zero items discovered from fetched pages)
```

In Scenario A, `PAGES_FETCHED > 0`, `ITEMS_PARSED > 0`, and `UNCHANGED == 24`. The system knows that the HTML DOM structure was intact and matched the expected CSS selectors. Zero `NEW` items is normal behavior during weekends or academic breaks.

In Scenario B, `PAGES_FETCHED > 0` but `ITEMS_DISCOVERED == 0` or `ITEMS_PARSED == 0`. The health diagnosis immediately flags `CRITICAL: Broken parser suspected`. An engineer is alerted to inspect the site for layout modifications.

---

## 2. Qualitative Coverage Metrics

Counting rows is insufficient to detect silent data degradation. A website redesign might keep the top-level table structure intact while changing the markup for speaker names, turning `<td>Dr. Divya P. Kumar</td>` into an unparsed `<div>`.

Our `RunMetrics` engine computes three qualitative coverage ratios:
1. **`COVERAGE_DATE` (% of parsed items with valid ISO timestamp):**
   - Expected: > 90%.
   - If coverage drops to 20%, the date parsing regex or selector broke.
2. **`COVERAGE_SPEAKER` (% of events with explicit speaker extracted):**
   - Expected: 40% – 80% on academic lecture listings.
   - If coverage falls to 0%, the speaker field marker pattern has drifted.
3. **`COVERAGE_ORGANIZATION` (% of events with organizing unit extracted):**
   - Expected: > 75%.
   - If coverage collapses, department/school extraction is failing.

---

## 3. Deliberate Failure Injection Verification

To test our diagnostic reporting, we executed the pipeline against `fixtures/broken_events.html` (simulating a Drupal 500 error and missing view container). The resulting metrics:
```text
SOURCE: jnu_events_broken_demo
PAGES_FETCHED: 1
ITEMS_DISCOVERED: 0
ITEMS_PARSED: 0
NEW: 0
CHANGED: 0
UNCHANGED: 0
FAILED: 0
STATUS: CRITICAL: Broken parser suspected (zero items discovered or parsed from fetched pages)
```
The failure is instantly obvious in logs and database audit tables, proving our metric reporting fulfills Assignment 9 requirements.
