#!/usr/bin/env python3
"""run_summary.py - Source Health & Coverage Metrics (Assignment 9)

Collects and persists per-run operational and qualitative health metrics:
- Pages fetched & HTTP status
- Items discovered, parsed, failed
- Incremental breakdown: new, changed, unchanged
- Entities extracted: people, organizations
- Quality coverage: % with date, % with speaker, % with organization
- Health diagnosis: distinguishing 'healthy steady state' from 'broken parser'
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
import sqlite3
from typing import Any, Dict, Optional


@dataclass
class RunMetrics:
    source: str
    started_at: str
    finished_at: str
    http_status: int = 200
    pages_fetched: int = 0
    items_discovered: int = 0
    items_parsed: int = 0
    new: int = 0
    changed: int = 0
    unchanged: int = 0
    failed: int = 0
    people_extracted: int = 0
    organizations_extracted: int = 0
    items_with_date: int = 0
    items_with_speaker: int = 0
    items_with_organization: int = 0

    @property
    def pct_with_date(self) -> float:
        return (self.items_with_date / self.items_parsed * 100.0) if self.items_parsed > 0 else 0.0

    @property
    def pct_with_speaker(self) -> float:
        return (self.items_with_speaker / self.items_parsed * 100.0) if self.items_parsed > 0 else 0.0

    @property
    def pct_with_organization(self) -> float:
        return (self.items_with_organization / self.items_parsed * 100.0) if self.items_parsed > 0 else 0.0

    def diagnose_health(self) -> str:
        """Distinguish healthy steady state from broken parser."""
        if self.pages_fetched > 0 and self.items_parsed == 0 and self.items_discovered == 0:
            return "CRITICAL: Broken parser suspected (zero items discovered or parsed from fetched pages)"
        if self.failed > 0 and self.failed >= self.items_parsed:
            return "CRITICAL: High failure rate (failed >= parsed)"
        if self.items_parsed > 0 and self.new == 0 and self.changed == 0:
            return "HEALTHY: Source active (steady state, all unchanged)"
        if self.new > 0 or self.changed > 0:
            return "HEALTHY: Active updates ingested"
        return "NOTICE: Run complete with zero new records"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pct_with_date"] = round(self.pct_with_date, 1)
        d["pct_with_speaker"] = round(self.pct_with_speaker, 1)
        d["pct_with_organization"] = round(self.pct_with_organization, 1)
        d["diagnosis"] = self.diagnose_health()
        return d

    def to_summary_text(self) -> str:
        """Format metrics matching assignment standard block."""
        return (
            f"SOURCE: {self.source}\n"
            f"PAGES_FETCHED: {self.pages_fetched}\n"
            f"ITEMS_DISCOVERED: {self.items_discovered}\n"
            f"ITEMS_PARSED: {self.items_parsed}\n"
            f"NEW: {self.new}\n"
            f"CHANGED: {self.changed}\n"
            f"UNCHANGED: {self.unchanged}\n"
            f"FAILED: {self.failed}\n"
            f"PEOPLE_EXTRACTED: {self.people_extracted}\n"
            f"ORGANIZATIONS_EXTRACTED: {self.organizations_extracted}\n"
            f"COVERAGE_DATE: {self.pct_with_date:.1f}%\n"
            f"COVERAGE_SPEAKER: {self.pct_with_speaker:.1f}%\n"
            f"COVERAGE_ORGANIZATION: {self.pct_with_organization:.1f}%\n"
            f"STATUS: {self.diagnose_health()}"
        )


def persist_metrics_to_db(metrics: RunMetrics, conn: sqlite3.Connection) -> None:
    """Persist run metrics into SQLite run_metrics table."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                http_status INTEGER,
                pages_fetched INTEGER,
                items_discovered INTEGER,
                items_parsed INTEGER,
                new_items INTEGER,
                changed_items INTEGER,
                unchanged_items INTEGER,
                failed_items INTEGER,
                people_extracted INTEGER,
                organizations_extracted INTEGER,
                coverage_date REAL,
                coverage_speaker REAL,
                coverage_organization REAL,
                diagnosis TEXT
            );
        """)
        conn.execute("""
            INSERT INTO run_metrics (
                source, started_at, finished_at, http_status, pages_fetched,
                items_discovered, items_parsed, new_items, changed_items,
                unchanged_items, failed_items, people_extracted, organizations_extracted,
                coverage_date, coverage_speaker, coverage_organization, diagnosis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.source, metrics.started_at, metrics.finished_at, metrics.http_status,
            metrics.pages_fetched, metrics.items_discovered, metrics.items_parsed,
            metrics.new, metrics.changed, metrics.unchanged, metrics.failed,
            metrics.people_extracted, metrics.organizations_extracted,
            metrics.pct_with_date, metrics.pct_with_speaker, metrics.pct_with_organization,
            metrics.diagnose_health()
        ))
