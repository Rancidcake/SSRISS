#!/usr/bin/env python3
"""test_aggregator_discovery.py - Unit tests for Discovery Adapters (Assignment 3)

Required tests:
- test_html_discovery
- test_feed_discovery
- test_sitemap_discovery
- test_scope_filter
- test_duplicate_discovery_url
"""

import os
import pytest
from aggregator_discovery import (
    DISCOVERY_SCHEMA_KEYS,
    discover_from_html,
    discover_from_feed,
    discover_from_sitemap,
    discover_items,
    HtmlListingDiscoveryAdapter,
    FeedDiscoveryAdapter,
    SitemapDiscoveryAdapter,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

CONFIG = {
    "source_name": "jnu_events",
    "allowed_hostname": "www.jnu.ac.in",
    "allowed_path_prefixes": ["/node", "/jnuevents", "/events-archive"],
    "excluded_path_prefixes": ["/login", "/user", "/admin", "/search"],
    "allow_external": False,
    "strip_all_query_params": False,
}


@pytest.fixture
def html_content():
    with open(os.path.join(FIXTURES_DIR, "fixture_html.html"), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def feed_content():
    with open(os.path.join(FIXTURES_DIR, "fixture_feed.xml"), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sitemap_content():
    with open(os.path.join(FIXTURES_DIR, "fixture_sitemap.xml"), "r", encoding="utf-8") as f:
        return f.read()


def test_html_discovery(html_content):
    records = discover_from_html(html_content, CONFIG)
    assert len(records) == 3
    for r in records:
        assert set(r.keys()) == DISCOVERY_SCHEMA_KEYS
        assert r["discovery_method"] == "html_listing"
        assert r["source_name"] == "jnu_events"
        assert r["discovered_url"].startswith("https://www.jnu.ac.in/node/")
        assert r["discovered_title"] is not None

    assert "SCIS organises a lecture by Dr. Divya P. Kumar" in records[0]["discovered_title"]
    assert records[0]["discovered_url"] == "https://www.jnu.ac.in/node/159898390"


def test_feed_discovery(feed_content):
    records = discover_from_feed(feed_content, CONFIG)
    assert len(records) == 2
    for r in records:
        assert set(r.keys()) == DISCOVERY_SCHEMA_KEYS
        assert r["discovery_method"] == "rss"
        assert r["source_name"] == "jnu_events"
        assert r["discovered_url"].startswith("https://www.jnu.ac.in/node/")
        assert r["discovered_title"] is not None
        assert r["source_timestamp"] is not None


def test_sitemap_discovery(sitemap_content):
    records = discover_from_sitemap(sitemap_content, CONFIG)
    assert len(records) == 2
    for r in records:
        assert set(r.keys()) == DISCOVERY_SCHEMA_KEYS
        assert r["discovery_method"] == "sitemap"
        assert r["source_name"] == "jnu_events"
        assert r["discovered_url"].startswith("https://www.jnu.ac.in/node/")
        assert r["discovered_title"] is None
        assert r["source_timestamp"] is not None


def test_scope_filter():
    restricted_config = {
        "source_name": "jnu_events",
        "allowed_hostname": "www.jnu.ac.in",
        "allowed_path_prefixes": ["/node/159898390"],  # only allow this single node
        "allow_external": False,
    }
    sample_html = """
    <table>
      <tr><td><a href="https://www.jnu.ac.in/node/159898390">Allowed Event</a></td></tr>
      <tr><td><a href="https://www.jnu.ac.in/node/999999999">Disallowed Event</a></td></tr>
      <tr><td><a href="https://external.org/event">External Event</a></td></tr>
    </table>
    """
    records = discover_from_html(sample_html, restricted_config)
    assert len(records) == 1
    assert records[0]["discovered_url"] == "https://www.jnu.ac.in/node/159898390"


def test_duplicate_discovery_url(html_content):
    duplicate_html = html_content + html_content
    adapter = HtmlListingDiscoveryAdapter(CONFIG)
    records = adapter.discover(duplicate_html)
    assert len(records) == 3  # duplicates deduplicated within discovery adapter
    urls = [r["discovered_url"] for r in records]
    assert len(urls) == len(set(urls))


def test_discover_items_generic_router(html_content, feed_content, sitemap_content):
    r1 = discover_items(CONFIG, html_content, format_type="html")
    r2 = discover_items(CONFIG, feed_content, format_type="feed")
    r3 = discover_items(CONFIG, sitemap_content, format_type="sitemap")

    assert len(r1) == 3
    assert len(r2) == 2
    assert len(r3) == 2

    with pytest.raises(ValueError, match="Unsupported discovery format"):
        discover_items(CONFIG, html_content, format_type="unknown_format")
