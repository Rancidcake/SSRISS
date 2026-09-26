#!/usr/bin/env python3
"""
Assignment 1 - deliberately trigger each failure type through the normal runner
and capture the log output. Uses a throw-away database so real data is untouched.

Run from week_2/:  python3 scripts/failure_demo.py
Output: logs/failure_examples.log
"""

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sources.jnu import JNU_EVENTS, JNU_NOTICES  # noqa: E402
from src.fetch import fetch  # noqa: E402
from src.logging_config import get_logger, setup_logging  # noqa: E402
from src.runner import run_source  # noqa: E402

FIXTURES = ROOT / "fixtures"


def main() -> None:
    log_path = ROOT / "logs" / "failure_examples.log"
    log_path.unlink(missing_ok=True)
    setup_logging("INFO", str(log_path))
    log = get_logger()
    db = str(Path(tempfile.mkdtemp()) / "failure_demo.db")
    notices = replace(JNU_NOTICES, max_pages=1)

    scenarios = [
        ("1. invalid URL", lambda: run_source(replace(notices, listing_url="htp://www.jnu.ac.in/notices"), db)),
        ("2. connection failure (DNS)", lambda: run_source(
            replace(notices, listing_url="https://www.jnu-does-not-exist.invalid/notices"), db)),
        ("3. HTTP 404 on the listing", lambda: run_source(
            replace(notices, listing_url="https://www.jnu.ac.in/events"), db)),
        ("4a. parser receives unexpected HTML (wrong page)", lambda: run_source(
            replace(notices, listing_url="https://www.jnu.ac.in/about-us"), db)),
        ("4b. parser receives changed layout (cards instead of table)", lambda: run_source(
            replace(notices, listing_url=(FIXTURES / "jnu/notices/changed_card_structure.html").as_uri()), db)),
        ("5. empty listing (real JNU empty page)", lambda: run_source(
            replace(JNU_EVENTS, listing_url="https://www.jnu.ac.in/jnuevents?page=1", detail_limit=0), db)),
        ("6. database write problem (db path is a directory)", lambda: run_source(
            replace(notices, listing_url=(FIXTURES / "pagination/page_1.html").as_uri()), str(ROOT / "data"))),
        ("7. one detail page 404s (URL rewritten to a node that does not exist)", lambda: run_source(
            replace(JNU_EVENTS, detail_limit=3), db,
            fetcher=lambda url: fetch(url.replace("159898442", "999999999")))),
    ]
    for title, scenario in scenarios:
        log.info(f"========== SCENARIO {title} ==========")
        scenario()


if __name__ == "__main__":
    main()
