#!/usr/bin/env python3
"""
JNU Web Notice Scraper - Assignment 05B
Fetches live notices from Jawaharlal Nehru University (https://www.jnu.ac.in/notices)
and extracts structured notice items distinguishing PDF documents from HTML pages.
"""

import os
import json
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

JNU_NOTICES_URL = "https://www.jnu.ac.in/notices"
DEFAULT_USER_AGENT = "WebMonitor/1.0 (JNU Academic Monitoring)"
DEFAULT_TIMEOUT = 10


def fetch(url: str = JNU_NOTICES_URL, user_agent: str = DEFAULT_USER_AGENT, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Fetches raw HTML content from the specified URL using requests.
    Enforces timeout=10 and a custom User-Agent header.
    """
    headers = {"User-Agent": user_agent}
    logging.info(f"Fetching network surface: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.Timeout:
        logging.error(f"Network request timed out after {timeout}s for {url}")
        raise
    except requests.RequestException as e:
        logging.error(f"HTTP request failed for {url}: {e}")
        raise


def parse_items(html: str, base_url: str = JNU_NOTICES_URL) -> List[Dict[str, Any]]:
    """
    Parses raw HTML from JNU notices listing table, extracting raw notice items.
    Categorizes notice URLs into 'pdf_notice' or 'html_notice'.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []

    # JNU renders notices in standard table rows (<tr>)
    rows = soup.select("table tr")
    if not rows:
        logging.warning("No table rows found in HTML content.")
        return items

    for idx, row in enumerate(rows):
        cells = row.find_all(["td", "th"])
        if not cells or len(cells) < 3:
            continue  # Skip header or malformed rows

        # Extract cell texts safely
        sl_no = cells[0].get_text(strip=True)
        # Skip header row if first cell is non-digit
        if not sl_no.isdigit():
            continue

        title_cell = cells[1]
        title = title_cell.get_text(strip=True)

        date_cell = cells[2]
        date_raw = date_cell.get_text(strip=True)

        # Extract notice document URL (check 4th column download link or link inside title)
        notice_link = None
        if len(cells) >= 4 and cells[3].find("a", href=True):
            notice_link = cells[3].find("a", href=True)["href"]
        elif title_cell.find("a", href=True):
            notice_link = title_cell.find("a", href=True)["href"]

        if notice_link:
            item_url = urljoin(base_url, notice_link)
        else:
            # Fallback URL if link is missing
            item_url = base_url

        # Classify item_type: pdf_notice vs html_notice
        url_lower = item_url.lower()
        if url_lower.endswith(".pdf") or ".pdf" in url_lower:
            item_type = "pdf_notice"
        else:
            item_type = "html_notice"

        # Raw text retention for provenance
        raw_text = f"Sl: {sl_no} | Title: {title} | Date: {date_raw}"

        item = {
            "source_name": "jnu_official_notices",
            "source_url": base_url,
            "sl_no": sl_no,
            "title": title,
            "item_url": item_url,
            "item_type": item_type,
            "date_raw": date_raw,
            "speaker_raw": None,  # Not available on listing surface
            "location_raw": None, # Not available on listing surface
            "raw_text": raw_text
        }
        items.append(item)

    logging.info(f"Extracted {len(items)} raw notice items.")
    return items


def run_scraper(use_live: bool = True) -> List[Dict[str, Any]]:
    """
    Main driver executing fetch and parse phases, persisting sample_response.html and output.json.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_html_path = os.path.join(script_dir, "sample_response.html")
    output_json_path = os.path.join(script_dir, "output.json")

    html_content = ""
    if use_live:
        try:
            html_content = fetch(JNU_NOTICES_URL)
            # Cache sample html fixture
            with open(sample_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logging.info(f"Saved live HTML snapshot to {sample_html_path}")
        except Exception as e:
            logging.warning(f"Live fetch failed ({e}). Falling back to local sample_response.html if available.")
            if os.path.exists(sample_html_path):
                with open(sample_html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
            else:
                raise RuntimeError("No live response or cached snapshot available.")
    else:
        if os.path.exists(sample_html_path):
            with open(sample_html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        else:
            raise FileNotFoundError(f"Snapshot file not found: {sample_html_path}")

    items = parse_items(html_content, base_url=JNU_NOTICES_URL)

    # Save output JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logging.info(f"Saved extracted items to {output_json_path}")

    return items


if __name__ == "__main__":
    run_scraper(use_live=True)
