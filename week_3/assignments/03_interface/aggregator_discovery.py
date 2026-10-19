#!/usr/bin/env python3
"""aggregator_discovery.py - Aggregator Discovery Interface & Adapters (Assignment 3)

Defines a clean, unified discovery layer:
- BaseDiscoveryAdapter (Abstract Base Class)
- HtmlListingDiscoveryAdapter
- FeedDiscoveryAdapter
- SitemapDiscoveryAdapter
- UnifiedAggregatorDiscovery

Every discovery result adheres to the canonical shape:
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

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional
import urllib.parse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import feedparser  # type: ignore

# Add assignments/02_scope to path for scope filter
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCOPE_DIR = os.path.abspath(os.path.join(_HERE, "..", "02_scope"))
if _SCOPE_DIR not in sys.path:
    sys.path.insert(0, _SCOPE_DIR)

try:
    from scope_filter import UrlScopeFilter, canonicalize_url, is_allowed_item_url
except ImportError:
    UrlScopeFilter = None  # type: ignore
    canonicalize_url = lambda u, c=None: u.strip()  # type: ignore
    is_allowed_item_url = lambda u, c=None: True  # type: ignore

DISCOVERY_SCHEMA_KEYS = {
    "source_name",
    "discovered_url",
    "discovery_method",
    "discovered_title",
    "source_timestamp",
    "discovered_at",
}


def _make_record(
    source_name: str,
    url: str,
    method: str,
    title: Optional[str] = None,
    timestamp: Optional[str] = None,
    discovered_at: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "source_name": source_name,
        "discovered_url": url.strip(),
        "discovery_method": method,
        "discovered_title": title.strip() if title else None,
        "source_timestamp": timestamp.strip() if timestamp else None,
        "discovered_at": discovered_at or datetime.now(timezone.utc).isoformat(),
    }


class BaseDiscoveryAdapter(ABC):
    """Abstract interface for all discovery adapters."""

    def __init__(self, source_config: Dict[str, Any]) -> None:
        self.config = source_config
        self.source_name = source_config.get("source_name", "unknown_source")
        self.scope_filter = UrlScopeFilter(source_config) if UrlScopeFilter else None

    @abstractmethod
    def discover(self, content: str, **kwargs) -> List[Dict[str, Any]]:
        """Parse raw content and yield normalized discovery items."""
        pass


class HtmlListingDiscoveryAdapter(BaseDiscoveryAdapter):
    """Discovers items from central HTML table or card listings."""

    def discover(self, content: str, **kwargs) -> List[Dict[str, Any]]:
        base_url = kwargs.get("base_url") or self.config.get("base_url", "https://www.jnu.ac.in")
        discovered_at = kwargs.get("discovered_at")
        soup = BeautifulSoup(content, "html.parser")
        results: List[Dict[str, Any]] = []

        # JNU Drupal View table layout: div.view-id-jnu_events, table.views-table
        rows = soup.select("table.views-table tr, tr.marquee-row, tr")
        for row in rows:
            title_cell = row.select_one("td.views-field-title") or row.find("td")
            if not title_cell:
                continue
            link = title_cell.find("a", href=True) or row.find("a", href=True)
            if not link:
                continue

            raw_url = urllib.parse.urljoin(base_url, link["href"].strip())
            canonical = canonicalize_url(raw_url, self.config)

            if self.scope_filter and not self.scope_filter.accept(canonical):
                continue

            title = link.get_text(strip=True) or title_cell.get_text(strip=True)
            time_el = row.select_one("time") or row.select_one("td.views-field-field-event-from-date")
            ts = time_el.get("datetime") or time_el.get_text(strip=True) if time_el else None

            results.append(_make_record(
                source_name=self.source_name,
                url=canonical,
                method="html_listing",
                title=title,
                timestamp=ts,
                discovered_at=discovered_at,
            ))

        # Fallback card selectors
        if not results:
            for card in soup.select("div.event-card, article.node, div.views-row"):
                link = card.find("a", href=True)
                if not link:
                    continue
                raw_url = urllib.parse.urljoin(base_url, link["href"].strip())
                canonical = canonicalize_url(raw_url, self.config)
                if self.scope_filter and not self.scope_filter.accept(canonical):
                    continue

                title = (card.select_one("h2, h3, h4, .title") or link).get_text(strip=True)
                time_el = card.find("time")
                ts = time_el.get("datetime") if time_el else None
                results.append(_make_record(
                    source_name=self.source_name,
                    url=canonical,
                    method="html_listing",
                    title=title,
                    timestamp=ts,
                    discovered_at=discovered_at,
                ))

        return results


class FeedDiscoveryAdapter(BaseDiscoveryAdapter):
    """Discovers items from RSS 2.0 or Atom feeds."""

    def discover(self, content: str, **kwargs) -> List[Dict[str, Any]]:
        discovered_at = kwargs.get("discovered_at")
        feed = feedparser.parse(content)
        results: List[Dict[str, Any]] = []

        for entry in feed.entries:
            raw_url = entry.get("link") or entry.get("id") or ""
            if not raw_url:
                continue

            canonical = canonicalize_url(raw_url, self.config)
            if self.scope_filter and not self.scope_filter.accept(canonical):
                continue

            title = entry.get("title")
            ts = entry.get("published") or entry.get("updated") or entry.get("pubDate")

            results.append(_make_record(
                source_name=self.source_name,
                url=canonical,
                method="rss",
                title=title,
                timestamp=ts,
                discovered_at=discovered_at,
            ))

        return results


class SitemapDiscoveryAdapter(BaseDiscoveryAdapter):
    """Discovers items from XML Sitemaps and Sitemap Indexes."""

    def discover(self, content: str, **kwargs) -> List[Dict[str, Any]]:
        discovered_at = kwargs.get("discovered_at")
        root = ET.fromstring(content)
        results: List[Dict[str, Any]] = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag == "sitemapindex":
            elements = root.findall("sm:sitemap", ns) or root.findall("sitemap")
            for sm in elements:
                loc = sm.findtext("sm:loc", default="", namespaces=ns) or sm.findtext("loc", default="")
                if not loc:
                    continue
                canonical = canonicalize_url(loc, self.config)
                if self.scope_filter and not self.scope_filter.accept(canonical):
                    continue
                lastmod = sm.findtext("sm:lastmod", default="", namespaces=ns) or sm.findtext("lastmod", default="")
                results.append(_make_record(
                    source_name=self.source_name,
                    url=canonical,
                    method="sitemap",
                    title=None,
                    timestamp=lastmod,
                    discovered_at=discovered_at,
                ))
        else:
            elements = root.findall("sm:url", ns) or root.findall("url")
            for url_el in elements:
                loc = url_el.findtext("sm:loc", default="", namespaces=ns) or url_el.findtext("loc", default="")
                if not loc:
                    continue
                canonical = canonicalize_url(loc, self.config)
                if self.scope_filter and not self.scope_filter.accept(canonical):
                    continue
                lastmod = url_el.findtext("sm:lastmod", default="", namespaces=ns) or url_el.findtext("lastmod", default="")
                results.append(_make_record(
                    source_name=self.source_name,
                    url=canonical,
                    method="sitemap",
                    title=None,
                    timestamp=lastmod,
                    discovered_at=discovered_at,
                ))

        return results


# ---------------------------------------------------------------------------
# Functional Interface
# ---------------------------------------------------------------------------

def discover_from_html(html: str, source_config: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
    adapter = HtmlListingDiscoveryAdapter(source_config)
    return adapter.discover(html, **kwargs)


def discover_from_feed(feed_content: str, source_config: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
    adapter = FeedDiscoveryAdapter(source_config)
    return adapter.discover(feed_content, **kwargs)


def discover_from_sitemap(sitemap_content: str, source_config: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
    adapter = SitemapDiscoveryAdapter(source_config)
    return adapter.discover(sitemap_content, **kwargs)


def discover_items(source_config: Dict[str, Any], content: str, format_type: str = "html", **kwargs) -> List[Dict[str, Any]]:
    """Generic high-level router function discovering items according to format_type."""
    if format_type in ("html", "html_listing"):
        return discover_from_html(content, source_config, **kwargs)
    elif format_type in ("rss", "atom", "feed"):
        return discover_from_feed(content, source_config, **kwargs)
    elif format_type in ("sitemap", "xml"):
        return discover_from_sitemap(content, source_config, **kwargs)
    else:
        raise ValueError(f"Unsupported discovery format: {format_type}")
