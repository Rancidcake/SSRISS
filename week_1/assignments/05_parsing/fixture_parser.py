#!/usr/bin/env python3
"""
Assignment 05A - Local Fixture Parser
Parses fictional HTML notice cards safely without crashing on missing fields.
"""

import os
import json
from typing import List, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def parse_events(html: str, base_url: str = "https://example.university.edu") -> List[Dict[str, Any]]:
    """
    Parses HTML notice cards from string content, returning a list of extracted dictionaries.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.notice-card")
    items: List[Dict[str, Any]] = []

    for card in cards:
        # Title & URL
        title_elem = card.select_one("h2.notice-title a")
        title = title_elem.get_text(strip=True) if title_elem else None
        
        raw_href = title_elem.get("href", "") if title_elem else ""
        item_url = urljoin(base_url, raw_href) if raw_href else None

        # Determine item_type: pdf_notice vs html_notice
        item_type = "pdf_notice" if item_url and (item_url.lower().endswith(".pdf") or ".pdf" in item_url.lower()) else "html_notice"

        # Date
        date_elem = card.select_one("time.notice-date")
        date_raw = date_elem.get_text(strip=True) if date_elem else None

        # Speaker
        speaker_elem = card.select_one("span.speaker-name")
        speaker_raw = speaker_elem.get_text(strip=True) if speaker_elem else None

        # Location
        location_elem = card.select_one("span.location-name")
        location_raw = location_elem.get_text(strip=True) if location_elem else None

        # Raw Text / Summary
        summary_elem = card.select_one("p.notice-summary")
        raw_text = summary_elem.get_text(strip=True) if summary_elem else card.get_text(strip=True)

        item = {
            "title": title,
            "item_url": item_url,
            "item_type": item_type,
            "date_raw": date_raw,
            "speaker_raw": speaker_raw,
            "location_raw": location_raw,
            "raw_text": raw_text
        }
        items.append(item)

    return items


def main():
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "03_dom", "fixture.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    extracted = parse_events(html_content, base_url="https://example.university.edu")
    
    output_path = os.path.join(os.path.dirname(__file__), "fixture_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2)

    print(f"[*] Parsed {len(extracted)} items from fixture. Output saved to {output_path}")


if __name__ == "__main__":
    main()
