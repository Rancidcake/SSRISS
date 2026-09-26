"""
Scheduled repeated runs (APScheduler 3.10.x - pinned; 4.x has a different API).

Schedules live in schedules.json, NOT in source modules, so a schedule can be
changed without touching any parser. This file contains no selectors and no
institution-specific logic: it only calls run_source(source).

Overlap protection:
  - max_instances=1  -> APScheduler never starts a second copy of the same job
  - coalesce=True    -> if several runs were missed, run once, not N times
  - runner._running  -> second guard inside run_source itself
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from sources import get_source
from src import storage
from src.logging_config import get_logger, setup_logging
from src.runner import run_source

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEDULE_FILE = ROOT / "schedules.json"
TIMEZONE = "Asia/Kolkata"
META_KEYS = {"enabled", "trigger", "misfire_grace_time", "run_immediately", "comment"}


def load_schedules(path: str | Path = DEFAULT_SCHEDULE_FILE) -> dict[str, dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def scheduled_run(source_name: str, db_path: str) -> dict[str, Any]:
    """Job body. Never raises: a failed run is logged and recorded, existing data untouched."""
    log = get_logger()
    try:
        result = run_source(get_source(source_name), db_path=db_path)
    except Exception as e:  # defensive - run_source already catches stage errors
        log.error(f"SCHEDULED_RUN source={source_name} status=crashed error_type={type(e).__name__} message={e}")
        return {"status": "crashed"}
    log.info(f"SCHEDULED_RUN source={source_name} status={result['status']} "
             f"new={result.get('new', 0)} changed={result.get('changed', 0)} existing={result.get('existing', 0)}")
    return result


def build_scheduler(
    schedules: dict[str, dict[str, Any]],
    db_path: str = storage.DEFAULT_DB_PATH,
    scheduler: BaseScheduler | None = None,
) -> BaseScheduler:
    log = get_logger()
    scheduler = scheduler or BlockingScheduler(timezone=TIMEZONE)

    for name, cfg in schedules.items():
        if not cfg.get("enabled", True):
            log.info(f"SCHEDULE source={name} enabled=false (skipped)")
            continue
        get_source(name)  # fail fast on typos in schedules.json
        trigger = cfg.get("trigger", "interval")
        trigger_args = {k: v for k, v in cfg.items() if k not in META_KEYS}
        extra = {}
        if cfg.get("run_immediately"):
            from datetime import datetime
            extra["next_run_time"] = datetime.now(scheduler.timezone)
        scheduler.add_job(
            scheduled_run, trigger, args=[name, db_path], id=name, name=name,
            max_instances=1, coalesce=True,
            misfire_grace_time=cfg.get("misfire_grace_time", 300),
            replace_existing=True, **trigger_args, **extra,
        )
        log.info(f"SCHEDULE source={name} trigger={trigger} args={trigger_args}")

    def on_event(event):
        if event.code == EVENT_JOB_MAX_INSTANCES:
            log.warning(f"SCHEDULE_SKIP source={event.job_id} reason=previous run still in progress (no overlap)")
        elif event.code == EVENT_JOB_MISSED:
            log.warning(f"SCHEDULE_MISSED source={event.job_id} scheduled_for={event.scheduled_run_time}")
        elif event.code == EVENT_JOB_ERROR:
            log.error(f"SCHEDULE_ERROR source={event.job_id} error={event.exception!r}")

    scheduler.add_listener(on_event, EVENT_JOB_MAX_INSTANCES | EVENT_JOB_MISSED | EVENT_JOB_ERROR)
    return scheduler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run sources on the schedules in schedules.json")
    parser.add_argument("--config", default=str(DEFAULT_SCHEDULE_FILE))
    parser.add_argument("--db", default=storage.DEFAULT_DB_PATH)
    parser.add_argument("--log-file", default=str(ROOT / "logs" / "scheduler.log"))
    parser.add_argument("--run-for", type=int, default=0,
                        help="demo mode: stop after N seconds (0 = run forever)")
    args = parser.parse_args()

    setup_logging("INFO", args.log_file)
    log = get_logger()
    schedules = load_schedules(args.config)

    if args.run_for:
        scheduler = build_scheduler(schedules, args.db, BackgroundScheduler(timezone=TIMEZONE))
        scheduler.start()
        log.info(f"SCHEDULER started (demo, {args.run_for}s) config={args.config}")
        try:
            time.sleep(args.run_for)
        finally:
            scheduler.shutdown(wait=True)
            log.info("SCHEDULER stopped")
    else:
        scheduler = build_scheduler(schedules, args.db)
        log.info(f"SCHEDULER started config={args.config} (Ctrl+C to stop)")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            log.info("SCHEDULER stopped")


if __name__ == "__main__":
    main()
