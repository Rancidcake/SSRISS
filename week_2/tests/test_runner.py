"""Assignment 1 + 2 - common runner, logging, and failure stages."""

import sqlite3
from dataclasses import replace

import pytest

from sources.jnu import JNU_NOTICES
from src import runner, storage
from src.errors import FetchError
from src.fetch import fetch
from src.schema import build_record

NOTICES = "https://www.jnu.ac.in/notices"


def one_page(source=JNU_NOTICES, **kw):
    return replace(source, max_pages=1, **kw)


def messages(logs):
    return [r.message for r in logs.records]


def test_successful_run_logs_every_stage(fake_fetcher, db_path, logs):
    fetcher = fake_fetcher({NOTICES: "jnu/notices/normal_page.html"})
    result = runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)

    assert result["status"] == "success" and result["new"] == 10
    text = "\n".join(messages(logs))
    for marker in ("START source=jnu_notices", "PARSE source=jnu_notices page=1", "records=10",
                   "NORMALIZE source=jnu_notices records=10", "STORE source=jnu_notices new=10",
                   "END source=jnu_notices"):
        assert marker in text


def test_rerun_is_idempotent(fake_fetcher, db_path):
    fetcher = fake_fetcher({NOTICES: "jnu/notices/normal_page.html"})
    runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)
    second = runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)
    assert (second["new"], second["existing"]) == (0, 10)
    assert storage.count_items(db_path) == 10


@pytest.mark.parametrize("url", ["htp://www.jnu.ac.in/notices", "not a url", "ftp://jnu.ac.in/x"])
def test_invalid_url_fails_at_fetch(url, db_path, logs):
    result = runner.run_source(one_page(listing_url=url), db_path=db_path)
    assert result["status"] == "failed" and result["failed_stage"] == "fetch"
    assert any("stage=fetch" in m and "error_type=FetchError" in m for m in messages(logs))


def test_connection_failure_fails_at_fetch(db_path, logs):
    # network is blocked in tests, so this is a real requests ConnectionError
    result = runner.run_source(one_page(listing_url="https://www.jnu.ac.in/notices"), db_path=db_path)
    assert result["failed_stage"] == "fetch"
    assert any("connection failed" in m for m in messages(logs))


def test_fetch_raises_fetch_error_directly():
    with pytest.raises(FetchError):
        fetch("https://www.jnu.ac.in/notices")


def test_unexpected_html_fails_at_parse(fake_fetcher, db_path, logs):
    fetcher = fake_fetcher({NOTICES: "jnu/notices/changed_card_structure.html"})
    result = runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)
    assert result["status"] == "failed" and result["failed_stage"] == "parse"
    assert any("stage=parse" in m and "ParseError" in m for m in messages(logs))


def test_empty_listing_is_a_warning_not_a_crash(fake_fetcher, db_path, logs):
    fetcher = fake_fetcher({NOTICES: "jnu/notices/empty_listing.html"})
    result = runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)
    assert result["status"] == "success" and result["parsed"] == 0
    assert any(r.levelname == "WARNING" and "EMPTY source=jnu_notices" in r.message for r in logs.records)


def test_database_problem_fails_at_store_and_keeps_old_data(fake_fetcher, db_path, logs, monkeypatch):
    fetcher = fake_fetcher({NOTICES: "jnu/notices/normal_page.html"})
    runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)

    real_upsert = storage._upsert
    calls = {"n": 0}

    def flaky(conn, record, seen_at):
        calls["n"] += 1
        if calls["n"] == 5:
            raise sqlite3.OperationalError("database is locked")
        return real_upsert(conn, record, seen_at)
    monkeypatch.setattr(storage, "_upsert", flaky)

    result = runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)
    assert result["failed_stage"] == "store"
    assert any("stage=store" in m and "rolled back" in m for m in messages(logs))
    assert storage.count_items(db_path) == 10  # nothing lost, nothing half-written


def test_bad_record_is_skipped_not_fatal(fake_fetcher, db_path, logs):
    def normalize(raw):
        if raw["sl_no"] == "3":
            raise ValueError("boom")
        return JNU_NOTICES.normalize_item(raw)
    fetcher = fake_fetcher({NOTICES: "jnu/notices/normal_page.html"})
    result = runner.run_source(one_page(normalize_item=normalize), db_path=db_path, fetcher=fetcher)
    assert result["status"] == "success" and result["new"] == 9
    assert any("NORMALIZE_SKIP" in m for m in messages(logs))


def test_run_history_is_recorded(fake_fetcher, db_path):
    fetcher = fake_fetcher({NOTICES: "jnu/notices/changed_card_structure.html"})
    runner.run_source(one_page(), db_path=db_path, fetcher=fetcher)
    conn = sqlite3.connect(db_path)
    status, stage = conn.execute("SELECT status, failed_stage FROM runs").fetchone()
    assert (status, stage) == ("failed", "parse")


def test_overlapping_run_of_same_source_is_skipped(db_path, logs):
    runner._running.add("jnu_notices")
    try:
        result = runner.run_source(one_page(), db_path=db_path)
    finally:
        runner._running.discard("jnu_notices")
    assert result["status"] == "skipped"
    assert any("already_running" in m for m in messages(logs))


def test_new_source_needs_only_an_adapter(fake_fetcher, db_path):
    """Template check: a brand-new site plugs in with two functions and a config - no core changes."""
    from bs4 import BeautifulSoup
    from src.source import SourceConfig

    def parse(html, base_url):
        return [{"item_url": a["href"], "title": a.get_text(strip=True)}
                for a in BeautifulSoup(html, "html.parser").select("td.views-field-title a")]

    def normalize(raw):
        return build_record("announcement", source_name=raw["source_name"], item_url=raw["item_url"],
                            title=raw["title"])

    toy = SourceConfig(name="toy_site", display_name="Toy", institution="Toy U",
                       listing_url="https://toy.test/news", item_type="announcement",
                       parse_listing=parse, normalize_item=normalize)
    fetcher = fake_fetcher({"https://toy.test/news": "jnu/notices/normal_page.html"})
    assert runner.run_source(toy, db_path=db_path, fetcher=fetcher)["new"] == 10
