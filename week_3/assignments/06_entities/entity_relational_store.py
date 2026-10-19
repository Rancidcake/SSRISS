#!/usr/bin/env python3
"""entity_relational_store.py - Entity Storage and Relationships (Assignment 6)

Extends SQLite storage to model many-to-many relationships between Events (Items),
People, and Organizations using dedicated join tables with provenance tracking.

Relational Model
----------------
items (events)           people                 organizations
--------------           ------                 -------------
id (PK)                  id (PK)                id (PK)
item_url (UNIQUE)        normalized_name (UQ)   normalized_name (UQ)
item_type                display_name           display_name
title                    created_at             created_at
source_name
raw_text
created_at
      │                        │                       │
      │ 1                      │ 1                     │ 1
      ├───────────┐            │                       │
      │           │            │                       │
      │ N         │ N          │ N                     │ N
item_people   item_organizations
-----------   ------------------
item_id  (FK) item_id         (FK)
person_id(FK) organization_id (FK)
role          role
affiliation   source_text
source_text
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple

# Enable import of entity extractor from 05_extraction
_HERE = os.path.dirname(os.path.abspath(__file__))
_EXTRACTOR_DIR = os.path.abspath(os.path.join(_HERE, "..", "05_extraction"))
if _EXTRACTOR_DIR not in sys.path:
    sys.path.insert(0, _EXTRACTOR_DIR)

try:
    from entity_extractor import EventEntities, ExtractedPerson, ExtractedOrganization
except ImportError:
    EventEntities = None  # type: ignore


_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_url    TEXT UNIQUE NOT NULL,
    item_type   TEXT DEFAULT 'event',
    title       TEXT,
    source_name TEXT,
    raw_text    TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS people (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_name TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_name TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS item_people (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    person_id       INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    affiliation_raw TEXT,
    source_text     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE(item_id, person_id, role)
);

CREATE TABLE IF NOT EXISTS item_organizations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    source_text     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE(item_id, organization_id, role)
);

CREATE INDEX IF NOT EXISTS idx_item_people_person ON item_people(person_id);
CREATE INDEX IF NOT EXISTS idx_item_orgs_org ON item_organizations(organization_id);
"""

_HONORIFIC_REGEX = re.compile(
    r"^(?:prof(?:essor)?|dr|mr|ms|mrs|shri|smt|amb(?:assador)?)\.?\s+",
    re.IGNORECASE,
)


def normalize_person_name(name: str) -> str:
    """Strip honorifics, punctuation, and multiple spaces to build matching key."""
    clean = name.strip().lower()
    clean = _HONORIFIC_REGEX.sub("", clean).strip()
    clean = re.sub(r"[\.,]", " ", clean)
    return " ".join(clean.split())


def normalize_org_name(name: str) -> str:
    """Normalize organization name key for deduplication."""
    clean = name.strip().lower()
    clean = re.sub(r"[\.,]", " ", clean)
    return " ".join(clean.split())


class EntityRelationalStore:
    """SQLite-backed relational repository for events, people, and organizations."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.executescript(_DDL)

    def close(self) -> None:
        self._conn.close()

    def insert_item(
        self,
        item_url: str,
        title: Optional[str],
        source_name: str = "jnu_events",
        item_type: str = "event",
        raw_text: Optional[str] = None,
    ) -> int:
        """Insert or retrieve existing item record by item_url."""
        now_iso = datetime.now(timezone.utc).isoformat()
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM items WHERE item_url = ?", (item_url,))
        row = cur.fetchone()
        if row:
            return row["id"]

        with self._conn:
            cur.execute(
                """
                INSERT INTO items (item_url, item_type, title, source_name, raw_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item_url, item_type, title, source_name, raw_text, now_iso),
            )
            return cur.lastrowid

    def get_or_create_person(self, display_name: str) -> int:
        """Insert or retrieve person by normalized key."""
        now_iso = datetime.now(timezone.utc).isoformat()
        norm_key = normalize_person_name(display_name)
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM people WHERE normalized_name = ?", (norm_key,))
        row = cur.fetchone()
        if row:
            return row["id"]

        with self._conn:
            cur.execute(
                "INSERT INTO people (normalized_name, display_name, created_at) VALUES (?, ?, ?)",
                (norm_key, display_name.strip(), now_iso),
            )
            return cur.lastrowid

    def get_or_create_organization(self, display_name: str) -> int:
        """Insert or retrieve organization by normalized key."""
        now_iso = datetime.now(timezone.utc).isoformat()
        norm_key = normalize_org_name(display_name)
        cur = self._conn.cursor()
        cur.execute("SELECT id FROM organizations WHERE normalized_name = ?", (norm_key,))
        row = cur.fetchone()
        if row:
            return row["id"]

        with self._conn:
            cur.execute(
                "INSERT INTO organizations (normalized_name, display_name, created_at) VALUES (?, ?, ?)",
                (norm_key, display_name.strip(), now_iso),
            )
            return cur.lastrowid

    def link_item_person(
        self,
        item_id: int,
        person_id: int,
        role: str,
        affiliation_raw: Optional[str],
        source_text: str,
    ) -> None:
        """Link an item to a person with role and verbatim provenance."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO item_people (
                    item_id, person_id, role, affiliation_raw, source_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item_id, person_id, role, affiliation_raw, source_text, now_iso),
            )

    def link_item_organization(
        self,
        item_id: int,
        organization_id: int,
        role: str,
        source_text: str,
    ) -> None:
        """Link an item to an organization with role and verbatim provenance."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO item_organizations (
                    item_id, organization_id, role, source_text, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, organization_id, role, source_text, now_iso),
            )

    def store_event_with_entities(
        self,
        item_dict: Dict[str, Any],
        entities: Any,  # EventEntities instance
    ) -> int:
        """Store an event item and create all many-to-many entity relationships atomically."""
        item_id = self.insert_item(
            item_url=item_dict["item_url"],
            title=item_dict.get("title"),
            source_name=item_dict.get("source_name", "jnu_events"),
            item_type=item_dict.get("item_type", "event"),
            raw_text=item_dict.get("raw_text"),
        )

        for person in entities.people:
            p_id = self.get_or_create_person(person.name)
            self.link_item_person(
                item_id=item_id,
                person_id=p_id,
                role=person.role,
                affiliation_raw=person.affiliation_raw,
                source_text=person.source_text,
            )

        for org in entities.organizations:
            o_id = self.get_or_create_organization(org.name)
            self.link_item_organization(
                item_id=item_id,
                organization_id=o_id,
                role=org.role,
                source_text=org.source_text,
            )

        return item_id

    # -----------------------------------------------------------------------
    # Relational Query Interface (Required by Assignment 6)
    # -----------------------------------------------------------------------

    def get_events_by_person_name(self, normalized_or_display_name: str) -> List[Dict[str, Any]]:
        """Query: Which events in my local database mention this exact normalized person name?"""
        norm_key = normalize_person_name(normalized_or_display_name)
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT 
                i.id AS event_id,
                i.title AS event_title,
                i.item_url,
                p.display_name AS person_name,
                ip.role,
                ip.affiliation_raw,
                ip.source_text
            FROM item_people ip
            JOIN items i ON ip.item_id = i.id
            JOIN people p ON ip.person_id = p.id
            WHERE p.normalized_name = ?
            ORDER BY i.id
            """,
            (norm_key,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_organizer_organizations(self) -> List[Dict[str, Any]]:
        """Query: Which organizations have appeared as organizers in my collected sample?"""
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT
                o.id AS organization_id,
                o.display_name AS organization_name,
                o.normalized_name,
                io.role,
                COUNT(io.item_id) AS event_count
            FROM item_organizations io
            JOIN organizations o ON io.organization_id = o.id
            WHERE io.role IN ('organizer', 'co_organizer')
            GROUP BY o.id, io.role
            ORDER BY event_count DESC, o.display_name ASC
            """
        )
        return [dict(r) for r in cur.fetchall()]

    # Metric counts
    def count_items(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM items")
        return cur.fetchone()[0]

    def count_people(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM people")
        return cur.fetchone()[0]

    def count_organizations(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM organizations")
        return cur.fetchone()[0]

    def count_item_people(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM item_people")
        return cur.fetchone()[0]

    def count_item_organizations(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM item_organizations")
        return cur.fetchone()[0]
