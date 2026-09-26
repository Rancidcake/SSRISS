"""Assignment 8 - scheduling wiring (no real waiting)."""

import inspect
import json

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from src import scheduler, storage


def build(schedules, db_path):
    return scheduler.build_scheduler(schedules, db_path, BackgroundScheduler(timezone=scheduler.TIMEZONE))


def test_jobs_come_from_config_with_overlap_protection(db_path):
    sched = build({"jnu_notices_fixture": {"trigger": "interval", "minutes": 30}}, db_path)
    [job] = sched.get_jobs()
    assert job.id == "jnu_notices_fixture"
    assert job.max_instances == 1 and job.coalesce is True
    assert "interval[0:30:00]" in str(job.trigger)


def test_disabled_sources_are_not_scheduled(db_path):
    sched = build({"jnu_notices_fixture": {"enabled": False, "trigger": "interval", "minutes": 5}}, db_path)
    assert sched.get_jobs() == []


def test_unknown_source_is_rejected(db_path):
    with pytest.raises(KeyError):
        build({"typo_source": {"trigger": "interval", "minutes": 5}}, db_path)


def test_real_schedule_file_is_valid(db_path):
    schedules = scheduler.load_schedules()
    sched = build(schedules, db_path)
    assert {j.id for j in sched.get_jobs()} == {k for k, v in schedules.items() if v.get("enabled", True)}


def test_changing_schedule_only_touches_json(tmp_path, db_path):
    cfg = tmp_path / "s.json"
    cfg.write_text(json.dumps({"jnu_notices_fixture": {"trigger": "cron", "hour": 7, "minute": 15}}))
    [job] = build(scheduler.load_schedules(cfg), db_path).get_jobs()
    assert "hour='7'" in str(job.trigger) and "minute='15'" in str(job.trigger)


def test_scheduled_job_runs_repeatedly_without_duplicates(db_path):
    first = scheduler.scheduled_run("jnu_notices_fixture", db_path)
    second = scheduler.scheduled_run("jnu_notices_fixture", db_path)
    assert first["new"] == 14 and second["new"] == 0 and second["existing"] == 14
    assert storage.count_items(db_path) == 14


def test_scheduled_failure_does_not_raise(db_path):
    result = scheduler.scheduled_run("jnu_notices", db_path)  # network blocked -> fetch failure
    assert result["status"] == "failed"


def test_scheduler_has_no_site_specific_code():
    source = inspect.getsource(scheduler)
    for forbidden in ("select(", "select_one", "BeautifulSoup", "views-field", "jnu.ac.in"):
        assert forbidden not in source


def test_slow_run_is_not_overlapped(db_path, logs, monkeypatch):
    """Job interval 1s, but each run takes 2.5s -> APScheduler must skip, not start a 2nd copy."""
    import threading
    import time

    active, peak = [0], [0]
    lock = threading.Lock()

    def slow_run_source(source, db_path):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(2.5)
        with lock:
            active[0] -= 1
        return {"status": "success"}

    monkeypatch.setattr(scheduler, "run_source", slow_run_source)
    sched = build({"jnu_notices_fixture": {"trigger": "interval", "seconds": 1, "run_immediately": True}}, db_path)
    sched.start()
    time.sleep(3.5)
    sched.shutdown(wait=True)

    assert peak[0] == 1
    assert any("SCHEDULE_SKIP" in r.message for r in logs.records)
