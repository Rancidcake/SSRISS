#!/usr/bin/env python3
"""inspect_sitemap.py - XML Sitemap Inspector (Assignment 1A)

Parses standard XML sitemaps and sitemap indexes according to sitemaps.org.
Prints a controlled sample of:
- URL
- title (None for sitemaps as title is not in protocol)
- published/updated/lastmod (if available)
- discovery source
"""

import argparse
import os
import sys
from typing import Any, Dict, List
import urllib.request
import xml.etree.ElementTree as ET

DEFAULT_SITEMAP_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_sitemap.xml")

XML_NAMESPACES = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}


def inspect_sitemap(sitemap_source: str, max_items: int = 5) -> List[Dict[str, Any]]:
    """Parse XML sitemap or sitemap index from file or URL."""
    try:
        if sitemap_source.startswith(("http://", "https://")):
            req = urllib.request.Request(sitemap_source, headers={"User-Agent": "SSRISS-Monitor/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                tree = ET.parse(resp)
        else:
            tree = ET.parse(sitemap_source)
    except Exception as exc:
        print(f"[ERROR] Failed to parse sitemap: {exc}", file=sys.stderr)
        return []

    root = tree.getroot()
    records = []

    # Check if sitemapindex or urlset
    tag_clean = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    if tag_clean == "sitemapindex":
        for sm in root.findall("sm:sitemap", XML_NAMESPACES) or root.findall("sitemap"):
            loc = sm.findtext("sm:loc", default="", namespaces=XML_NAMESPACES) or sm.findtext("loc", default="")
            lastmod = sm.findtext("sm:lastmod", default="", namespaces=XML_NAMESPACES) or sm.findtext("lastmod", default="")
            records.append({
                "URL": loc.strip(),
                "title": None,
                "published/updated/lastmod": lastmod.strip() if lastmod else None,
                "discovery source": "sitemap_index",
            })
            if len(records) >= max_items:
                break
    else:
        for url in root.findall("sm:url", XML_NAMESPACES) or root.findall("url"):
            loc = url.findtext("sm:loc", default="", namespaces=XML_NAMESPACES) or url.findtext("loc", default="")
            lastmod = url.findtext("sm:lastmod", default="", namespaces=XML_NAMESPACES) or url.findtext("lastmod", default="")
            records.append({
                "URL": loc.strip(),
                "title": None,
                "published/updated/lastmod": lastmod.strip() if lastmod else None,
                "discovery source": "xml_sitemap",
            })
            if len(records) >= max_items:
                break

    return records


def main():
    parser = argparse.ArgumentParser(description="Inspect an XML sitemap for URL discovery.")
    parser.add_argument("sitemap", nargs="?", default=DEFAULT_SITEMAP_FIXTURE, help="Sitemap URL or file path")
    parser.add_argument("--limit", type=int, default=5, help="Maximum items to display")
    args = parser.parse_args()

    print(f"=== XML Sitemap Inspection: {args.sitemap} ===")
    results = inspect_sitemap(args.sitemap, max_items=args.limit)
    for idx, r in enumerate(results, 1):
        print(f"\nItem #{idx}:")
        for k, v in r.items():
            print(f"  {k}: {v}")
    print(f"\nDiscovered {len(results)} items via XML Sitemap.")


if __name__ == "__main__":
    main()
