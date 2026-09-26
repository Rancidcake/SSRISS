# Assignment 7 — JNU Adapter on the Shared Template

```text
src/                      GENERIC — knows nothing about JNU
  fetch.py                requests client: timeout 15 s, User-Agent, 1 s politeness delay, file:// support
  errors.py               stage-tagged exceptions (FetchError, ParseError, SchemaError, StorageError)
  logging_config.py       one "monitor" logger, key=value format, console + file
  schema.py               shared record schema per item_type, validation, clean_text, parse_date
  source.py               SourceConfig dataclass = the adapter contract
  pagination.py           bounded listing traversal + URL canonicalisation + duplicate skipping
  runner.py               run_source(): fetch → parse → detail → normalize → store → log
  storage.py              SQLite: items (UNIQUE item_url, content hash), runs history, atomic batches
  scheduler.py            APScheduler 3.10 jobs from schedules.json
sources/
  __init__.py             registry: name → SourceConfig
  jnu.py                  SOURCE-SPECIFIC — selectors, parsers, quirks, 3 SourceConfigs
schedules.json            WHEN each source runs (no code)
```

## What is generic?

- HTTP: timeout, User-Agent, politeness delay, error classification (`src/fetch.py`).
  Change the timeout in **one** place: `DEFAULT_TIMEOUT`.
- Pagination loop and **all** stop conditions (`src/pagination.py`).
- Detail enrichment orchestration: limit, skip PDFs, per-item failure isolation (`runner._enrich`).
- Schema, validation, date/text helpers (`src/schema.py`).
- Storage, dedup, change detection, rollback, run history (`src/storage.py`).
  Swap the database in **one** place.
- Logging format and stage reporting (`src/logging_config.py`, `src/runner.py`).
- Scheduling (`src/scheduler.py` + `schedules.json`).

## What is source-specific? (`sources/jnu.py` only)

- URLs: `/notices`, `/jnuevents`, `/events-archive`
- Selectors: `div.view-id-notices`, `div.view-id-jnu_events`, `td.views-field-title`,
  `td.views-field-field-notice-date`, `.field--name-field-event-*`
- Empty vs changed-layout rule for Drupal views
- Identity rules: PDF = identity; shared HTML landing page → `#notice-<hash>`; `jnu.ac.in` → `www.`
- Hindi translation folding (`/hi/node/N`)
- Organising unit / speaker extraction from titles
- Venue + registration-link heuristics, webmail-redirect unwrapping
- Per-source budgets: `max_pages`, `detail_limit`

`sources/jnu.py` imports **nothing** from `requests`, `sqlite3` or `logging` → checkpoint satisfied.
(Check: `grep -nE "import (requests|sqlite3|logging)" sources/jnu.py` → no output.)

## Which optional capabilities does this source support?

| Source | listing | pagination | detail | item_type |
|---|---|---|---|---|
| `jnu_notices` | ✔ | ✔ (4 pages) | ✘ (items are PDFs) | announcement |
| `jnu_events` | ✔ | ✔ capability, but page has no pager | ✔ | event |
| `jnu_events_archive` | ✔ | ✔ (41 pages, capped at 2) | ✔ | event |
| `jnu_notices_fixture` | ✔ | ✔ (local fixture) | ✘ | announcement |

`jnu_events_archive` needed **zero new parsing code**. It is a new `SourceConfig` pointing
the same parser at a different URL, which shows the template works.

## What assumptions remain brittle?

1. **Drupal class names.** If JNU renames `view-id-notices` or the `views-field-*` classes, parsing
   fails. It fails *loudly* (`ParseError`), and the 62 fixture tests plus live snapshots catch it.
2. **Title regexes** for organiser/speaker (`"X organises …"`, `"lecture by Y"`). Titles not in
   that shape give `speakers=[]`; nothing breaks, the data is just thinner.
3. **Poster-only event pages.** Venue/time are inside an image, so `location` is almost always
   `null`. Fixing that needs OCR (out of scope).
4. **Identity by URL.** If JNU re-uploads a PDF under a new file name, the monitor sees a *new*
   notice (the old one just stops getting `last_seen_at` updates).
5. **`detail_limit` takes the first N rows.** The same N events get detail-fetched every run and
   later rows are never enriched. Better: only fetch detail for items that are new or whose
   listing hash changed (Week 3 refactor).
6. **Dates:** `DD-MM-YYYY` is assumed (Indian order). An American-style date would be mis-read.
   The `12:00:00Z` time on events is a Drupal placeholder and is dropped.
7. **In-process overlap guard only.** `max_instances=1` + `runner._running` protect one process.
   Two separate `python run.py` processes on the same source at once are not blocked (SQLite
   upserts are still idempotent, so no duplicates, but work is wasted).
