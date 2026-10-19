#!/usr/bin/env python3
"""test_central_aggregator.py - Unit and Integration tests for Central Aggregator Adapter (Assignment 10)"""

import os
import pytest
from central_aggregator_adapter import CentralAggregatorAdapter, DEFAULT_JNU_CONFIG

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "central_listing.html")


@pytest.fixture
def adapter():
    a = CentralAggregatorAdapter(config=DEFAULT_JNU_CONFIG, db_path=":memory:")
    yield a
    a.close()


def test_end_to_end_initial_run(adapter):
    metrics = adapter.run(html_fixture_path=FIXTURE_PATH)
    assert metrics.pages_fetched == 1
    assert metrics.items_discovered == 6
    assert metrics.items_parsed == 6
    assert metrics.new == 6
    assert metrics.changed == 0
    assert metrics.unchanged == 0
    assert metrics.failed == 0
    assert metrics.people_extracted >= 4
    assert metrics.organizations_extracted >= 4
    assert "HEALTHY: Active updates ingested" in metrics.diagnose_health()

    # Relational store verification
    assert adapter.store.count_items() == 6
    assert adapter.store.count_people() >= 4
    assert adapter.store.count_organizations() >= 4
    assert adapter.store.count_item_people() >= 4
    assert adapter.store.count_item_organizations() >= 4


def test_consecutive_runs_incremental_detection(adapter):
    # Run 1: all new
    m1 = adapter.run(html_fixture_path=FIXTURE_PATH)
    assert m1.new == 6
    assert m1.unchanged == 0

    # Run 2: same content -> all unchanged
    m2 = adapter.run(html_fixture_path=FIXTURE_PATH)
    assert m2.new == 0
    assert m2.changed == 0
    assert m2.unchanged == 6
    assert "HEALTHY: Source active (steady state, all unchanged)" in m2.diagnose_health()


def test_bounded_ceiling_limit(adapter):
    metrics = adapter.run(html_fixture_path=FIXTURE_PATH, max_items=3)
    assert metrics.items_parsed == 3
    assert adapter.store.count_items() == 3


def test_broken_fixture_health_diagnosis(adapter):
    broken_html = "<html><body><div>Error 500</div></body></html>"
    metrics = adapter.run(html_content=broken_html)
    assert metrics.items_discovered == 0
    assert metrics.items_parsed == 0
    assert "CRITICAL: Broken parser suspected" in metrics.diagnose_health()
