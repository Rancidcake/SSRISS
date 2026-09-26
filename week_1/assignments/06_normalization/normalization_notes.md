# Assignment 06 — Normalization Notes

This document details the architectural assumptions, schema mappings, and boundary design decisions made in `normalizer.py`.

---

## Shared Schema Architecture

The normalization layer acts as a strict boundary contract between raw, source-specific website markup and standardized downstream database persistence.

```text
Raw Extracted Dict (scraper.py) ──> normalizer.py ──> Standard Schema (JSONL / SQLite)
```

---

## Detailed Normalizer Assumptions

### Assumption 1: Date String Format & Timezone Assumption (IST / UTC)
- **Observed Source Pattern:** JNU lists dates as `Mon, 07-09-2026` or `31-08-2026` (Day, DD-MM-YYYY format).
- **Normalizer Assumption:** The normalizer assumes that two-digit date strings separated by hyphens represent `DD-MM-YYYY` rather than `MM-DD-YYYY` (standard for Indian academic institutions).
- **Timezone:** Standard publication dates on JNU notices carry no explicit UTC offset. The normalizer assigns IST (`+05:30`) context to the `fetched_at` timestamp.

### Assumption 2: Item Classification via URL Extension
- **Normalizer Assumption:** If an `item_url` string ends with `.pdf` or contains `.pdf`, the item is classified as `item_type: "pdf_notice"`. All other URLs are classified as `item_type: "html_notice"`.
- **Failure Mode & Safeguard:** If JNU serves a PDF notice via a dynamic parameter path (e.g. `download.php?id=123` without `.pdf` extension), the normalizer defaults to `"html_notice"` until a HEAD request content-type check is introduced.

### Assumption 3: Missing Fields and Scalar vs List Fields
- **Normalizer Assumption:** Fields not present on the listing table surface (like `speaker_raw` or `location_raw`) are set to empty structures:
  - `location`: `None` (scalar string or null)
  - `speakers`: `[]` (list of strings)
  - `organizations`: `["Jawaharlal Nehru University"]` (default institutional authority)
- **Provenance Retention:** Both `raw_text` and `date_raw` are preserved verbatim to ensure auditability and debugging back to raw HTML.

---

## Checkpoint Question Answer

> **Question:** If the institution changes how it displays dates tomorrow, which function should ideally change: HTTP fetching, parsing, normalization, or database storage?

**Answer:** **Only the `normalization` function (`parse_date_to_iso` inside `normalizer.py`) should change.**

### Architectural Rationale:
1. **HTTP Fetching (`fetch`)**: Handles network communication, timeouts, and user agents. It remains unaffected by UI formatting changes.
2. **Parsing (`parse_items`)**: Responsible only for extracting raw strings from DOM selectors as they appear on the page (`date_raw`). If the date selector remains unchanged, parsing code does not need modification.
3. **Database Storage (`upsert_item`)**: Expects clean, validated ISO 8601 string inputs matching the standard table schema.
4. **Normalization (`normalize_item`)**: Is explicitly designed to encapsulate UI formatting variability and translate raw strings (`date_raw`) into canonical standardized representations (`event_start`). Decoupling normalization isolates site changes to a single function.
