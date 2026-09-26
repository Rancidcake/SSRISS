# Assignment 1 — Failure Examples (JNU)

All output below is **real**, produced on 2026-09-26 by `python3 scripts/failure_demo.py`
(full log: `logs/failure_examples.log`). Each scenario goes through the normal
`run_source()` runner; only the source URL / DB path was changed to force the failure.
The demo uses a throw-away database, so `data/monitor.db` is untouched.

## How to read the logs

Every line is `timestamp LEVEL EVENT key=value ...`. A run always starts with `START`
and ends with `END ... status=success|failed`. A failure is **one `ERROR FAILED` line**
that carries everything needed to diagnose it without opening the code:

| key | meaning |
|---|---|
| `source=` | which source adapter (registry name) |
| `run_id=` | ties START / FAILED / END of one run together |
| `stage=` | **fetch / parse / normalize / store** (or `detail` for per-item enrichment) |
| `url=` | the URL being processed when it failed |
| `error_type=` | exception class (`FetchError`, `ParseError`, `StorageError`, …) |
| `message=` | human explanation |

Useful greps: `grep ERROR logs/monitor.log`, `grep "stage=parse" logs/*.log`,
`python3 run.py runs` (run history table incl. `failed_stage`).

## Successful run (for comparison)

```text
INFO     START source=jnu_notices run_id=cc110541 url=https://www.jnu.ac.in/notices capabilities=listing,pagination
INFO     FETCH url=https://www.jnu.ac.in/notices status=200 duration_ms=283
INFO     PARSE source=jnu_notices page=1 url=https://www.jnu.ac.in/notices records=50
INFO     FETCH url=https://www.jnu.ac.in/notices?page=1 status=200 duration_ms=225
INFO     PARSE source=jnu_notices page=2 url=https://www.jnu.ac.in/notices?page=1 records=50
INFO     PAGINATION source=jnu_notices pages=2 records=100 duplicates=0 stop=max_pages
INFO     NORMALIZE source=jnu_notices records=100 skipped=0
INFO     STORE source=jnu_notices new=100 existing=0 changed=0
INFO     END source=jnu_notices run_id=cc110541 status=success duration_ms=1505
```

Second run of the same source a moment later → `STORE source=jnu_notices new=0 existing=100 changed=0`.

---

## 1. Invalid URL → stage=fetch

```text
INFO     START source=jnu_notices run_id=a41dc337 url=htp://www.jnu.ac.in/notices capabilities=listing,pagination
ERROR    FAILED source=jnu_notices run_id=a41dc337 stage=fetch url=htp://www.jnu.ac.in/notices error_type=FetchError message=invalid URL (scheme 'htp' not supported)
INFO     END source=jnu_notices run_id=a41dc337 status=failed duration_ms=0
```
Diagnosis: no `FETCH` line at all + `invalid URL` → config typo, no request was sent.

## 2. Connection failure (DNS) → stage=fetch

```text
INFO     START source=jnu_notices run_id=c1f1061b url=https://www.jnu-does-not-exist.invalid/notices capabilities=listing,pagination
ERROR    FAILED source=jnu_notices run_id=c1f1061b stage=fetch url=https://www.jnu-does-not-exist.invalid/notices error_type=FetchError message=connection failed: ConnectionError: HTTPSConnectionPool(host='www.jnu-does-not-exist.invalid', port=443): Max retries exceeded with url: /notices (Caused by NameResolutionError(...
INFO     END source=jnu_notices run_id=c1f1061b status=failed duration_ms=48
```
Diagnosis: `connection failed` + `NameResolutionError` → network/DNS problem, not our code. Retry later.

## 3. HTTP 404 on the listing → stage=fetch

```text
INFO     START source=jnu_notices run_id=ccabbc75 url=https://www.jnu.ac.in/events capabilities=listing,pagination
INFO     FETCH url=https://www.jnu.ac.in/events status=404 duration_ms=250
ERROR    FAILED source=jnu_notices run_id=ccabbc75 stage=fetch url=https://www.jnu.ac.in/events error_type=FetchError message=HTTP 404
INFO     END source=jnu_notices run_id=ccabbc75 status=failed duration_ms=1255
```
Diagnosis: the server answered (`FETCH ... status=404`) → the page moved. (This is a real
finding: `/events`, listed in the Week 1 recon notes, is 404; the real page is `/jnuevents`.)

## 4a. Parser receives unexpected HTML (wrong page) → stage=parse

```text
INFO     START source=jnu_notices run_id=bd02be47 url=https://www.jnu.ac.in/about-us capabilities=listing,pagination
INFO     FETCH url=https://www.jnu.ac.in/about-us status=200 duration_ms=196
ERROR    FAILED source=jnu_notices run_id=bd02be47 stage=parse url=https://www.jnu.ac.in/about-us error_type=ParseError message=listing container 'div.view-id-notices' not found - page structure changed or this is not the expected page
INFO     END source=jnu_notices run_id=bd02be47 status=failed duration_ms=1240
```
Diagnosis: fetch was fine (200) but the parser could not find its container → redesign or wrong URL.

## 4b. Parser receives changed layout (table replaced by cards) → stage=parse

```text
INFO     FETCH url=file:///.../fixtures/jnu/notices/changed_card_structure.html status=200 duration_ms=0
ERROR    FAILED source=jnu_notices run_id=46c22902 stage=parse url=file:///.../changed_card_structure.html error_type=ParseError message=div.view-id-notices has .view-content but no table rows - listing layout changed (cards/divs instead of a table?)
```
Important design choice: a changed layout **fails loudly**. If it silently returned 0 items the
monitor would report "no new notices" forever and nobody would notice.

## 5. Empty listing → WARNING, run still succeeds

Real JNU page `https://www.jnu.ac.in/jnuevents?page=1` (Drupal renders the view with no `.view-content`):

```text
INFO     START source=jnu_events run_id=b002e9a8 url=https://www.jnu.ac.in/jnuevents?page=1 capabilities=listing,pagination,detail
INFO     FETCH url=https://www.jnu.ac.in/jnuevents?page=1 status=200 duration_ms=220
INFO     PARSE source=jnu_events page=1 url=https://www.jnu.ac.in/jnuevents?page=1 records=0
INFO     PAGINATION source=jnu_events pages=1 records=0 duplicates=0 stop=empty_page
WARNING  EMPTY source=jnu_events url=https://www.jnu.ac.in/jnuevents?page=1 stage=parse message=listing returned 0 records (page empty or selectors no longer match)
INFO     NORMALIZE source=jnu_events records=0 skipped=0
INFO     STORE source=jnu_events new=0 existing=0 changed=0
INFO     END source=jnu_events run_id=b002e9a8 status=success duration_ms=1189
```
Empty is a legitimate state (no upcoming events), so it is a WARNING, not an ERROR.

## 6. Database write problem → stage=store

DB path pointed at a directory:

```text
INFO     NORMALIZE source=jnu_notices records=5 skipped=0
ERROR    FAILED source=jnu_notices run_id=09ec9e8d stage=store url=file:///.../fixtures/pagination/page_1.html error_type=StorageError message=cannot open database /Users/mayank/Documents/SSRISS/week_2/data: OperationalError: unable to open database file
INFO     END source=jnu_notices run_id=09ec9e8d status=failed duration_ms=3
```
Fetch/parse/normalize all logged success, so the problem is clearly the database.
A write failure in the *middle* of a batch is rolled back (tested in
`tests/test_runner.py::test_database_problem_fails_at_store_and_keeps_old_data`), message then reads
`write failed, transaction rolled back: OperationalError: database is locked`.

## 7. One detail page 404s → WARNING, other records still stored

```text
INFO     FETCH url=https://www.jnu.ac.in/node/159898390 status=200 duration_ms=193
INFO     FETCH url=https://www.jnu.ac.in/node/999999999 status=404 duration_ms=689
WARNING  DETAIL_FAILED source=jnu_events stage=detail url=https://www.jnu.ac.in/node/159898442 error_type=FetchError status=404 message=HTTP 404 (listing record kept)
INFO     FETCH url=https://www.jnu.ac.in/node/159898416 status=200 duration_ms=242
INFO     DETAIL source=jnu_events attempted=3 ok=2 failed=1
INFO     STORE source=jnu_events new=13 existing=0 changed=0
INFO     END source=jnu_events run_id=fa882ef5 status=success duration_ms=5363
```

## Summary: which stage failed?

| What you see in the log | Stage | Typical cause |
|---|---|---|
| `FAILED ... stage=fetch` with no `FETCH` line | fetch | bad URL / DNS / connection refused / timeout |
| `FETCH ... status=4xx/5xx` then `FAILED stage=fetch` | fetch | page moved, server down |
| `FETCH status=200` then `FAILED stage=parse ParseError` | parse | site redesign / wrong page |
| `WARNING EMPTY` and `status=success` | parse (warning) | nothing listed right now |
| `WARNING NORMALIZE_SKIP` | normalize | one bad record skipped |
| `FAILED stage=store StorageError` | store | DB locked / path / disk |
| `WARNING DETAIL_FAILED` and `status=success` | detail | one detail page broken |
