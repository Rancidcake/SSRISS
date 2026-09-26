# Adding a new source (guide for Soumyadipta / any teammate)

You should only need to **create one file and add one line**. Do not edit `src/`.
If you feel you must, write down why in `assignments/09_template_swap/review.md`.

## 1. Save a fixture first

```bash
curl -s -A "WebMonitor/2.0" "https://example.edu/events" -o fixtures/<site>/listing.html
```

## 2. Write `sources/<site>.py`

```python
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from src.errors import ParseError
from src.schema import build_record, clean_text, parse_date
from src.source import SourceConfig

LISTING_URL = "https://example.edu/events"


def parse_listing(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.events-list")          # <- your selector
    if container is None:
        raise ParseError("div.events-list not found - layout changed?")
    items = []
    for card in container.select("article"):                  # <- your selector
        link = card.select_one("a[href]")
        if not link:
            continue
        items.append({
            "source_url": base_url,
            "item_url": urljoin(base_url, link["href"]),
            "title": clean_text(link.get_text()),
            "date_raw": clean_text(card.select_one(".date").get_text()) if card.select_one(".date") else None,
            "raw_text": card.get_text(" | ", strip=True),
        })
    return items


def get_next_page_url(html: str, current_url: str) -> str | None:   # optional
    a = BeautifulSoup(html, "html.parser").select_one("a.next, a[rel=next]")
    return urljoin(current_url, a["href"]) if a else None


def normalize_item(raw: dict) -> dict:
    return build_record(
        "event",                                   # or "announcement" / "faculty"
        source_name=raw["source_name"],            # injected by the runner
        source_url=raw["source_url"],
        item_url=raw["item_url"],
        title=raw["title"],
        event_start=parse_date(raw.get("date_raw")),
        organizations=["Example University"],
        raw_text=raw.get("raw_text"),
        extra={**raw.get("extra", {}), "date_raw": raw.get("date_raw")},
    )


SOURCE = SourceConfig(
    name="example_events",
    display_name="Example University Events",
    institution="Example University",
    listing_url=LISTING_URL,
    item_type="event",
    parse_listing=parse_listing,
    normalize_item=normalize_item,
    get_next_page_url=get_next_page_url,   # or None
    parse_detail=None,                     # optional: (html, item_url) -> dict of fields
    max_pages=2,
    detail_limit=0,
)
```

## 3. Register it — `sources/__init__.py`

```python
from sources.example import SOURCE as EXAMPLE_EVENTS
SOURCES = {s.name: s for s in [JNU_NOTICES, JNU_EVENTS, JNU_EVENTS_ARCHIVE, JNU_NOTICES_FIXTURE, EXAMPLE_EVENTS]}
```

## 4. Test offline, then run live (small)

```bash
python3 -c "from sources.example import *; print(parse_listing(open('fixtures/<site>/listing.html').read(), LISTING_URL)[:2])"
python3 run.py run example_events --max-pages 1
python3 run.py show example_events
```

Optional: add it to `schedules.json` to schedule it.

## What you get for free

Timeout/User-Agent/politeness, pagination limits + loop detection, duplicate handling,
detail-page failure isolation, schema validation, SQLite upsert + change detection,
run history, stage-tagged logs, and scheduling.
