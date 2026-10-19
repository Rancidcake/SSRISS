#!/usr/bin/env python3
"""central_aggregator_adapter.py - Central Aggregator Implementation (Assignment 10)

Synthesizes Week 3 capabilities into an end-to-end monitored aggregator pipeline:
1. Central Discovery Surface (HTML, RSS, Sitemap)
2. URL Scope Bounding & Deduplication
3. Content Routing (Event vs Announcement vs PDF vs External)
4. Detail Parsing & Canonical Shape Normalization
5. Explicit Entity Extraction (People & Organizations with Provenance)
6. Incremental Change Detection & Relational Storage (SQLite)
7. Source Health Metrics & Standardized Run Summary

Ceiling Control:
- Configured with max_items (20–40) and max_pages (2–5) to prove architecture
  without unbounded scraping.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

# Setup import paths across Week 3 modules
_HERE = os.path.dirname(os.path.abspath(__file__))
_ASSIGNMENTS_DIR = os.path.abspath(os.path.join(_HERE, ".."))

for sub in [
    "02_scope",
    "03_interface",
    "04_incremental",
    "05_extraction",
    "06_entities",
    "08_routing",
    "09_metrics",
]:
    path = os.path.join(_ASSIGNMENTS_DIR, sub)
    if path not in sys.path:
        sys.path.insert(0, path)

from scope_filter import UrlScopeFilter, canonicalize_url, is_allowed_item_url
from aggregator_discovery import discover_from_html, DISCOVERY_SCHEMA_KEYS
from incremental_store import compute_content_hash, ItemStatus
from entity_extractor import extract_entities, EventEntities
from entity_relational_store import EntityRelationalStore
from content_router import classify_discovered_item, ItemType
from run_summary import RunMetrics, persist_metrics_to_db


# ---------------------------------------------------------------------------
# Default Config for Central JNU Aggregator
# ---------------------------------------------------------------------------

DEFAULT_JNU_CONFIG = {
    "source_name": "jnu_events",
    "base_url": "https://www.jnu.ac.in",
    "allowed_hostname": "www.jnu.ac.in",
    "allowed_path_prefixes": ["/node", "/jnuevents", "/events-archive"],
    "excluded_path_prefixes": [
        "/login", "/user", "/admin", "/search", "/calendar", "/filter", "/sites/default/files",
    ],
    "allow_external": False,
    "max_items": 30,      # Ceiling: 20-40 records
    "max_pages": 3,       # Ceiling: 2-5 pages
    "ignored_query_params": ["utm_source", "utm_medium", "utm_campaign", "fbclid", "gclid"],
}


class CentralAggregatorAdapter:
    """End-to-end monitored aggregator coordinating discovery, scope,
    extraction, incremental storage, and run summary metrics.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        db_path: str = ":memory:",
        log_path: Optional[str] = None,
    ) -> None:
        self.config = config or DEFAULT_JNU_CONFIG.copy()
        self.db_path = db_path
        self.log_path = log_path
        self.scope_filter = UrlScopeFilter(self.config)
        self.store = EntityRelationalStore(self.db_path)
        self._setup_logger()
        self._init_incremental_table()

    def _setup_logger(self) -> None:
        self.logger = logging.getLogger(f"Aggregator.{self.config.get('source_name', 'jnu')}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        self.logger.addHandler(sh)

        if self.log_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            fh = logging.FileHandler(self.log_path, mode="a", encoding="utf-8")
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def _init_incremental_table(self) -> None:
        """Ensure incremental content hash table exists in the relational store."""
        with self.store._conn:
            self.store._conn.execute("""
                CREATE TABLE IF NOT EXISTS item_hashes (
                    item_url      TEXT PRIMARY KEY,
                    content_hash  TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at  TEXT NOT NULL,
                    fetched_at    TEXT NOT NULL
                );
            """)

    def close(self) -> None:
        self.store.close()

    # -----------------------------------------------------------------------
    # Main Execution Pipeline
    # -----------------------------------------------------------------------

    def run(
        self,
        html_content: Optional[str] = None,
        html_fixture_path: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> RunMetrics:
        """Execute complete monitored collection cycle."""
        started_at = datetime.now(timezone.utc).isoformat()
        source_name = self.config.get("source_name", "jnu_events")
        limit = max_items or self.config.get("max_items", 30)

        self.logger.info(f"=== Starting Ingestion Run: {source_name} ===")

        # Load content
        if html_fixture_path and not html_content:
            with open(html_fixture_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        elif not html_content:
            html_content = ""

        # 1. Discovery
        discovered_records = discover_from_html(
            html_content,
            self.config,
            base_url=self.config.get("base_url", "https://www.jnu.ac.in"),
            discovered_at=started_at,
        )
        self.logger.info(f"Discovery complete: found {len(discovered_records)} candidate items.")

        # 2. Scope & Ceiling Filtering
        admissible_records = []
        for rec in discovered_records:
            url = rec["discovered_url"]
            if self.scope_filter.is_allowed(url):
                admissible_records.append(rec)
            else:
                self.logger.debug(f"Scope boundary denied: {url}")

            if len(admissible_records) >= limit:
                self.logger.info(f"Reached discovery ceiling limit of {limit} items.")
                break

        # Metrics accumulators
        items_discovered = len(discovered_records)
        items_parsed = 0
        new_count = 0
        changed_count = 0
        unchanged_count = 0
        failed_count = 0
        people_extracted = 0
        orgs_extracted = 0
        items_with_date = 0
        items_with_speaker = 0
        items_with_org = 0

        current_run_urls: Set[str] = set()

        # 3. Process Each Admissible Item
        for rec in admissible_records:
            item_url = rec["discovered_url"]
            current_run_urls.add(item_url)

            # Route content
            item_type = classify_discovered_item(rec)
            if item_type not in (ItemType.EVENT, ItemType.ANNOUNCEMENT):
                self.logger.info(f"Skipping non-event/non-announcement item type '{item_type.value}': {item_url}")
                continue

            try:
                # Entity extraction from title and discovery metadata
                entities = extract_entities({
                    "title": rec["discovered_title"],
                    "raw_text": f"Title: {rec['discovered_title']}\nDate: {rec.get('source_timestamp') or ''}",
                })

                # Compute content hash
                payload = {
                    "title": rec["discovered_title"],
                    "timestamp": rec.get("source_timestamp"),
                    "item_type": item_type.value,
                    "speakers": [p.name for p in entities.people],
                    "orgs": [o.name for o in entities.organizations],
                }
                c_hash = compute_content_hash(payload)

                # Check incremental status
                cur = self.store._conn.cursor()
                cur.execute("SELECT content_hash, first_seen_at FROM item_hashes WHERE item_url = ?", (item_url,))
                hash_row = cur.fetchone()

                now_iso = datetime.now(timezone.utc).isoformat()
                if hash_row is None:
                    status = ItemStatus.NEW
                    new_count += 1
                    with self.store._conn:
                        self.store._conn.execute(
                            "INSERT INTO item_hashes VALUES (?, ?, ?, ?, ?)",
                            (item_url, c_hash, now_iso, now_iso, now_iso),
                        )
                elif hash_row["content_hash"] != c_hash:
                    status = ItemStatus.CHANGED
                    changed_count += 1
                    with self.store._conn:
                        self.store._conn.execute(
                            "UPDATE item_hashes SET content_hash=?, last_seen_at=?, fetched_at=? WHERE item_url=?",
                            (c_hash, now_iso, now_iso, item_url),
                        )
                else:
                    status = ItemStatus.UNCHANGED
                    unchanged_count += 1
                    with self.store._conn:
                        self.store._conn.execute(
                            "UPDATE item_hashes SET last_seen_at=?, fetched_at=? WHERE item_url=?",
                            (now_iso, now_iso, item_url),
                        )

                # Store item and entities relationally
                self.store.store_event_with_entities(
                    {
                        "item_url": item_url,
                        "title": rec["discovered_title"],
                        "source_name": source_name,
                        "item_type": item_type.value,
                        "raw_text": rec.get("discovered_title"),
                    },
                    entities,
                )

                items_parsed += 1
                people_extracted += len(entities.people)
                orgs_extracted += len(entities.organizations)

                if rec.get("source_timestamp"):
                    items_with_date += 1
                if entities.people:
                    items_with_speaker += 1
                if entities.organizations:
                    items_with_org += 1

                self.logger.info(f"[{status.value.upper()}] {item_url} -> {len(entities.people)} people, {len(entities.organizations)} orgs")

            except Exception as exc:
                failed_count += 1
                self.logger.error(f"Failed processing item {item_url}: {exc}")

        finished_at = datetime.now(timezone.utc).isoformat()

        metrics = RunMetrics(
            source=source_name,
            started_at=started_at,
            finished_at=finished_at,
            http_status=200 if html_content else 500,
            pages_fetched=1 if html_content else 0,
            items_discovered=items_discovered,
            items_parsed=items_parsed,
            new=new_count,
            changed=changed_count,
            unchanged=unchanged_count,
            failed=failed_count,
            people_extracted=people_extracted,
            organizations_extracted=orgs_extracted,
            items_with_date=items_with_date,
            items_with_speaker=items_with_speaker,
            items_with_organization=items_with_org,
        )

        persist_metrics_to_db(metrics, self.store._conn)
        self.logger.info("\n" + metrics.to_summary_text())
        return metrics
