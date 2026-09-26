# Assignment 07 — Persistence & Deduplication Experiment Log

This document records the design, empirical experiment outputs, and architectural analysis for SQLite persistence and content-hash deduplication (`storage.py`).

---

## 1. Database Table Schema

Database Engine: SQLite 3  
Database Path: `assignments/07_storage/jnu_monitor.db`  
Table Name: `monitored_items`

```sql
CREATE TABLE IF NOT EXISTS monitored_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_url TEXT UNIQUE NOT NULL,
    source_name TEXT,
    item_type TEXT,
    title TEXT,
    event_start TEXT,
    raw_text TEXT,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_item_url ON monitored_items(item_url);
```

---

## 2. Experimental Verification Runs

### Run 1 — Initial Database Population
- **Input:** 50 normalized JSONL records from `jnu_normalized.jsonl`.
- **Database State Before Run:** Empty table.
- **Execution Output:**
  ```text
  RUN 1 RESULTS:
  - Inserted:  50 records
  - Updated:   0 records
  - Unchanged: 0 records
  ```
- **Observations:** 50 new records successfully inserted with identical `first_seen_at` and `last_seen_at` timestamps.

### Run 2 — Immediate Rerun (Idempotency Check)
- **Input:** Same 50 normalized JSONL records.
- **Execution Output:**
  ```text
  RUN 2 RESULTS:
  - Inserted:  0 records
  - Updated:   0 records
  - Unchanged: 50 records
  ```
- **Observations:** Zero duplicate rows created. All 50 existing records matched on `item_url` and `content_hash`. The system updated `last_seen_at` while preserving `first_seen_at`.

### Run 3 — Modified Record Test (Content Change Detection)
- **Input:** Single item modified with updated title: `"Circular regarding holiday on 11.09.2026 [CORRIGENDUM ADDED]"`.
- **Execution Output:**
  ```text
  RUN 3 RESULTS:
  - Status Returned: 'updated'
  - Updated Title:   Circular regarding holiday on 11.09.2026 [CORRIGENDUM ADDED]
  - DB Action:       Content hash updated, last_seen_at refreshed, original first_seen_at preserved.
  ```

---

## 3. Storage Conceptual Questions & Answers

### 1. How are duplicates identified?
Duplicates are identified primarily via the **`item_url` UNIQUE constraint**. When a scraper extracts an item, `storage.py` queries the database by `item_url`. If a record with that canonical URL already exists, it is recognized as a known item rather than a new discovery.

### 2. What happens if the same URL appears twice in a single crawl run?
Because `item_url` is indexed and enforced with a `UNIQUE` constraint, the first occurrence inserts the record into `monitored_items`. The second occurrence triggers the upsert logic: it queries `item_url`, finds the existing record, compares `content_hash`, updates `last_seen_at`, and returns `unchanged` without raising a primary key collision error or creating duplicate rows.

### 3. What does `first_seen_at` mean?
`first_seen_at` records the exact ISO 8601 timestamp when a given canonical item URL was **first discovered and persisted** by the web monitoring pipeline. It remains immutable across all future scrapes and updates, serving as the baseline provenance timestamp.

### 4. What does `last_seen_at` mean?
`last_seen_at` records the timestamp of the **most recent pipeline execution** in which the item URL was observed on the target public listing page. Comparing `last_seen_at` against the current time allows monitoring systems to detect dropped or archived items.

### 5. Why is a `content_hash` useful?
A `content_hash` (computed via SHA-256 over normalized fields `title|event_start|raw_text|item_type`) enables instant change detection:
- It decouples URL identity from content state.
- It allows the system to distinguish between a routine re-observation (where content is unchanged) and an official update/corrigendum (where the notice title or date was revised).

### 6. Why is "scraping the page again" different from "discovering a new item"?
Scraping the page again is a **routine collection cycle** that re-inspects a public surface. Discovering a new item means **extracting a canonical URL that has never been recorded in persistent storage before**. Conflating fetching with item discovery leads to inflated event counts and false positive alerts.
