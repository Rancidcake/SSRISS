"""
Shared record schema for all sources, plus small text/date helpers that every
adapter can reuse.

Each content type has a fixed set of fields. `build_record` fills defaults,
drops nothing silently, and refuses records missing required fields - so two
different institutions produce rows with identical field names.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from src.errors import SchemaError

IST = timezone(timedelta(hours=5, minutes=30))

# Fields every record has, regardless of type. Provenance + identity.
COMMON_FIELDS: dict[str, Any] = {
    "source_name": None,    # provenance: which adapter produced it
    "source_url": None,     # provenance: listing page the item was discovered on
    "item_url": None,       # IDENTITY: stable per item, used for dedup
    "item_type": None,
    "raw_text": None,       # provenance: original text before normalization
    "fetched_at": None,
    "http_status": None,
}

TYPE_FIELDS: dict[str, dict[str, Any]] = {
    "event": {
        "title": None,
        "event_start": None,
        "event_end": None,
        "location": None,
        "speakers": [],
        "organizations": [],
        "description": None,
    },
    "announcement": {
        "title": None,
        "published_at": None,
        "organizations": [],
        "description": None,
    },
    "faculty": {
        "name": None,
        "title": None,
        "department": None,
        "bio": None,
        "research_areas": [],
    },
}

REQUIRED = {
    "event": ["source_name", "item_url", "item_type", "title"],
    "announcement": ["source_name", "item_url", "item_type", "title"],
    "faculty": ["source_name", "item_url", "item_type", "name"],
}

# Source-specific leftovers go here instead of becoming new top-level columns.
EXTRA_KEY = "extra"


def build_record(item_type: str, **values: Any) -> dict[str, Any]:
    if item_type not in TYPE_FIELDS:
        raise SchemaError(f"unknown item_type {item_type!r}")

    fields = {**COMMON_FIELDS, **TYPE_FIELDS[item_type]}
    record: dict[str, Any] = {}
    for key, default in fields.items():
        value = values.pop(key, None)
        if value is None:
            value = list(default) if isinstance(default, list) else default
        record[key] = value
    record["item_type"] = item_type

    extra = values.pop(EXTRA_KEY, None) or {}
    extra.update(values)  # anything unknown is kept, but not as a column
    record[EXTRA_KEY] = extra

    validate(record)
    return record


def validate(record: dict[str, Any]) -> None:
    item_type = record.get("item_type")
    if item_type not in REQUIRED:
        raise SchemaError(f"unknown item_type {item_type!r}")
    missing = [f for f in REQUIRED[item_type] if not record.get(f)]
    if missing:
        raise SchemaError(f"record missing required fields {missing}: item_url={record.get('item_url')}")
    for key, default in TYPE_FIELDS[item_type].items():
        if isinstance(default, list) and not isinstance(record.get(key), list):
            raise SchemaError(f"field {key!r} must be a list")


# ---- helpers shared by adapters -------------------------------------------

def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value: str | None) -> str | None:
    """Return YYYY-MM-DD for the date formats seen on academic sites, else None."""
    if not value:
        return None
    text = clean_text(value)

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        y, mo, d = m.groups()
        return _iso(y, mo, d)

    m = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", text)  # DD-MM-YYYY (Indian order)
    if m:
        d, mo, y = m.groups()
        return _iso(y, mo, d)

    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)[,]?\s+(\d{4})", text)
    if m:
        d, month_name, y = m.groups()
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(f"{d} {month_name} {y}", fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def _iso(y: str, mo: str, d: str) -> str | None:
    try:
        return datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")
