#!/usr/bin/env python3
"""test_week3_integration.py - Integration test suite for Week 3 final pipeline (Assignment 12)"""

import os
import pytest
from run_integration import run_week3_demonstration

_HERE = os.path.dirname(os.path.abspath(__file__))


def test_full_week3_integration_demonstration():
    m1, m2 = run_week3_demonstration()

    # Phase 1 asserts: Initial run discovers and stores all items as NEW
    assert m1.pages_fetched == 1
    assert m1.items_discovered == 6
    assert m1.items_parsed == 6
    assert m1.new == 6
    assert m1.changed == 0
    assert m1.unchanged == 0
    assert m1.failed == 0
    assert m1.people_extracted >= 4
    assert m1.organizations_extracted >= 4
    assert "HEALTHY: Active updates ingested" in m1.diagnose_health()

    # Phase 2 asserts: Incremental re-crawl reports all items as UNCHANGED
    assert m2.pages_fetched == 1
    assert m2.items_discovered == 6
    assert m2.items_parsed == 6
    assert m2.new == 0
    assert m2.changed == 0
    assert m2.unchanged == 6
    assert m2.failed == 0
    assert "HEALTHY: Source active (steady state, all unchanged)" in m2.diagnose_health()

    # Verify integration_run.log exists and contains log lines
    log_path = os.path.join(_HERE, "integration_run.log")
    assert os.path.exists(log_path)
    with open(log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "=== Starting Ingestion Run: jnu_events ===" in log_content
    assert "[NEW]" in log_content
    assert "[UNCHANGED]" in log_content
