#!/usr/bin/env python3
"""unified_discovery.py - Unified Discovery Record Engine (Assignment 1B)

Normalizes candidate event items discovered from disparate channels:
- HTML card/table listings
- RSS / Atom syndication feeds
- XML Sitemaps / Sitemap indexes

All adapters emit the identical canonical shape:
{
    "source_name": str,
    "discovered_url": str,
    "discovery_method": "html_listing" | "rss" | "sitemap",
    "discovered_title": Optional[str],
    "source_timestamp": Optional[str],
    "discovered_at": str (ISO 8601 UTC)
}
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, List, Optional
import urllib.parse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import feedparser  # type: ignore

DEFAULT_SOURCE_NAME = "jnu"
DEFAULT_HTML_URL = "https://www.jnu.ac.in/jnuevents"
DEFAULT_RSS_URL = "https://www.jnu.ac.in/rss/events.xml"

DEFAULT_SITEMAP_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "sample_sitemap.xml"
)
DEFAULT_HTML_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "sample_html_listing.html"
)
DEFAULT_FEED_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "sample_feed.xml"
)


@dataclass(frozen=True)
class DiscoveryRecord:
    """Canonical discovery candidate model."""

    source_name: str
    discovered_url: str
    discovery_method: str  # 'html_listing', 'rss', or 'sitemap'
    discovered_title: Optional[str]
    source_timestamp: Optional[str]
    discovered_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to primitive dictionary."""
        return asdict(self)

    @classmethod
    def create(
        cls,
        source_name: str,
        discovered_url: str,
        discovery_method: str,
        discovered_title: Optional[str] = None,
        source_timestamp: Optional[str] = None,
        discovered_at: Optional[str] = None,
    ) -> DiscoveryRecord:
        """Factory creating a validated discovery record."""
        if not discovered_url or not discovered_url.strip():
            raise ValueError("discovered_url cannot be empty")
        if discovery_method not in {"html_listing", "rss", "sitemap"}:
            raise ValueError(
                f"Invalid discovery_method '{discovery_method}'. Must be 'html_listing', 'rss', or 'sitemap'."
            )

        now_iso = (
            discovered_at
            if discovered_at
            else datetime.now(timezone.utc).isoformat()
        )

        clean_title = discovered_title.strip() if discovered_title else None
        clean_timestamp = source_timestamp.strip() if source_timestamp else None

        return cls(
            source_name=source_name,
            discovered_url=discovered_url.strip(),
            discovery_method=discovery_method,
            discovered_title=clean_title,
            source_timestamp=clean_timestamp,
            discovered_at=now_iso,
        )


def discover_from_html_content(
    html_content: str,
    base_url: str = "https://www.jnu.ac.in",
    source_name: str = DEFAULT_SOURCE_NAME,
    discovered_at: Optional[str] = None,
) -> List[DiscoveryRecord]:
    """Extract candidate items from HTML event table or cards."""
    soup = BeautifulSoup(html_content, "html.parser")
    records: List[DiscoveryRecord] = []
    seen_urls = set()

    # Drupal table layout: div.view-id-jnu_events or table.views-table
    rows = soup.select("table.views-table tr, div.view-content tr.marquee-row, tr")
    for row in rows:
        title_cell = row.select_one("td.views-field-title") or row.find("td")
        if not title_cell:
            continue
        link = title_cell.find("a", href=True) or row.find("a", href=True)
        if not link:
            continue

        raw_href = link["href"].strip()
        full_url = urllib.parse.urljoin(base_url, raw_href)

        # Skip anchor links or duplicates within page
        if full_url in seen_urls or full_url.endswith("#"):
            continue
        seen_urls.add(full_url)

        title_text = link.get_text(strip=True) or title_cell.get_text(strip=True)

        # Date cell if present
        date_el = row.select_one("time") or row.select_one("td.views-field-field-event-from-date")
        timestamp = None
        if date_el:
            timestamp = date_el.get("datetime") or date_el.get_text(strip=True)

        record = DiscoveryRecord.create(
            source_name=source_name,
            discovered_url=full_url,
            discovery_method="html_listing",
            discovered_title=title_text if title_text else None,
            source_timestamp=timestamp,
            discovered_at=discovered_at,
        )
        records.append(record)

    # Fallback for generic card layouts if no table rows matched
    if not records:
        for card in soup.select("div.event-card, article.node, div.views-row"):
            link = card.find("a", href=True)
            if not link:
                continue
            full_url = urllib.parse.urljoin(base_url, link["href"].strip())
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title_el = card.select_one("h2, h3, h4, .title") or link
            title = title_el.get_text(strip=True)
            time_el = card.find("time")
            timestamp = time_el.get("datetime", time_el.get_text(strip=True)) if time_el else None

            records.append(
                DiscoveryRecord.create(
                    source_name=source_name,
                    discovered_url=full_url,
                    discovery_method="html_listing",
                    discovered_title=title,
                    source_timestamp=timestamp,
                    discovered_at=discovered_at,
                )
            )

    return records


def discover_from_rss_content(
    feed_xml: str,
    source_name: str = DEFAULT_SOURCE_NAME,
    discovered_at: Optional[str] = None,
) -> List[DiscoveryRecord]:
    """Parse candidate items from RSS/Atom XML string."""
    parsed = feedparser.parse(feed_xml)
    records: List[DiscoveryRecord] = []

    for entry in parsed.entries:
        url = entry.get("link") or entry.get("id") or ""
        if not url:
            continue

        title = entry.get("title")
        timestamp = (
            entry.get("published")
            or entry.get("updated")
            or entry.get("pubDate")
        )

        record = DiscoveryRecord.create(
            source_name=source_name,
            discovered_url=url.strip(),
            discovery_method="rss",
            discovered_title=title.strip() if title else None,
            source_timestamp=timestamp.strip() if timestamp else None,
            discovered_at=discovered_at,
        )
        records.append(record)

    return records


def discover_from_sitemap_content(
    sitemap_xml: str,
    source_name: str = DEFAULT_SOURCE_NAME,
    discovered_at: Optional[str] = None,
) -> List[DiscoveryRecord]:
    """Parse candidate URLs from XML Sitemap string."""
    root = ET.fromstring(sitemap_xml)
    records: List[DiscoveryRecord] = []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    # Handle sitemapindex vs urlset
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    if tag == "sitemapindex":
        elements = root.findall("sm:sitemap", ns) or root.findall("sitemap")
        for sm in elements:
            loc = sm.findtext("sm:loc", default="", namespaces=ns) or sm.findtext("loc", default="")
            if not loc:
                continue
            lastmod = sm.findtext("sm:lastmod", default="", namespaces=ns) or sm.findtext("lastmod", default="")
            records.append(
                DiscoveryRecord.create(
                    source_name=source_name,
                    discovered_url=loc.strip(),
                    discovery_method="sitemap",
                    discovered_title=None,
                    source_timestamp=lastmod.strip() if lastmod else None,
                    discovered_at=discovered_at,
                )
            )
    else:
        elements = root.findall("sm:url", ns) or root.findall("url")
        for url in elements:
            loc = url.findtext("sm:loc", default="", namespaces=ns) or url.findtext("loc", default="")
            if not loc:
                continue
            lastmod = url.findtext("sm:lastmod", default="", namespaces=ns) or url.findtext("lastmod", default="")
            records.append(
                DiscoveryRecord.create(
                    source_name=source_name,
                    discovered_url=loc.strip(),
                    discovery_method="sitemap",
                    discovered_title=None,
                    source_timestamp=lastmod.strip() if lastmod else None,
                    discovered_at=discovered_at,
                )
            )

    return records


def main():
    parser = argparse.ArgumentParser(description="Unified Discovery Record Generator")
    parser.add_argument("--format", choices=["html", "rss", "sitemap"], default="html")
    parser.add_argument("--file", help="Path to fixture file")
    args = parser.parse_args()

    target_file = args.file
    if not target_file:
        if args.format == "html":
            target_file = DEFAULT_HTML_FIXTURE
        elif args.format == "rss":
            target_file = DEFAULT_FEED_FIXTURE
        else:
            target_file = DEFAULT_SITEMAP_FIXTURE

    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    if args.format == "html":
        records = discover_from_html_content(content)
    elif args.format == "rss":
        records = discover_from_rss_content(content)
    else:
        records = discover_from_sitemap_content(content)

    print(json.dumps([r.to_dict() for r in records], indent=2))


if __name__ == "__main__":
    main()
