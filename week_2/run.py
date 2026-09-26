#!/usr/bin/env python3
"""
Command-line entry point.

  python run.py list                               # registered sources + capabilities
  python run.py run jnu_notices --max-pages 2      # one crawl through the common runner
  python run.py run jnu_events --detail-limit 5
  python run.py show jnu_events                    # what is stored
  python run.py export data/normalized_output.jsonl
  python run.py runs                               # run history (status / failed stage)
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from sources import SOURCES, get_source
from src import storage
from src.logging_config import setup_logging
from src.runner import run_source

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Academic web monitor")
    parser.add_argument("--db", default=storage.DEFAULT_DB_PATH)
    parser.add_argument("--log-file", default=str(ROOT / "logs" / "monitor.log"))
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")
    p_run = sub.add_parser("run")
    p_run.add_argument("source")
    p_run.add_argument("--max-pages", type=int)
    p_run.add_argument("--detail-limit", type=int)
    p_show = sub.add_parser("show")
    p_show.add_argument("source", nargs="?")
    p_export = sub.add_parser("export")
    p_export.add_argument("out")
    sub.add_parser("runs")

    args = parser.parse_args()
    setup_logging(args.log_level, args.log_file)

    if args.cmd == "list":
        for s in SOURCES.values():
            print(f"{s.name:24} {s.item_type:13} {','.join(s.capabilities):28} {s.listing_url}")
        return 0

    if args.cmd == "run":
        result = run_source(get_source(args.source), db_path=args.db,
                            max_pages=args.max_pages, detail_limit=args.detail_limit)
        return 0 if result["status"] == "success" else 1

    if args.cmd == "show":
        items = storage.get_items(args.db, args.source)
        for item in items:
            date = item.get("event_start") or item.get("published_at") or "-"
            print(f"{date:10}  {item['item_type']:12}  {item.get('title') or item.get('name')}")
        print(f"\n{len(items)} records")
        return 0

    if args.cmd == "export":
        items = storage.get_items(args.db)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"exported {len(items)} records to {args.out}")
        return 0

    if args.cmd == "runs":
        conn = sqlite3.connect(args.db)
        for row in conn.execute("SELECT started_at, source_name, status, failed_stage, pages, parsed, new,"
                                " changed, existing, error FROM runs ORDER BY id"):
            print(" | ".join("" if v is None else str(v) for v in row))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
