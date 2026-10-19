#!/usr/bin/env python3
"""test_content_router.py - Unit tests for Content Router (Assignment 8)"""

import json
import os
import pytest
from content_router import ItemType, classify_discovered_item

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "mixed_listing_sample.json")


@pytest.fixture
def sample_items():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_classify_all_fixture_items(sample_items):
    for item in sample_items:
        classified = classify_discovered_item(item)
        assert classified.value == item["expected_type"], (
            f"Failed on URL '{item['discovered_url']}': Expected {item['expected_type']}, got {classified.value}"
        )


def test_external_link_routing():
    rec = {"discovered_url": "https://docs.google.com/forms/d/123", "discovered_title": "Registration"}
    assert classify_discovered_item(rec) == ItemType.EXTERNAL_LINK


def test_pdf_document_routing():
    rec = {"discovered_url": "https://www.jnu.ac.in/sites/default/files/syllabus.pdf"}
    assert classify_discovered_item(rec) == ItemType.PDF_DOCUMENT


def test_event_routing_by_path():
    rec = {"discovered_url": "https://www.jnu.ac.in/jnuevents/seminar-2026"}
    assert classify_discovered_item(rec) == ItemType.EVENT


def test_announcement_routing_by_path():
    rec = {"discovered_url": "https://www.jnu.ac.in/notices/tenders-october"}
    assert classify_discovered_item(rec) == ItemType.ANNOUNCEMENT


def test_faculty_routing_by_path():
    rec = {"discovered_url": "https://www.jnu.ac.in/faculty/scis/divya-kumar"}
    assert classify_discovered_item(rec) == ItemType.FACULTY


def test_unknown_item_preserved():
    rec = {
        "discovered_url": "https://www.jnu.ac.in/custom-portal/query?uid=99",
        "discovered_title": "Unknown Utility",
    }
    assert classify_discovered_item(rec) == ItemType.UNKNOWN
