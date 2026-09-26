# Assignment 8 — Scheduled Runs

- Library: **APScheduler 3.10.4** (pinned in `requirements.txt`; 4.x has a different API).
- Code: `src/scheduler.py`. Config: `schedules.json` (production), `schedules.demo.json` (offline demo).
- Timezone: `Asia/Kolkata`.

```text
SCHEDULER (schedules.json) → scheduled_run(name) → run_source(get_source(name))
                                                   → fetch → parse → normalize → store → log
```

## schedules.json

| source | trigger | why |
|---|---|---|
| `jnu_notices` | interval, every 6 h | notices appear a few times a week; 6 h is timely and polite |
| `jnu_events` | cron 08:00 and 20:00 | short list, detail pages limited to 5 per run |
| `jnu_events_archive` | cron Mon 03:00, **disabled** | history rarely changes; enable only if needed |

Changing a schedule = edit JSON only. No parser or source file is touched
(tested: `test_changing_schedule_only_touches_json`, `test_scheduler_has_no_site_specific_code`).

## Requirements → how they are met

| Requirement | How |
|---|---|
| no institution-specific selectors in scheduler | scheduler only knows source *names*; test greps its source for selectors |
| no overlapping execution | `max_instances=1`, `coalesce=True`, plus `runner._running` guard. Test `test_slow_run_is_not_overlapped`: 2.5 s job every 1 s → peak concurrency 1, `SCHEDULE_SKIP` logged |
| repeated run → no uncontrolled duplicates | `item_url` UNIQUE + upsert. Demo below: 4 runs → 14 rows |
| run result logged | `SCHEDULED_RUN source=… status=… new=… changed=… existing=…` + `runs` table |
| failure doesn't corrupt data | `scheduled_run` never raises; storage writes are one transaction (rollback) |
| missed runs | `misfire_grace_time=300`, `coalesce=True` → one catch-up run, not a burst |

## Demo (real output, 2026-09-26)

```bash
python3 -m src.scheduler --config schedules.demo.json --db data/scheduler_demo.db \
        --log-file logs/scheduler_demo.log --run-for 10
```
```text
15:52:37 INFO SCHEDULE source=jnu_notices_fixture trigger=interval args={'seconds': 3}
15:52:37 INFO SCHEDULER started (demo, 10s) config=schedules.demo.json
15:52:37 INFO STORE source=jnu_notices_fixture new=14 existing=0 changed=0
15:52:37 INFO SCHEDULED_RUN source=jnu_notices_fixture status=success new=14 changed=0 existing=0
15:52:40 INFO SCHEDULED_RUN source=jnu_notices_fixture status=success new=0 changed=0 existing=14
15:52:43 INFO SCHEDULED_RUN source=jnu_notices_fixture status=success new=0 changed=0 existing=14
15:52:46 INFO SCHEDULED_RUN source=jnu_notices_fixture status=success new=0 changed=0 existing=14
15:52:47 INFO SCHEDULER stopped
```
`sqlite3 data/scheduler_demo.db "select count(*), count(distinct item_url) from items"` → `14|14`; 4 rows in `runs`.

Production start (runs until Ctrl+C): `python3 -m src.scheduler`
