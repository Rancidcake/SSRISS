# Incremental Collection & Change Detection — Architectural Notes

**Author:** Mayank (SSRISS Intern)  
**Target:** Central Aggregation & Repeated Ingestion Architecture  
**Assignment:** Assignment 4 — Classify Run Results  
**Date:** October 2026  

---

## 1. Core State Definitions

A production monitoring pipeline operates on a continuous schedule (e.g., hourly or daily). The state machine must rigorously classify items into four mutually exclusive categories per run:

```text
               Discovered in current listing?
                     /                \
                   YES                 NO
                  /                      \
          Present in DB?              Present in DB?
           /          \                /          \
         NO            YES           YES           NO
        /                \            /             \
   [NEW]           Content Hash?   [NOT_SEEN_    [IGNORE /
                    /        \      THIS_RUN]     DISALLOWED]
               MATCH        DIFF
                /              \
         [UNCHANGED]        [CHANGED]
```

### 1. What makes an item "new"?
An item is **new** if its canonical identifier (canonical `item_url`) does not exist anywhere in the persistence layer. When a new item is detected:
- It is assigned a `first_seen_at` timestamp equal to the current ingestion run time.
- Its `last_seen_at` and `fetched_at` timestamps are initialized.
- Its initial content hash is calculated and stored.
- Downstream detail extraction and entity parsing are triggered.

### 2. What makes an item "changed"?
An item is **changed** if its canonical `item_url` already exists in the database, but the cryptographic content hash of its normalized semantic payload differs from the stored `content_hash` from previous runs. When a changed item is detected:
- Its `content_hash` is updated to the new value.
- Its `last_seen_at` and `fetched_at` timestamps are updated to the current run time.
- Downstream re-parsing is executed to capture updated dates, modified abstracts, or newly added speakers.
- Its `first_seen_at` timestamp is strictly preserved.

### 3. What fields contribute to your content hash?
The content hash must capture the immutable semantic core of the record. In our implementation, the SHA-256 content hash is computed over a deterministic UTF-8 serialized JSON tuple of:
- `title`: Event or notice headline (cleaned of leading/trailing whitespace).
- `event_start`: Normalized ISO-8601 start datetime string (or date).
- `event_end`: Normalized ISO-8601 end datetime string (or date).
- `location`: Cleaned venue string (e.g., "SCIS Seminar Hall, JNU").
- `description`: Cleaned abstract or event summary text.
- `speaker_names`: Alphabetically sorted list of explicitly extracted speaker names.
- `organizer_names`: Alphabetically sorted list of explicitly extracted organizing units.

### 4. Which volatile fields should NOT contribute to the content hash?
The following transient or environmental attributes must be **strictly excluded** from the content hash:
- `fetched_at` / `discovered_at`: The time the HTTP scraper requested the page.
- `first_seen_at` / `last_seen_at`: Internal database lifecycle bookkeeping timestamps.
- `http_status` / `response_time_ms`: Ephemeral network metrics.
- `sl_no` (Serial numbers / counters): In Drupal and university tables, adding a new top row shifts all preceding serial numbers (e.g., #1 becomes #2). Including serial numbers causes every existing record to appear changed on every run.
- Session IDs / CSRF tokens / cache-busting tokens embedded in URLs.
- Tracking query parameters (`utm_*`, `fbclid`).

### 5. Why should `fetched_at` not make every record appear changed?
`fetched_at` is an operational observation timestamp reflecting when the monitoring process ran, not a semantic property of the academic event. If `fetched_at` were incorporated into the content hash:
- Every record would generate a brand-new SHA-256 hash on every scheduled run.
- The pipeline would report `changed=100%` on every cycle, destroying cache efficiency.
- Downstream consumers would be flooded with false update notifications.
- Relational tables would repeatedly churn duplicate entity edges.

### 6. What does absence from a current listing actually prove?
Absence from a current listing proves **only** that the item is no longer visible on the immediate listing surface at the time of the scrape. It proves nothing more:
- **It does NOT prove the event was deleted or cancelled.**
- In paginated or sliding-window listings (e.g., JNU `/jnuevents`), older events naturally fall off page 1 as newer events are posted, moving into the archive (`/events-archive`).
- Transient network timeouts, server-side pagination glitches, or temporary CMS caching can temporarily hide records.
- Therefore, our system marks absent items as `not_seen_this_run` and retains their full database records and entity relations. Deletion is never inferred without an explicit HTTP 404/410 on the canonical detail URL or a tombstone marker.

---

## 2. Checkpoint Verification: Simulated Run Cycle

Given the Assignment 4 specification:
```text
Run 1: A, B, C
Result: new=3, changed=0, unchanged=0, not_seen_this_run=0

Run 2: A (same content), B (updated abstract), D (new), C (absent from listing)
Result: new=1, changed=1, unchanged=1, not_seen_this_run=1
```
Database state after Run 2:
- Items `A`, `B`, `C`, `D` all remain in the database.
- `C` is retained with its original `first_seen_at` and `last_seen_at` preserved from Run 1.
- Zero destructive deletes occur.
