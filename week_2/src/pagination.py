"""
Bounded listing traversal, shared by every source that paginates.

Stops when ANY of these is true (the reason is logged and returned):
  no_next        - the page has no "next" link
  max_pages      - page budget reached
  already_visited- next URL (canonicalised) was already crawled -> loop guard
  empty_page     - a page returned zero records
  off_site       - next link points to a different host
  fetch_error    - a page after the first failed; keep what we already have
"""

from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.errors import FetchError
from src.fetch import FetchResult, fetch
from src.logging_config import get_logger

HARD_PAGE_LIMIT = 20  # absolute safety cap, whatever a source config says


def canonical_url(url: str) -> str:
    """Normalise a URL so the same page is recognised under different spellings."""
    parts = urlsplit(url)
    query = sorted(parse_qsl(parts.query, keep_blank_values=True))
    # Drupal: ?page=0 is the same page as no page parameter at all
    query = [(k, v) for k, v in query if not (k == "page" and v == "0")]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def collect_listing(
    start_url: str,
    parse_listing: Callable[[str, str], list[dict[str, Any]]],
    get_next_page_url: Callable[[str, str], str | None] | None,
    max_pages: int = 1,
    source_name: str = "?",
    fetcher: Callable[[str], FetchResult] = fetch,
) -> dict[str, Any]:
    """
    Crawl listing pages starting at start_url.

    Returns {"items", "pages", "stop_reason", "duplicates", "first_status"}.
    Each item gets extra.discovered_on = the page it was found on.
    Duplicates across pages are dropped (first occurrence wins).
    """
    log = get_logger()
    max_pages = max(1, min(max_pages, HARD_PAGE_LIMIT))
    visited: set[str] = set()
    seen_items: set[str] = set()
    items: list[dict[str, Any]] = []
    duplicates = 0
    pages = 0
    first_status = None
    url: str | None = start_url
    stop_reason = "no_next"

    while url:
        visited.add(canonical_url(url))
        try:
            result = fetcher(url)
        except FetchError:
            if pages == 0:
                raise  # nothing collected: the whole run failed at fetch
            stop_reason = "fetch_error"
            log.warning(f"PAGINATION source={source_name} stage=fetch url={url} stop=fetch_error "
                        f"keeping={len(items)} records from {pages} page(s)")
            break
        pages += 1
        first_status = first_status or result.status

        page_items = parse_listing(result.text, url)
        log.info(f"PARSE source={source_name} page={pages} url={url} records={len(page_items)}")
        if not page_items:
            stop_reason = "empty_page"
            break

        for item in page_items:
            key = item.get("item_url")
            if key in seen_items:
                duplicates += 1
                log.info(f"DUPLICATE source={source_name} item_url={key} page={pages} (skipped)")
                continue
            seen_items.add(key)
            item.setdefault("extra", {})["discovered_on"] = url
            items.append(item)

        if pages >= max_pages:
            stop_reason = "max_pages"
            break
        next_url = get_next_page_url(result.text, url) if get_next_page_url else None
        if not next_url:
            stop_reason = "no_next"
            break
        if urlsplit(next_url).netloc != urlsplit(url).netloc:
            stop_reason = "off_site"
            break
        if canonical_url(next_url) in visited:
            stop_reason = "already_visited"
            break
        url = next_url

    log.info(f"PAGINATION source={source_name} pages={pages} records={len(items)} "
             f"duplicates={duplicates} stop={stop_reason}")
    return {"items": items, "pages": pages, "stop_reason": stop_reason,
            "duplicates": duplicates, "first_status": first_status}
