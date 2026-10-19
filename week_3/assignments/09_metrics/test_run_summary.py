#!/usr/bin/env python3
"""test_run_summary.py - Unit tests for Source Health & Coverage Metrics (Assignment 9)"""

import os
import sqlite3
import pytest
from run_summary import RunMetrics, persist_metrics_to_db

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_metrics_percentages():
    m = RunMetrics(
        source="jnu_events",
        started_at="2026-10-19T10:00:00Z",
        finished_at="2026-10-19T10:01:00Z",
        pages_fetched=2,
        items_discovered=10,
        items_parsed=10,
        items_with_date=10,
        items_with_speaker=8,
        items_with_organization=9,
    )
    assert m.pct_with_date == 100.0
    assert m.pct_with_speaker == 80.0
    assert m.pct_with_organization == 90.0


def test_diagnosis_active_updates():
    m = RunMetrics(
        source="jnu_events",
        started_at="2026-10-19T10:00:00Z",
        finished_at="2026-10-19T10:01:00Z",
        pages_fetched=2,
        items_discovered=10,
        items_parsed=10,
        new=4,
        changed=2,
        unchanged=4,
    )
    assert "HEALTHY: Active updates ingested" in m.diagnose_health()


def test_diagnosis_steady_state_all_unchanged():
    m = RunMetrics(
        source="jnu_events",
        started_at="2026-10-19T10:00:00Z",
        finished_at="2026-10-19T10:01:00Z",
        pages_fetched=2,
        items_discovered=10,
        items_parsed=10,
        new=0,
        changed=0,
        unchanged=10,
        failed=0,
    )
    assert "HEALTHY: Source active (steady state, all unchanged)" in m.diagnose_health()


def test_diagnosis_broken_parser_failure():
    """Assignment 9 Checkpoint: A reviewer must be able to distinguish
    'source had no new content' from 'parser broke and returned zero content'.
    """
    m = RunMetrics(
        source="jnu_events",
        started_at="2026-10-19T10:00:00Z",
        finished_at="2026-10-19T10:01:00Z",
        pages_fetched=2,
        items_discovered=0,
        items_parsed=0,
        new=0,
        changed=0,
        unchanged=0,
    )
    assert "CRITICAL: Broken parser suspected" in m.diagnose_health()


def test_diagnosis_high_failure_rate():
    m = RunMetrics(
        source="jnu_events",
        started_at="2026-10-19T10:00:00Z",
        finished_at="2026-10-19T10:01:00Z",
        pages_fetched=2,
        items_discovered=10,
        items_parsed=2,
        failed=8,
    )
    assert "CRITICAL: High failure rate" in m.diagnose_health()


def test_summary_text_output_format():
    m = RunMetrics(
        source="example_events",
        started_at="2026-10-19T10:00:00Z",
        finished_at="2026-10-19T10:01:00Z",
        pages_fetched=3,
        items_discovered=26,
        items_parsed=25,
        new=4,
        changed=2,
        unchanged=19,
        failed=1,
        people_extracted=13,
        organizations_extracted=8,
        items_with_date=25,
        items_with_speaker=13,
        items_with_organization=20,
    )
    txt = m.to_summary_text()
    assert "SOURCE: example_events" in txt
    assert "PAGES_FETCHED: 3" in txt
    assert "ITEMS_DISCOVERED: 26" in txt
    assert "ITEMS_PARSED: 25" in txt
    assert "NEW: 4" in txt
    assert "CHANGED: 2" in txt
    assert "UNCHANGED: 19" in txt
    assert "FAILED: 1" in txt
    assert "PEOPLE_EXTRACTED: 13" in txt
    assert "ORGANIZATIONS_EXTRACTED: 8" in txt


def test_persist_metrics_to_sqlite():
    conn = sqlite3.connect(":memory:")
    m = RunMetrics(
        source="jnu_events",
        started_at="2026-10-19T10:00:00Z",
        finished_at="2026-10-19T10:01:00Z",
        pages_fetched=2,
        items_discovered=10,
        items_parsed=10,
        new=2,
        changed=1,
        unchanged=7,
        failed=0,
        people_extracted=8,
        organizations_extracted=5,
    )
    persist_metrics_to_db(m, conn)

    cur = conn.cursor()
    cur.execute("SELECT * FROM run_metrics")
    row = cur.fetchone()
    assert row is not None
    assert row[1] == "jnu_events"
    assert row[8] == 2  # new_items
    assert row[9] == 1  # changed_items
    assert row[10] == 7 # unchanged_items
    conn.close()
