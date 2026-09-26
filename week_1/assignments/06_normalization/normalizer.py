#!/usr/bin/env python3
"""
Assignment 06 - Normalization Layer
Refactors raw scraped JNU notice items into the shared standard schema with
ISO 8601 timestamps, clean titles, and preserved provenance.
"""

import os
import re
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Indian Standard Time (IST) timezone (+05:30)
IST = timezone(timedelta(hours=5, minutes=30))


def clean_text(text: Optional[str]) -> str:
    """
    Cleans surrounding and internal whitespace using regex.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    """
    Normalizes diverse date string formats to ISO 8601 (YYYY-MM-DD).
    Handles formats like:
      - 'Mon, 07-09-2026' -> '2026-09-07'
      - '07-09-2026'      -> '2026-09-07'
      - '15 September 2026' -> '2026-09-15'
      - '2026-09-15'      -> '2026-09-15'
    """
    if not date_str:
        return None

    cleaned = clean_text(date_str)

    # 1. Mon, 07-09-2026 or 07-09-2026 (DD-MM-YYYY)
    m1 = re.search(r"(\d{2})[-/](\d{2})[-/](\d{4})", cleaned)
    if m1:
        day, month, year = m1.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 2. 15 September 2026 or 15 Sept 2026
    m2 = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", cleaned)
    if m2:
        day, month_str, year = m2.groups()
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                dt = datetime.strptime(f"{day} {month_str} {year}", fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    # 3. YYYY-MM-DD
    m3 = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", cleaned)
    if m3:
        year, month, day = m3.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def normalize_item(raw_item: Dict[str, Any], fetched_at: Optional[str] = None) -> Dict[str, Any]:
    """
    Maps a raw scraped item dictionary to the standard output schema.
    """
    title = clean_text(raw_item.get("title"))
    date_raw = raw_item.get("date_raw")
    event_start = parse_date_to_iso(date_raw)

    item_url = raw_item.get("item_url", "")
    item_type = raw_item.get("item_type")
    if not item_type:
        item_type = "pdf_notice" if item_url.lower().endswith(".pdf") or ".pdf" in item_url.lower() else "html_notice"

    speaker_raw = raw_item.get("speaker_raw")
    speakers = [clean_text(speaker_raw)] if speaker_raw and clean_text(speaker_raw) else []

    location_raw = raw_item.get("location_raw")
    location = clean_text(location_raw) if location_raw else None

    timestamp = fetched_at if fetched_at else datetime.now(IST).isoformat()

    normalized = {
        "source_name": raw_item.get("source_name", "jnu_official_notices"),
        "source_url": raw_item.get("source_url", "https://www.jnu.ac.in/notices"),
        "item_url": item_url,
        "item_type": item_type,
        "title": title,
        "event_start": event_start,
        "event_end": None,
        "location": location,
        "speakers": speakers,
        "organizations": ["Jawaharlal Nehru University"],
        "raw_text": raw_item.get("raw_text", title),
        "date_raw": date_raw,
        "fetched_at": timestamp,
        "http_status": 200
    }
    return normalized


def process_normalization():
    """
    Reads raw output.json from 05_parsing/jnu/, normalizes each item, and writes jnu_normalized.jsonl.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_json_path = os.path.join(script_dir, "..", "05_parsing", "jnu", "output.json")
    output_jsonl_path = os.path.join(script_dir, "jnu_normalized.jsonl")

    if not os.path.exists(input_json_path):
        raise FileNotFoundError(f"Input file not found: {input_json_path}")

    with open(input_json_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    normalized_count = 0
    with open(output_jsonl_path, "w", encoding="utf-8") as out_f:
        for item in raw_items:
            norm_item = normalize_item(item)
            out_f.write(json.dumps(norm_item, ensure_ascii=False) + "\n")
            normalized_count += 1

    print(f"[*] Successfully normalized {normalized_count} items into {output_jsonl_path}")


if __name__ == "__main__":
    process_normalization()
