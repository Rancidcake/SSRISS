#!/usr/bin/env python3
"""scope_filter.py - URL Scope Filter & Frontier Boundary (Assignment 2)

Implements a configurable crawl-frontier boundary that decides whether a
discovered URL is allowed to enter the collection pipeline.

Key Concepts Implemented:
- Allowlist rules (hostname, path prefixes, excluded path prefixes)
- Same-site vs external link control
- URL canonicalization (scheme normalization, fragment stripping, tracking parameter stripping)
- Duplicate / visited-URL tracking
- Prevention of calendar / search / filter / infinite URL loops
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set

_BINARY_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".zip", ".rar", ".tar", ".gz",
    ".mp3", ".mp4", ".avi", ".mkv",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
    ".css", ".js",
}

DEFAULT_IGNORED_PARAMS = [
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "feature",
]


def canonicalize_url(url: str, config: Optional[Dict[str, Any]] = None) -> str:
    """Return a stable canonical form of *url* for deduplication.

    1. Strip whitespace.
    2. Normalize scheme and netloc to lowercase.
    3. Remove fragments (#...).
    4. Remove tracking / ignored query parameters.
    5. Strip trailing slash on path (unless path is empty or root).
    """
    if not url:
        return ""

    cfg = config or {}
    try:
        parts = urllib.parse.urlsplit(url.strip())
    except Exception:
        return url.strip()

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    # Normalize host aliases for JNU (jnu.ac.in -> www.jnu.ac.in)
    if netloc == "jnu.ac.in":
        netloc = "www.jnu.ac.in"

    path = parts.path
    if path and path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Query cleaning
    if cfg.get("strip_all_query_params", False):
        query = ""
    else:
        ignored = set(cfg.get("ignored_query_params", DEFAULT_IGNORED_PARAMS))
        params = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in params if k.lower() not in ignored]
        query = urllib.parse.urlencode(filtered)

    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


def is_allowed_item_url(url: str, source_config: Dict[str, Any]) -> bool:
    """Determine whether a candidate URL is permissible under source_config."""
    if not url or not isinstance(url, str):
        return False

    url_str = url.strip()
    if not url_str.startswith(("http://", "https://")):
        return False

    try:
        parts = urllib.parse.urlsplit(url_str)
    except Exception:
        return False

    netloc = parts.netloc.lower()
    # Normalize JNU host alias
    if netloc == "jnu.ac.in":
        netloc = "www.jnu.ac.in"

    allowed_host = source_config.get("allowed_hostname")
    allow_external = source_config.get("allow_external", False)

    # 1. Hostname boundary check
    if allowed_host:
        target_allowed = allowed_host.lower()
        if target_allowed == "jnu.ac.in":
            target_allowed = "www.jnu.ac.in"
        if netloc != target_allowed and not allow_external:
            return False

    # 2. Binary extension check
    path_lower = parts.path.lower()
    for ext in _BINARY_EXTENSIONS:
        if path_lower.endswith(ext):
            return False

    # 3. Excluded path prefixes (e.g. login, admin, search, user)
    excluded_prefixes = source_config.get("excluded_path_prefixes", [])
    for prefix in excluded_prefixes:
        if path_lower.startswith(prefix.lower()):
            return False

    # 4. Denylist query parameter traps (calendar pagination loops, etc.)
    q_lower = parts.query.lower()
    if any(k in q_lower for k in ("calendar", "month=", "year=", "filter=")):
        return False

    # 5. Allowed path prefixes check
    allowed_prefixes = source_config.get("allowed_path_prefixes", [])
    if allowed_prefixes:
        matched = any(path_lower.startswith(p.lower()) for p in allowed_prefixes)
        if not matched:
            return False

    return True


class UrlScopeFilter:
    """Stateful crawl frontier boundary enforcing deduplication and scope policies."""

    def __init__(self, source_config: Dict[str, Any]) -> None:
        self.config = source_config
        self.seen_canonical_urls: Set[str] = set()

    def canonicalize(self, url: str) -> str:
        return canonicalize_url(url, self.config)

    def is_allowed(self, url: str) -> bool:
        return is_allowed_item_url(url, self.config)

    def is_duplicate(self, url: str) -> bool:
        canonical = self.canonicalize(url)
        return canonical in self.seen_canonical_urls

    def accept(self, url: str) -> bool:
        """Check if URL is allowed and not yet seen; if accepted, mark as seen."""
        if not self.is_allowed(url):
            return False
        canonical = self.canonicalize(url)
        if canonical in self.seen_canonical_urls:
            return False
        self.seen_canonical_urls.add(canonical)
        return True

    def reset(self) -> None:
        self.seen_canonical_urls.clear()
