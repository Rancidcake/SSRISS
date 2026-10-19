#!/usr/bin/env python3
"""test_unified_discovery.py - Unit tests for unified discovery records (Assignment 1B)"""

import os
import pytest
from unified_discovery import (
    DiscoveryRecord,
    discover_from_html_content,
    discover_from_rss_content,
    discover_from_sitemap_content,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def html_content():
    with open(os.path.join(FIXTURES_DIR, "sample_html_listing.html"), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def rss_content():
    with open(os.path.join(FIXTURES_DIR, "sample_feed.xml"), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sitemap_content():
    with open(os.path.join(FIXTURES_DIR, "sample_sitemap.xml"), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sitemap_index_content():
    with open(os.path.join(FIXTURES_DIR, "sample_sitemap_index.xml"), "r", encoding="utf-8") as f:
        return f.read()


def test_discovery_record_validation():
    with pytest.raises(ValueError, match="discovered_url cannot be empty"):
        DiscoveryRecord.create(source_name="jnu", discovered_url="", discovery_method="rss")

    with pytest.raises(ValueError, match="Invalid discovery_method"):
        DiscoveryRecord.create(source_name="jnu", discovered_url="https://jnu.ac.in", discovery_method="ftp")


def test_unified_shape_schema():
    rec = DiscoveryRecord.create(
        source_name="jnu_events",
        discovered_url="https://www.jnu.ac.in/node/123",
        discovery_method="rss",
        discovered_title="Test Event",
        source_timestamp="2026-09-30T10:00:00Z",
        discovered_at="2026-10-19T12:00:00Z",
    )
    d = rec.to_dict()
    expected_keys = {
        "source_name",
        "discovered_url",
        "discovery_method",
        "discovered_title",
        "source_timestamp",
        "discovered_at",
    }
    assert set(d.keys()) == expected_keys
    assert d["source_name"] == "jnu_events"
    assert d["discovered_url"] == "https://www.jnu.ac.in/node/123"
    assert d["discovery_method"] == "rss"
    assert d["discovered_title"] == "Test Event"


def test_html_discovery(html_content):
    records = discover_from_html_content(html_content, base_url="https://www.jnu.ac.in", source_name="jnu_events")
    assert len(records) == 4
    for r in records:
        assert r.discovery_method == "html_listing"
        assert r.source_name == "jnu_events"
        assert r.discovered_url.startswith("https://www.jnu.ac.in/node/")
        assert r.discovered_title is not None

    assert "SCIS organises a lecture by Dr. Divya P. Kumar" in records[0].discovered_title
    assert records[0].discovered_url == "https://www.jnu.ac.in/node/159898390"


def test_rss_discovery(rss_content):
    records = discover_from_rss_content(rss_content, source_name="jnu_events")
    assert len(records) == 5
    for r in records:
        assert r.discovery_method == "rss"
        assert r.discovered_url.startswith("https://www.jnu.ac.in/node/")
        assert r.discovered_title is not None
        assert r.source_timestamp is not None


def test_sitemap_discovery(sitemap_content):
    records = discover_from_sitemap_content(sitemap_content, source_name="jnu_sitemap")
    assert len(records) == 6
    for r in records:
        assert r.discovery_method == "sitemap"
        assert r.discovered_url.startswith("https://www.jnu.ac.in/")
        assert r.discovered_title is None
        assert r.source_timestamp is not None


def test_sitemap_index_discovery(sitemap_index_content):
    records = discover_from_sitemap_content(sitemap_index_content, source_name="jnu_index")
    assert len(records) == 3
    assert records[0].discovered_url == "https://www.jnu.ac.in/sitemap_events.xml"


def test_format_shape_equivalence(html_content, rss_content, sitemap_content):
    r_html = discover_from_html_content(html_content)[0].to_dict()
    r_rss = discover_from_rss_content(rss_content)[0].to_dict()
    r_sm = discover_from_sitemap_content(sitemap_content)[0].to_dict()

    assert set(r_html.keys()) == set(r_rss.keys()) == set(r_sm.keys())
