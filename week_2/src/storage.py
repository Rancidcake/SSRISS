"""
Shared SQLite storage for every source and content type.

- One `items` table. `item_url` is the identity (UNIQUE), so re-running a crawl
  or seeing the same item on two pages never creates a second row.
- A content hash over the *content* fields (not provenance such as fetched_at
  or which page the item was found on) decides new / changed / existing.
- Each run's writes happen in ONE transaction: if anything fails midway, the
  whole batch is rolled back and the existing data is untouched.
- A `runs` table keeps a history of every run (status, failing stage, counts).

To swap SQLite for something else, only this file changes.
"""

import hashlib
import json
import os
import sqlite3
from typing import Any

from src.errors import StorageError
from src.schema import now_iso

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "monitor.db")

# Provenance fields: they describe *how/when* we saw the item, not the item itself.
NON_CONTENT_FIELDS = {"source_name", "source_url", "fetched_at", "http_status", "first_seen_at", "last_seen_at"}
NON_CONTENT_EXTRA = {"discovered_on", "detail_status"}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    item_url      TEXT UNIQUE NOT NULL,
    source_name   TEXT NOT NULL,
    item_type     TEXT NOT NULL,
    title         TEXT,
    primary_date  TEXT,
    content_hash  TEXT NOT NULL,
    record_json   TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source_name, item_type);

CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT NOT NULL,
    source_name  TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL,
    failed_stage TEXT,
    error        TEXT,
    pages        INTEGER DEFAULT 0,
    parsed       INTEGER DEFAULT 0,
    new          INTEGER DEFAULT 0,
    changed      INTEGER DEFAULT 0,
    existing     INTEGER DEFAULT 0
);
"""


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    try:
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)
        return conn
    except (sqlite3.Error, OSError) as e:
        raise StorageError(f"cannot open database {db_path}: {type(e).__name__}: {e}")


def content_hash(record: dict[str, Any]) -> str:
    content = {k: v for k, v in record.items() if k not in NON_CONTENT_FIELDS and k != "extra"}
    extra = {k: v for k, v in (record.get("extra") or {}).items() if k not in NON_CONTENT_EXTRA}
    payload = json.dumps({"c": content, "e": extra}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def store_records(db_path: str, records: list[dict[str, Any]], seen_at: str | None = None) -> dict[str, int]:
    """Upsert records atomically. Returns counts: new / changed / existing."""
    seen_at = seen_at or now_iso()
    counts = {"new": 0, "changed": 0, "existing": 0}
    conn = connect(db_path)
    try:
        with conn:  # one transaction: commit on success, rollback on any exception
            for record in records:
                counts[_upsert(conn, record, seen_at)] += 1
    except sqlite3.Error as e:
        raise StorageError(f"write failed, transaction rolled back: {type(e).__name__}: {e}")
    finally:
        conn.close()
    return counts


def _upsert(conn: sqlite3.Connection, record: dict[str, Any], seen_at: str) -> str:
    url = record["item_url"]
    h = content_hash(record)
    title = record.get("title") or record.get("name")
    primary_date = record.get("event_start") or record.get("published_at")
    row = conn.execute("SELECT content_hash, first_seen_at FROM items WHERE item_url = ?", (url,)).fetchone()

    if row is None:
        stored = {**record, "first_seen_at": seen_at, "last_seen_at": seen_at}
        conn.execute(
            "INSERT INTO items (item_url, source_name, item_type, title, primary_date, content_hash,"
            " record_json, first_seen_at, last_seen_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (url, record["source_name"], record["item_type"], title, primary_date, h,
             json.dumps(stored, ensure_ascii=False), seen_at, seen_at),
        )
        return "new"

    stored = {**record, "first_seen_at": row["first_seen_at"], "last_seen_at": seen_at}
    if row["content_hash"] == h:
        conn.execute(
            "UPDATE items SET last_seen_at = ?, record_json = ? WHERE item_url = ?",
            (seen_at, json.dumps(stored, ensure_ascii=False), url),
        )
        return "existing"

    conn.execute(
        "UPDATE items SET title = ?, primary_date = ?, content_hash = ?, record_json = ?, last_seen_at = ?"
        " WHERE item_url = ?",
        (title, primary_date, h, json.dumps(stored, ensure_ascii=False), seen_at, url),
    )
    return "changed"


def get_items(db_path: str, source_name: str | None = None) -> list[dict[str, Any]]:
    conn = connect(db_path)
    try:
        if source_name:
            rows = conn.execute("SELECT record_json FROM items WHERE source_name = ? ORDER BY id", (source_name,))
        else:
            rows = conn.execute("SELECT record_json FROM items ORDER BY id")
        return [json.loads(r["record_json"]) for r in rows]
    finally:
        conn.close()


def count_items(db_path: str, source_name: str | None = None) -> int:
    conn = connect(db_path)
    try:
        if source_name:
            return conn.execute("SELECT COUNT(*) FROM items WHERE source_name = ?", (source_name,)).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    finally:
        conn.close()


def record_run(db_path: str, run: dict[str, Any]) -> None:
    """Best effort: a broken DB must not hide the original failure."""
    try:
        conn = connect(db_path)
        with conn:
            conn.execute(
                "INSERT INTO runs (run_id, source_name, started_at, finished_at, status, failed_stage, error,"
                " pages, parsed, new, changed, existing) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (run["run_id"], run["source_name"], run["started_at"], run.get("finished_at"), run["status"],
                 run.get("failed_stage"), run.get("error"), run.get("pages", 0), run.get("parsed", 0),
                 run.get("new", 0), run.get("changed", 0), run.get("existing", 0)),
            )
        conn.close()
    except (StorageError, sqlite3.Error):
        pass
