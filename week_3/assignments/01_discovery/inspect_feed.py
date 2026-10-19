#!/usr/bin/env python3
"""inspect_feed.py - Feed Discovery Inspector (Assignment 1A)

Parses RSS / Atom syndication feeds to discover candidate event items.
Prints a controlled sample of:
- URL
- title (if available)
- published/updated timestamp (if available)
- discovery source
"""

import argparse
import os
import sys
from typing import Any, Dict, List
import feedparser  # type: ignore

DEFAULT_FEED_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed.xml")


def inspect_feed(feed_source: str, max_items: int = 5) -> List[Dict[str, Any]]:
    """Parse feed from URL or local file path, returning normalized candidate summaries."""
    feed = feedparser.parse(feed_source)

    if feed.bozo and not feed.entries:
        print(f"[ERROR] Failed to parse feed: {feed.bozo_exception}", file=sys.stderr)
        return []

    records = []
    for entry in feed.entries[:max_items]:
        url = entry.get("link") or entry.get("id") or ""
        title = entry.get("title")
        timestamp = (
            entry.get("published")
            or entry.get("updated")
            or entry.get("pubDate")
        )
        record = {
            "URL": url.strip(),
            "title": title.strip() if title else None,
            "published/updated": timestamp.strip() if timestamp else None,
            "discovery source": "rss_feed",
        }
        records.append(record)
    return records


def main():
    parser = argparse.ArgumentParser(description="Inspect an RSS/Atom feed for event discovery.")
    parser.add_argument("feed", nargs="?", default=DEFAULT_FEED_FIXTURE, help="Feed URL or file path")
    parser.add_argument("--limit", type=int, default=5, help="Maximum items to display")
    args = parser.parse_args()

    print(f"=== Feed Discovery Inspection: {args.feed} ===")
    results = inspect_feed(args.feed, max_items=args.limit)
    for idx, r in enumerate(results, 1):
        print(f"\nItem #{idx}:")
        for k, v in r.items():
            print(f"  {k}: {v}")
    print(f"\nDiscovered {len(results)} items via RSS/Atom feed.")


if __name__ == "__main__":
    main()
