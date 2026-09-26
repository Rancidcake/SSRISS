# Failure-Mode Analysis (Week 2 deliverable 12)

What can go wrong with the JNU monitor, how we notice, and what happens to the data.
✔ = covered by an automated test in `tests/`.

| # | Failure | Where detected | Visible as | Effect on data | Test |
|---|---|---|---|---|---|
| 1 | Bad URL in config | fetch | `ERROR FAILED stage=fetch … invalid URL` | none written | ✔ `test_invalid_url_fails_at_fetch` |
| 2 | DNS / network down | fetch | `stage=fetch … connection failed` | none written; next scheduled run retries | ✔ `test_connection_failure_fails_at_fetch` |
| 3 | Timeout (slow server) | fetch | `stage=fetch … timeout after 15s` | none written | (same path as 2) |
| 4 | Listing moved (404/5xx) | fetch | `FETCH … status=404` + `FAILED stage=fetch` | none written | live demo scenario 3 |
| 5 | Page 2+ fails mid-pagination | fetch | `WARNING PAGINATION … stop=fetch_error keeping=N` | earlier pages **stored** | ✔ `test_later_page_failure_keeps_earlier_records` |
| 6 | Site redesign / wrong page | parse | `stage=parse ParseError … not found / layout changed` | none written (old data intact) | ✔ `test_changed_card_structure_raises`, `test_unexpected_html_fails_at_parse` |
| 7 | Listing legitimately empty | parse | `WARNING EMPTY`, run `success` | nothing new | ✔ `test_empty_listing_is_a_warning_not_a_crash` |
| 8 | Pagination loop / endless pages | pagination | `stop=already_visited` / `max_pages` / hard cap 20 | bounded | ✔ `test_loop_is_detected`, `test_max_pages_limit` |
| 9 | Same item on two pages | pagination + storage | `DUPLICATE … (skipped)` | one row | ✔ `test_duplicate_across_pages_creates_one_db_row` |
| 10 | Different notices sharing a link (`/convocation`) | parse (identity rule) | 3 separate records | no silent merge | ✔ `test_notices_sharing_a_landing_page_stay_separate` |
| 11 | Hindi duplicate rows | parse | folded, `extra.title_hi` | one row per event | ✔ `test_live_snapshot_events_regression` |
| 12 | Sl. No. shifts when new notice is posted | normalize/hash | counted `existing`, not `changed` | no false "changed" | ✔ `test_serial_number_shift_is_not_a_change` |
| 13 | Detail page 404 / broken | detail | `WARNING DETAIL_FAILED … (listing record kept)` | listing record stored, `detail_status=failed` | ✔ `test_detail_404_does_not_break_the_crawl` |
| 14 | One record can't be normalized | normalize | `WARNING NORMALIZE_SKIP` | other records stored | ✔ `test_bad_record_is_skipped_not_fatal` |
| 15 | DB unwritable / locked mid-write | store | `stage=store StorageError … rolled back` | **whole batch rolled back**, old rows intact | ✔ `test_database_problem_fails_at_store_and_keeps_old_data`, `test_failed_batch_is_rolled_back` |
| 16 | Scheduler fires while previous run still going | scheduler | `WARNING SCHEDULE_SKIP` | no overlap | ✔ `test_slow_run_is_not_overlapped` |
| 17 | Machine asleep → missed runs | scheduler | `SCHEDULE_MISSED` / one coalesced catch-up run | no burst | config (`coalesce`, `misfire_grace_time`) |
| 18 | Typo in schedules.json | scheduler start | `KeyError unknown source …` at startup | nothing runs, fails fast | ✔ `test_unknown_source_is_rejected` |
| 19 | Content silently wrong (e.g. date format change) | **not detected automatically** | `published_at=null` rising | data quality drops | ✗ gap: add a "% of records with a date" alert in Week 3 |
| 20 | JNU blocks our User-Agent / rate-limits | fetch | 403/429 in `FETCH` lines | none written | ✗ not tested; politeness delay + 6 h interval make it unlikely |

## Known gaps / next steps
- Data-quality checks (row 19): alert if a run's parsed count drops >50% vs the previous run.
- Cross-process lock (a lock file or DB row) for two manual runs at the same time.
- Enrich only new/changed items instead of the first N (see adapter notes).
