#!/usr/bin/env python3
"""incremental_store.py - Incremental Collection & Change Detection Store (Assignment 4)

Tracks item versions using cryptographic content hashes (SHA-256) and lifecycle timestamps:
- first_seen_at
- last_seen_at
- fetched_at

Distinguishes:
- NEW: Item URL never seen in database before
- CHANGED: Item URL exists, but semantic content hash differs
- UNCHANGED: Item URL exists and content hash matches exactly
- NOT_SEEN_THIS_RUN: Item URL exists in DB but was absent from current listing (RETAINED, never deleted)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple


class ItemStatus(str, Enum):
    NEW = "new"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
    NOT_SEEN_THIS_RUN = "not_seen_this_run"


VOLATILE_FIELDS = {
    "fetched_at",
    "discovered_at",
    "first_seen_at",
    "last_seen_at",
    "source_timestamp",
    "sl_no",
    "counter",
    "status",
    "http_status",
    "response_time_ms",
}


def compute_content_hash(payload: Dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash over normalized semantic fields.

    Volatile timestamps, crawl metrics, and unstable serial counters are excluded.
    """
    stable_dict: Dict[str, Any] = {}
    for key, val in payload.items():
        if key in VOLATILE_FIELDS:
            continue
        if val is None:
            stable_dict[key] = None
        elif isinstance(val, (list, set)):
            stable_dict[key] = sorted(str(v).strip() for v in val)
        elif isinstance(val, dict):
            stable_dict[key] = {
                k: str(v).strip() if v is not None else None
                for k, v in sorted(val.items())
                if k not in VOLATILE_FIELDS
            }
        elif isinstance(val, str):
            stable_dict[key] = " ".join(val.split()).strip()
        else:
            stable_dict[key] = val

    canonical_json = json.dumps(stable_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class IncrementalStore:
    """SQLite-backed incremental store managing content hashes and run classifications."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._current_run_seen_urls: Set[str] = set()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS incremental_items (
                    item_url      TEXT PRIMARY KEY,
                    source_name   TEXT NOT NULL,
                    content_hash  TEXT NOT NULL,
                    title         TEXT,
                    payload_json  TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at  TEXT NOT NULL,
                    fetched_at    TEXT NOT NULL
                );
            """)

    def close(self) -> None:
        self._conn.close()

    def begin_run(self) -> None:
        self._current_run_seen_urls.clear()

    def process_item(
        self,
        item_url: str,
        payload: Dict[str, Any],
        source_name: str = "jnu_events",
        run_timestamp: Optional[str] = None,
    ) -> ItemStatus:
        """Classify item as NEW, CHANGED, or UNCHANGED and update persistent record."""
        now_iso = run_timestamp or datetime.now(timezone.utc).isoformat()
        current_hash = compute_content_hash(payload)
        title = payload.get("title")
        payload_str = json.dumps(payload, sort_keys=True, default=str)

        self._current_run_seen_urls.add(item_url)

        cur = self._conn.cursor()
        cur.execute("SELECT content_hash, first_seen_at FROM incremental_items WHERE item_url = ?", (item_url,))
        row = cur.fetchone()

        if row is None:
            # NEW
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO incremental_items (
                        item_url, source_name, content_hash, title, payload_json,
                        first_seen_at, last_seen_at, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item_url, source_name, current_hash, title, payload_str, now_iso, now_iso, now_iso),
                )
            return ItemStatus.NEW
        else:
            old_hash = row["content_hash"]
            first_seen = row["first_seen_at"]
            if old_hash != current_hash:
                # CHANGED
                with self._conn:
                    self._conn.execute(
                        """
                        UPDATE incremental_items SET
                            content_hash = ?,
                            title = ?,
                            payload_json = ?,
                            last_seen_at = ?,
                            fetched_at = ?
                        WHERE item_url = ?
                        """,
                        (current_hash, title, payload_str, now_iso, now_iso, item_url),
                    )
                return ItemStatus.CHANGED
            else:
                # UNCHANGED
                with self._conn:
                    self._conn.execute(
                        """
                        UPDATE incremental_items SET
                            last_seen_at = ?,
                            fetched_at = ?
                        WHERE item_url = ?
                        """,
                        (now_iso, now_iso, item_url),
                    )
                return ItemStatus.UNCHANGED

    def get_not_seen_urls(self, source_name: Optional[str] = None) -> List[str]:
        """Return URLs in database that were not seen during this run."""
        cur = self._conn.cursor()
        if source_name:
            cur.execute("SELECT item_url FROM incremental_items WHERE source_name = ?", (source_name,))
        else:
            cur.execute("SELECT item_url FROM incremental_items")
        all_urls = [r["item_url"] for r in cur.fetchall()]
        return [u for u in all_urls if u not in self._current_run_seen_urls]

    def summarize_run(
        self,
        counts: Dict[str, int],
        source_name: Optional[str] = None,
    ) -> Dict[str, int]:
        """Add not_seen_this_run count to run metrics."""
        not_seen = len(self.get_not_seen_urls(source_name))
        return {
            "new": counts.get("new", 0),
            "changed": counts.get("changed", 0),
            "unchanged": counts.get("unchanged", 0),
            "not_seen_this_run": not_seen,
        }

    def get_item(self, item_url: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM incremental_items WHERE item_url = ?", (item_url,))
        row = cur.fetchone()
        return dict(row) if row else None
