"""
JNU source adapter. The ONLY place that knows JNU's HTML.

Two public surfaces, both rendered by Drupal "views":

  jnu_notices  https://www.jnu.ac.in/notices   announcement listing, paginated
               (?page=N, rel="next"), items are mostly PDFs -> no detail pages.
  jnu_events   https://www.jnu.ac.in/jnuevents event listing -> /node/<id> detail
               pages; currently a single page (no pager rendered).

No HTTP, logging setup or database code lives here - the generic runner does that.
"""

import hashlib
import re
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from src.errors import ParseError
from src.schema import build_record, clean_text, parse_date
from src.source import SourceConfig

INSTITUTION = "Jawaharlal Nehru University"
BASE = "https://www.jnu.ac.in"
NOTICES_URL = f"{BASE}/notices"
EVENTS_URL = f"{BASE}/jnuevents"

NOTICES_VIEW = "div.view-id-notices"
EVENTS_VIEW = "div.view-id-jnu_events"


# ---------------------------------------------------------------- shared Drupal bits

def _view(html: str, selector: str) -> Tag:
    soup = BeautifulSoup(html, "html.parser")
    view = soup.select_one(selector)
    if view is None:
        raise ParseError(f"listing container {selector!r} not found - page structure changed "
                         f"or this is not the expected page")
    return view


def _listing_rows(html: str, view_selector: str) -> list[Tag]:
    """
    Distinguish the three situations a monitor must not confuse:
      - view container missing              -> ParseError (wrong page / redesign)
      - view present, no .view-content       -> [] (Drupal's real "no results" state)
      - .view-content present but no <td> rows -> ParseError (layout changed, e.g. cards)
    """
    view = _view(html, view_selector)
    content = view.select_one(".view-content")
    if content is None:
        return []
    rows = [tr for tr in content.select("table tr") if tr.find("td")]
    if not rows:
        raise ParseError(f"{view_selector} has .view-content but no table rows - "
                         f"listing layout changed (cards/divs instead of a table?)")
    return rows


def get_next_page_url(html: str, current_url: str) -> str | None:
    """Drupal pager: <li class="pager__item--next"><a rel="next" href="?page=N">."""
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one("nav.pager a[rel=next]") or soup.select_one("li.pager__item--next a[href]")
    if not link or not link.get("href"):
        return None
    return urljoin(current_url, link["href"])


def _cell_date(cell: Tag | None) -> str | None:
    if cell is None:
        return None
    t = cell.find("time")
    if t and t.get("datetime"):
        return t["datetime"]
    return clean_text(cell.get_text(" ")) or None


def _digest(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def _synthetic_url(page_url: str, *parts: str) -> str:
    """Stable identity for a row that has no link (must not collide with other rows)."""
    return f"{page_url.split('?')[0]}#item-{_digest(*parts)}"


def _canonical_host(url: str) -> str:
    """JNU links both jnu.ac.in and www.jnu.ac.in for the same page."""
    return re.sub(r"^(https?://)jnu\.ac\.in(?=/|$)", r"\1www.jnu.ac.in", url)


# ---------------------------------------------------------------- notices (announcements)

def parse_notices_listing(html: str, base_url: str) -> list[dict[str, Any]]:
    rows = _listing_rows(html, NOTICES_VIEW)
    items = []
    for row in rows:
        title_cell = row.select_one("td.views-field-title")
        if title_cell is None:
            continue
        title = clean_text(title_cell.get_text(" "))
        if not title:
            continue
        date_raw = clean_text((row.select_one("td.views-field-field-notice-date") or Tag(name="x")).get_text(" ")) or None
        link = title_cell.find("a", href=True) or row.select_one("td.views-field-field-upload-file a[href]")
        link_url = _canonical_host(urljoin(base_url, link["href"].strip())) if link else None
        document_type = _document_type(link_url or "", has_link=bool(link))
        if document_type in ("pdf", "image"):
            item_url = link_url            # the circular file itself is the notice's identity
        elif link_url:
            # HTML landing pages are shared: "7th Convocation", "9th Convocation" and
            # "Special Convocation" all link to /convocation. Make identity per notice.
            item_url = f"{link_url.split('#')[0]}#notice-{_digest(title, date_raw or '')}"
        else:
            item_url = _synthetic_url(base_url, title, date_raw or "")
        counter = row.select_one("td.views-field-counter")
        # raw_text deliberately excludes the Sl. No.: it shifts every time a new notice is
        # posted, which would make every old notice look "changed" on the next run.
        raw_text = " | ".join(td.get_text(" ", strip=True) for td in row.find_all("td")
                              if "views-field-counter" not in td.get("class", []) and td.get_text(strip=True))
        items.append({
            "source_url": base_url,
            "item_url": item_url,
            "title": title,
            "date_raw": date_raw,
            "sl_no": clean_text(counter.get_text()) if counter else None,
            "document_type": document_type,
            "link_url": link_url,
            "raw_text": raw_text,
        })
    if rows and not items:
        raise ParseError(f"{len(rows)} table rows found but none has a td.views-field-title cell "
                         f"- column layout changed")
    return items


def _document_type(url: str, has_link: bool) -> str:
    if not has_link:
        return "none"
    path = urlsplit(url).path.lower()
    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith((".jpg", ".jpeg", ".png")):
        return "image"
    if urlsplit(url).netloc and "jnu.ac.in" not in urlsplit(url).netloc:
        return "external"
    return "html"


def normalize_notice(raw: dict[str, Any]) -> dict[str, Any]:
    return build_record(
        "announcement",
        source_name=raw["source_name"],
        source_url=raw.get("source_url"),
        item_url=raw["item_url"],
        title=raw["title"],
        published_at=parse_date(raw.get("date_raw")),
        organizations=[INSTITUTION],
        raw_text=raw.get("raw_text"),
        extra={**raw.get("extra", {}), "date_raw": raw.get("date_raw"), "document_type": raw.get("document_type"),
               "link_url": raw.get("link_url")},
    )


# ---------------------------------------------------------------- events

def parse_events_listing(html: str, base_url: str) -> list[dict[str, Any]]:
    rows = _listing_rows(html, EVENTS_VIEW)
    items = []
    for row in rows:
        title_cell = row.select_one("td.views-field-title")
        if title_cell is None:
            continue
        title = clean_text(title_cell.get_text(" "))
        link = title_cell.find("a", href=True)
        if not title:
            continue
        start_raw = _cell_date(row.select_one("td.views-field-field-event-from-date"))
        # the archive display only has the "Event End Date" column; start comes from the detail page
        end_raw = _cell_date(row.select_one("td.views-field-field-event-date"))
        item_url = urljoin(base_url, link["href"]) if link else _synthetic_url(base_url, title, start_raw or "")
        items.append({
            "source_url": base_url,
            "item_url": item_url,
            "title": title,
            "start_raw": start_raw,
            "end_raw": end_raw,
            "raw_text": row.get_text(" | ", strip=True),
        })
    if rows and not items:
        raise ParseError(f"{len(rows)} table rows found but none has a td.views-field-title cell "
                         f"- column layout changed")
    return _fold_translations(items)


HINDI_PREFIX = re.compile(r"^(https?://[^/]+)/hi/")


def _fold_translations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    JNU's English events list also contains some Hindi copies of the same node
    (/hi/node/N next to /node/N). Same event -> one record: keep the English row
    and remember the Hindi title. A Hindi-only row is kept as is.
    """
    english = {i["item_url"]: i for i in items if not HINDI_PREFIX.match(i["item_url"])}
    result = []
    for item in items:
        m = HINDI_PREFIX.match(item["item_url"])
        if m:
            english_url = HINDI_PREFIX.sub(r"\1/", item["item_url"])
            if english_url in english:
                english[english_url].setdefault("extra", {})["title_hi"] = item["title"]
                continue
            item.setdefault("extra", {})["language"] = "hi"
        result.append(item)
    return result


def parse_event_detail(html: str, item_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("article.node")
    if node is None:
        raise ParseError(f"no <article class='node'> on detail page {item_url}")

    def field(name: str) -> Tag | None:
        return node.select_one(f".field--name-{name} .field__item")

    title_el = field("field-event-title")
    details_el = field("field-event-details")
    description = None
    image_urls: list[str] = []
    links: list[str] = []
    location = None
    registration_url = None
    if details_el is not None:
        for hidden in details_el.select(".visually-hidden, .field__label"):
            hidden.decompose()  # screen-reader labels such as "Image"
        text_lines = [clean_text(line) for line in details_el.get_text("\n").split("\n")]
        text_lines = [line for line in text_lines if line]
        description = " ".join(text_lines) or None
        image_urls = [urljoin(item_url, img["src"]) for img in details_el.find_all("img", src=True)]
        links = [_unwrap_redirect(urljoin(item_url, a["href"])) for a in details_el.find_all("a", href=True)]
        location = _find_venue(text_lines)
        registration_url = _find_registration(details_el, item_url, text_lines)

    return {
        "title": clean_text(title_el.get_text(" ")) if title_el else None,
        "start_raw": _cell_date(field("field-event-from-date")),
        "end_raw": _cell_date(field("field-event-date")),
        "description": description,
        "location": location,
        "registration_url": registration_url,
        "image_urls": image_urls,
        "links": links,
    }


def _find_venue(lines: list[str]) -> str | None:
    for i, line in enumerate(lines):
        m = re.match(r"^(?:conference\s+|event\s+)?venue\s*[:\-]?\s*(.*)$", line, re.IGNORECASE)
        if m:
            if m.group(1):
                return m.group(1)
            if i + 1 < len(lines):
                return ", ".join(lines[i + 1:i + 3])  # e.g. "School of X, Jawaharlal Nehru University"
    return None


def _unwrap_redirect(url: str) -> str:
    """Links pasted from govt webmail are wrapped: mail.mgovcloud.in/zm/reUrlCheck.do?url=<real url>."""
    parts = urlsplit(url)
    if "reurlcheck" in parts.path.lower():
        target = dict(parse_qsl(parts.query)).get("url")
        if target:
            return target
    return url


def _find_registration(details: Tag, item_url: str, lines: list[str]) -> str | None:
    for a in details.find_all("a", href=True):
        context = a.get_text() + a["href"] + (a.parent.get_text() if a.parent else "")
        if "regist" in context.lower():
            return _unwrap_redirect(urljoin(item_url, a["href"]))
    for i, line in enumerate(lines):  # "Registration Link" followed by a bare URL line
        if "registration link" in line.lower() and i + 1 < len(lines):
            candidate = lines[i + 1]
            if re.match(r"^(https?://|www\.)\S+$", candidate):
                return candidate if candidate.startswith("http") else f"https://{candidate}"
    return None


def merge_listing_and_detail(listing_item: dict[str, Any], detail_item: dict[str, Any] | None) -> dict[str, Any]:
    """Detail values win when present; listing values are kept when the detail is missing/empty."""
    merged = dict(listing_item)
    for key, value in (detail_item or {}).items():
        if value not in (None, "", []):
            merged[key] = value
    return merged


ORG_PATTERN = re.compile(r"^(.+?)\s+(?:organi[sz]es|is organi[sz]ing|is celebrating|celebrates|invites)\b", re.I)
SPEAKER_PATTERN = re.compile(r"\b(?:lecture|talk|seminar|address)\s+by\s+(.+)$", re.I)


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    item = merge_listing_and_detail(raw, raw.get("detail"))
    title = item["title"]

    orgs = []
    m = ORG_PATTERN.match(title)
    if m:
        orgs.append(clean_text(m.group(1)))  # e.g. "SCIS", "CIPOD, SIS"
    orgs.append(INSTITUTION)

    speakers = []
    m = SPEAKER_PATTERN.search(title)
    if m:
        speakers.append(clean_text(m.group(1)).rstrip("."))

    extra = dict(raw.get("extra", {}))
    for key in ("registration_url", "image_urls", "links"):
        if item.get(key):
            extra[key] = item[key]
    extra["start_raw"] = raw.get("start_raw")
    extra["end_raw"] = raw.get("end_raw")

    return build_record(
        "event",
        source_name=raw["source_name"],
        source_url=raw.get("source_url"),
        item_url=raw["item_url"],
        title=title,
        event_start=parse_date(item.get("start_raw")),
        event_end=parse_date(item.get("end_raw")),
        location=item.get("location"),
        speakers=speakers,
        organizations=orgs,
        description=item.get("description"),
        raw_text=raw.get("raw_text"),
        extra=extra,
    )


# ---------------------------------------------------------------- source configs

JNU_NOTICES = SourceConfig(
    name="jnu_notices",
    display_name="JNU Notices & Circulars",
    institution=INSTITUTION,
    listing_url=NOTICES_URL,
    item_type="announcement",
    parse_listing=parse_notices_listing,
    normalize_item=normalize_notice,
    get_next_page_url=get_next_page_url,
    max_pages=2,
    notes="50 rows/page, ~4 pages. Items link straight to PDFs, so no detail stage.",
)

JNU_EVENTS = SourceConfig(
    name="jnu_events",
    display_name="JNU Events",
    institution=INSTITUTION,
    listing_url=EVENTS_URL,
    item_type="event",
    parse_listing=parse_events_listing,
    normalize_item=normalize_event,
    get_next_page_url=get_next_page_url,
    parse_detail=parse_event_detail,
    max_pages=1,
    detail_limit=5,
    notes="~15 upcoming events, single page. Detail pages are /node/<id>.",
)

JNU_EVENTS_ARCHIVE = SourceConfig(
    name="jnu_events_archive",
    display_name="JNU Events Archive",
    institution=INSTITUTION,
    listing_url=f"{BASE}/events-archive",
    item_type="event",
    parse_listing=parse_events_listing,     # same Drupal view as jnu_events -> same parser
    normalize_item=normalize_event,
    get_next_page_url=get_next_page_url,
    parse_detail=parse_event_detail,
    max_pages=2,                            # ~41 pages exist; never crawl the whole history
    detail_limit=3,
    notes="30 rows/page, newest first. Listing only shows end date; start date comes from detail.",
)
