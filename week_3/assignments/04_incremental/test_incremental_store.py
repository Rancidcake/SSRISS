#!/usr/bin/env python3
"""test_incremental_store.py - Unit tests for incremental collection (Assignment 4)"""

import pytest
from incremental_store import (
    IncrementalStore,
    ItemStatus,
    compute_content_hash,
)


def test_content_hash_stability():
    p1 = {"title": "SCIS Lecture", "speaker": "Dr. Kumar", "venue": "SCIS Hall"}
    p2 = {"venue": "SCIS Hall", "title": "SCIS Lecture", "speaker": "Dr. Kumar"}
    assert compute_content_hash(p1) == compute_content_hash(p2)


def test_content_hash_ignores_volatile_fields():
    p1 = {
        "title": "SCIS Lecture",
        "fetched_at": "2026-10-19T10:00:00Z",
        "sl_no": "1",
        "response_time_ms": 142,
    }
    p2 = {
        "title": "SCIS Lecture",
        "fetched_at": "2026-10-19T15:00:00Z",  # later fetch
        "sl_no": "5",                          # counter shifted
        "response_time_ms": 300,
    }
    assert compute_content_hash(p1) == compute_content_hash(p2)


def test_content_hash_detects_semantic_change():
    p1 = {"title": "SCIS Lecture", "description": "Original Abstract"}
    p2 = {"title": "SCIS Lecture", "description": "Updated Abstract with new venue"}
    assert compute_content_hash(p1) != compute_content_hash(p2)


def test_assignment_4_simulation_run_1_and_run_2():
    """Exact test case from Assignment 4 specification:
    Run 1: A, B, C
    Run 2: A unchanged, B changed, C absent, D new
    Result: new=1, changed=1, unchanged=1, not_seen_this_run=1
    Verify C is NOT deleted.
    """
    store = IncrementalStore(":memory:")

    item_a_url = "https://www.jnu.ac.in/node/101"
    item_b_url = "https://www.jnu.ac.in/node/102"
    item_c_url = "https://www.jnu.ac.in/node/103"
    item_d_url = "https://www.jnu.ac.in/node/104"

    payload_a = {"title": "Event A", "desc": "Desc A"}
    payload_b = {"title": "Event B", "desc": "Desc B original"}
    payload_c = {"title": "Event C", "desc": "Desc C"}
    payload_b_changed = {"title": "Event B", "desc": "Desc B updated abstract"}
    payload_d = {"title": "Event D", "desc": "Desc D"}

    # --- RUN 1 ---
    store.begin_run()
    counts_run1 = {"new": 0, "changed": 0, "unchanged": 0}
    for url, p in [(item_a_url, payload_a), (item_b_url, payload_b), (item_c_url, payload_c)]:
        status = store.process_item(url, p, run_timestamp="2026-10-19T10:00:00Z")
        counts_run1[status.value] += 1

    summary_run1 = store.summarize_run(counts_run1)
    assert summary_run1["new"] == 3
    assert summary_run1["changed"] == 0
    assert summary_run1["unchanged"] == 0
    assert summary_run1["not_seen_this_run"] == 0

    # Verify first_seen_at for C
    rec_c_run1 = store.get_item(item_c_url)
    assert rec_c_run1 is not None
    c_first_seen = rec_c_run1["first_seen_at"]
    assert c_first_seen == "2026-10-19T10:00:00Z"

    # --- RUN 2 ---
    # A is unchanged, B has changed payload, C is absent, D is new
    store.begin_run()
    counts_run2 = {"new": 0, "changed": 0, "unchanged": 0}
    for url, p in [
        (item_a_url, payload_a),
        (item_b_url, payload_b_changed),
        (item_d_url, payload_d),
    ]:
        status = store.process_item(url, p, run_timestamp="2026-10-19T11:00:00Z")
        counts_run2[status.value] += 1

    summary_run2 = store.summarize_run(counts_run2)
    assert summary_run2["new"] == 1
    assert summary_run2["changed"] == 1
    assert summary_run2["unchanged"] == 1
    assert summary_run2["not_seen_this_run"] == 1

    # CRITICAL CHECKPOINT: Ensure C was NOT deleted
    rec_c_run2 = store.get_item(item_c_url)
    assert rec_c_run2 is not None
    assert rec_c_run2["title"] == "Event C"
    assert rec_c_run2["first_seen_at"] == c_first_seen
    # B was updated
    rec_b_run2 = store.get_item(item_b_url)
    assert rec_b_run2 is not None
    assert rec_b_run2["last_seen_at"] == "2026-10-19T11:00:00Z"

    store.close()
