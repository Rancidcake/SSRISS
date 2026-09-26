#!/usr/bin/env python3
"""
Assignment 07 - Persistence & Deduplication Layer
Implements SQLite storage for monitored notice items with SHA-256 content hashing,
idempotent upserts, and change detection (first_seen_at vs last_seen_at).
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "jnu_monitor.db")


def compute_content_hash(item: Dict[str, Any]) -> str:
    """
    Computes a deterministic SHA-256 hash over normalized content fields.
    """
    title = item.get("title") or ""
    event_start = item.get("event_start") or ""
    raw_text = item.get("raw_text") or ""
    item_type = item.get("item_type") or ""

    payload = f"{title}|{event_start}|{raw_text}|{item_type}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def init_db(db_path: str = DEFAULT_DB_PATH):
    """
    Initializes SQLite database and creates monitored_items table if not present.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitored_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_url TEXT UNIQUE NOT NULL,
            source_name TEXT,
            item_type TEXT,
            title TEXT,
            event_start TEXT,
            raw_text TEXT,
            content_hash TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_url ON monitored_items(item_url)")
    conn.commit()
    conn.close()


def get_item(db_path: str, item_url: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a stored record dictionary by item_url, or None if missing.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitored_items WHERE item_url = ?", (item_url,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def upsert_item(db_path: str, item: Dict[str, Any], current_time: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Idempotently upserts a normalized item into the SQLite database.
    
    Returns:
        Tuple[action_status, record_dict]
        where action_status is one of: 'inserted', 'updated', 'unchanged'
    """
    item_url = item.get("item_url")
    if not item_url:
        raise ValueError("Cannot upsert item without a valid item_url.")

    now_iso = current_time if current_time else datetime.now(IST).isoformat()
    content_hash = compute_content_hash(item)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, content_hash, first_seen_at FROM monitored_items WHERE item_url = ?", (item_url,))
    existing = cursor.fetchone()

    if existing is None:
        # Case 1: Brand new item
        cursor.execute("""
            INSERT INTO monitored_items (
                item_url, source_name, item_type, title, event_start,
                raw_text, content_hash, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_url,
            item.get("source_name", "jnu_official_notices"),
            item.get("item_type", "html_notice"),
            item.get("title", ""),
            item.get("event_start"),
            item.get("raw_text", ""),
            content_hash,
            now_iso,
            now_iso
        ))
        conn.commit()
        conn.close()
        return "inserted", get_item(db_path, item_url)

    elif existing["content_hash"] == content_hash:
        # Case 2: Unchanged content -> update last_seen_at timestamp only
        cursor.execute("""
            UPDATE monitored_items
            SET last_seen_at = ?
            WHERE item_url = ?
        """, (now_iso, item_url))
        conn.commit()
        conn.close()
        return "unchanged", get_item(db_path, item_url)

    else:
        # Case 3: Content changed -> update fields, hash, and last_seen_at
        cursor.execute("""
            UPDATE monitored_items
            SET source_name = ?,
                item_type = ?,
                title = ?,
                event_start = ?,
                raw_text = ?,
                content_hash = ?,
                last_seen_at = ?
            WHERE item_url = ?
        """, (
            item.get("source_name", "jnu_official_notices"),
            item.get("item_type", "html_notice"),
            item.get("title", ""),
            item.get("event_start"),
            item.get("raw_text", ""),
            content_hash,
            now_iso,
            item_url
        ))
        conn.commit()
        conn.close()
        return "updated", get_item(db_path, item_url)


def run_storage_pipeline(jsonl_path: str, db_path: str = DEFAULT_DB_PATH) -> Dict[str, int]:
    """
    Reads normalized JSONL records and upserts them into the database,
    returning telemetry counts.
    """
    init_db(db_path)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            status, _ = upsert_item(db_path, item)
            counts[status] += 1

    return counts


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    jsonl_file = os.path.join(script_dir, "..", "06_normalization", "jnu_normalized.jsonl")
    db_file = os.path.join(script_dir, "jnu_monitor.db")

    if os.path.exists(db_file):
        os.remove(db_file)  # Clean state for initial execution test

    print("[*] Initializing database...")
    init_db(db_file)

    print("[*] Executing Run 1...")
    stats1 = run_storage_pipeline(jsonl_file, db_file)
    print(f"    Run 1 Results: {stats1}")

    print("[*] Executing Run 2 (Rerun without changes)...")
    stats2 = run_storage_pipeline(jsonl_file, db_file)
    print(f"    Run 2 Results: {stats2}")
