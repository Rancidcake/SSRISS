#!/usr/bin/env python3
"""
Automated Integration & Unit Tests for JNU Web Monitoring Pipeline (Assignments 01-07)
"""

import os
import sys
import json
import sqlite3
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "assignments", "01_http"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "assignments", "05_parsing"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "assignments", "05_parsing", "jnu"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "assignments", "06_normalization"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "assignments", "07_storage"))

from http_probe import probe_url
from fixture_parser import parse_events
from scraper import parse_items
from normalizer import normalize_item, parse_date_to_iso
from storage import init_db, upsert_item, get_item, compute_content_hash


class TestJNUPipeline(unittest.TestCase):

    def test_01_http_probe(self):
        """Test http_probe on robots.txt endpoint."""
        res = probe_url("https://www.jnu.ac.in/robots.txt", timeout=10)
        self.assertEqual(res["status_code"], 200)
        self.assertFalse(res["is_html"])
        self.assertIn("robots.txt", res["first_200_characters_of_body"])

    def test_03_fixture_parser(self):
        """Test fixture HTML parser missing optional fields and link type detection."""
        fixture_path = os.path.join(PROJECT_ROOT, "assignments", "03_dom", "fixture.html")
        with open(fixture_path, "r", encoding="utf-8") as f:
            html = f.read()
        
        events = parse_events(html, base_url="https://example.university.edu")
        self.assertEqual(len(events), 8)
        
        # Check PDF notice vs HTML notice classification
        self.assertEqual(events[0]["item_type"], "html_notice")
        self.assertEqual(events[1]["item_type"], "pdf_notice")
        
        # Check missing field resilience (Notice 3 has missing speaker)
        self.assertIsNone(events[2]["speaker_raw"])

    def test_05_jnu_scraper_parser(self):
        """Test real JNU scraper parser on local sample snapshot."""
        sample_path = os.path.join(PROJECT_ROOT, "assignments", "05_parsing", "jnu", "sample_response.html")
        with open(sample_path, "r", encoding="utf-8") as f:
            html = f.read()
        
        items = parse_items(html, base_url="https://www.jnu.ac.in/notices")
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertIn("title", item)
            self.assertIn("item_url", item)
            self.assertIn(item["item_type"], ["pdf_notice", "html_notice"])

    def test_06_normalizer(self):
        """Test date parsing and item normalization."""
        self.assertEqual(parse_date_to_iso("Mon, 07-09-2026"), "2026-09-07")
        self.assertEqual(parse_date_to_iso("15 September 2026"), "2026-09-15")

        raw_item = {
            "source_name": "jnu_official_notices",
            "source_url": "https://www.jnu.ac.in/notices",
            "title": "  Circular regarding   holiday  ",
            "item_url": "https://www.jnu.ac.in/docs/test.pdf",
            "date_raw": "Mon, 07-09-2026",
            "raw_text": "Sl 1"
        }
        norm = normalize_item(raw_item)
        self.assertEqual(norm["title"], "Circular regarding holiday")
        self.assertEqual(norm["event_start"], "2026-09-07")
        self.assertEqual(norm["item_type"], "pdf_notice")

    def test_07_storage_deduplication(self):
        """Test SQLite database initialization, insertion, idempotency, and update detection."""
        test_db = os.path.join(PROJECT_ROOT, "assignments", "07_storage", "test_temp.db")
        if os.path.exists(test_db):
            os.remove(test_db)
        
        init_db(test_db)
        item = {
            "source_name": "jnu_official_notices",
            "source_url": "https://www.jnu.ac.in/notices",
            "item_url": "https://www.jnu.ac.in/test-notice-1",
            "item_type": "html_notice",
            "title": "Test Notice 1",
            "event_start": "2026-09-09",
            "raw_text": "Test Notice 1 Raw Text"
        }

        # Run 1: Insert
        status1, rec1 = upsert_item(test_db, item, current_time="2026-09-09T10:00:00+05:30")
        self.assertEqual(status1, "inserted")
        self.assertEqual(rec1["first_seen_at"], "2026-09-09T10:00:00+05:30")

        # Run 2: Unchanged
        status2, rec2 = upsert_item(test_db, item, current_time="2026-09-09T11:00:00+05:30")
        self.assertEqual(status2, "unchanged")
        self.assertEqual(rec2["first_seen_at"], "2026-09-09T10:00:00+05:30")
        self.assertEqual(rec2["last_seen_at"], "2026-09-09T11:00:00+05:30")

        # Run 3: Content updated
        item["title"] = "Test Notice 1 (Updated)"
        status3, rec3 = upsert_item(test_db, item, current_time="2026-09-09T12:00:00+05:30")
        self.assertEqual(status3, "updated")
        self.assertEqual(rec3["title"], "Test Notice 1 (Updated)")
        self.assertEqual(rec3["first_seen_at"], "2026-09-09T10:00:00+05:30")

        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    unittest.main()
