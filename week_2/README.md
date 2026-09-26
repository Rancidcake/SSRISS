# Week 2 — Academic Scraper Template & Reliability (Mayank · JNU)

The Week 1 one-off JNU notice scraper, turned into a small reusable framework:

```text
source config → common runner → fetch → parse (+pagination) → detail enrichment → normalize → store → log
                                                                              ↑ scheduled by APScheduler
```

Live JNU sources implemented (verified 2026-09-26):

| Source | URL | Type | Capabilities | Live result |
|---|---|---|---|---|
| `jnu_notices` | /notices | announcement | listing, pagination | 2 of 4 pages → 100 notices |
| `jnu_events` | /jnuevents | event | listing, detail | 13 events, 5 enriched |
| `jnu_events_archive` | /events-archive | event | listing, pagination, detail | 2 of 41 pages → 58 events, 3 enriched |
| `jnu_notices_fixture` | local fixture | announcement | listing, pagination | 3 pages → 14 (1 duplicate) |

## Setup

```bash
cd week_2
pip3 install -r requirements.txt
python3 -m pytest            # 62 tests, fully offline (network is blocked inside the tests)
```

## Usage

```bash
python3 run.py list                                   # sources + capabilities
python3 run.py run jnu_notices --max-pages 2          # one crawl
python3 run.py run jnu_events --detail-limit 5
python3 run.py run jnu_notices_fixture                # offline, local pagination fixture
python3 run.py show jnu_events                        # stored records
python3 run.py runs                                   # run history: status / failed stage / counts
python3 run.py export data/normalized_output.jsonl    # normalized output
python3 -m src.scheduler                              # scheduled runs from schedules.json (Ctrl+C)
python3 -m src.scheduler --config schedules.demo.json --run-for 10   # 10 s offline demo
python3 scripts/failure_demo.py                       # trigger every failure type → logs/failure_examples.log
python3 scripts/build_fixtures.py                     # rebuild test fixtures from live snapshots
```

Logs go to the console and `logs/monitor.log` (`key=value` format, see
`assignments/01_logging/failure_examples.md`).

## Layout

```text
week_2/
├── run.py                    CLI
├── schedules.json            when each source runs (schedules.demo.json = offline demo)
├── src/                      GENERIC (no JNU knowledge)
│   ├── fetch.py              HTTP: timeout, UA, politeness delay, file:// for fixtures
│   ├── runner.py             run_source() — the common pipeline
│   ├── pagination.py         bounded traversal, stop conditions, canonical URLs
│   ├── schema.py             shared schema (event / announcement / faculty) + helpers
│   ├── storage.py            SQLite: items + runs, upsert, content hash, rollback
│   ├── scheduler.py          APScheduler 3.10.4
│   ├── source.py             SourceConfig (adapter contract)
│   ├── errors.py             stage-tagged exceptions
│   └── logging_config.py
├── sources/
│   ├── __init__.py           registry
│   └── jnu.py                ALL JNU selectors / quirks
├── fixtures/
│   ├── jnu/notices/          normal_page, missing_optional_field, changed_card_structure, empty_listing, duplicate_item
│   ├── jnu/events/           listing, detail_* (real), detail_broken, archive_page
│   ├── jnu/live_snapshots/   full real pages captured 2026-09-26 (regression tests)
│   └── pagination/           page_1..3 (+ loop_page)
├── tests/                    62 tests (pytest)
├── data/                     monitor.db (live SQLite), normalized_output.jsonl, scheduler_demo.db
├── logs/                     monitor.log, failure_examples.log, scheduler_demo.log
├── assignments/              written deliverables (below)
├── scripts/                  failure_demo.py, build_fixtures.py
└── ADDING_A_SOURCE.md        guide for the template swap partner
```

## Deliverables → where

| # | Deliverable | Location |
|---|---|---|
| 0 | Parser test suite + fixtures | `tests/test_jnu.py`, `fixtures/jnu/notices/` |
| 1 | Source structure map | `assignments/03_patterns/jnu_structure.md` |
| 2 | Source adapter | `sources/jnu.py` |
| 3 | Shared runner integration | `src/runner.py`, `sources/__init__.py` |
| 4 | Pagination (fixture + real) | `src/pagination.py`, `tests/test_pagination.py`, `assignments/04_pagination/jnu_pagination_notes.md` |
| 5 | Detail enrichment | `sources/jnu.py::parse_event_detail`, `tests/test_detail.py`, `assignments/05_detail/jnu_detail_notes.md` |
| 6 | Normalized output | `data/normalized_output.jsonl` (171 records) |
| 7 | SQLite data | `data/monitor.db` (`items`, `runs`) |
| 8 | Test suite | `tests/` — `python3 -m pytest` |
| 9 | Logs | `logs/`, `assignments/01_logging/failure_examples.md` |
| 10 | Schedule configuration | `schedules.json`, `src/scheduler.py`, `assignments/08_scheduling/schedule_notes.md` |
| 11 | README | this file |
| 12 | Failure-mode analysis | `assignments/10_integration/failure_modes.md` |
| 13 | Template-swap review | `assignments/09_template_swap/review.md` (**to be completed with partner**) |
| – | Schema review | `assignments/06_schema/schema_review.md` |
| – | Adapter notes | `assignments/07_template/jnu_adapter_notes.md` |

### Assignment 0 test names

| Required | Implemented as |
|---|---|
| test_parse_expected_number_of_items | `tests/test_jnu.py::test_parse_expected_number_of_items` |
| test_parse_title | `…::test_parse_title` |
| test_parse_url | `…::test_parse_url` |
| test_missing_optional_field | `…::test_missing_optional_field` |
| test_empty_listing | `…::test_empty_listing` |
| test_normalization_shape | `…::test_normalization_shape` |
| test_duplicate_item | `…::test_duplicate_item` |
| (changed structure) | `…::test_changed_card_structure_raises` |

(The brief suggests `tests/fixtures/<institution>/`; fixtures live in top-level `fixtures/`
because the Assignment 2 layout puts them there and the demos use them too.)

## Bugs found in Week 1 and fixed in Week 2

1. **Sl. No. inside `raw_text` (and so inside the hash):** every new notice shifts all serial
   numbers → every old notice would have been reported as "changed". Removed the counter.
2. **Link-less notices all got `item_url = /notices`:** they would collapse into one row.
   Now a synthetic `#item-<hash>` identity.
3. **Different notices sharing one landing page** (`/convocation` ×3) → per-notice identity.
4. **Week 1 recon listed `/events` and `/news`:** both are 404. The real pages are `/jnuevents`, `/events-archive`.
5. `source_name` and institution were hard-coded in the "generic" storage/normalizer → moved to adapter/runner.

## Out of scope (per brief)
No CAPTCHA/anti-bot work, no auth, no PDF text extraction, no OCR of event posters, no async/distributed crawling.
