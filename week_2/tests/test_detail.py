"""Assignment 5 - listing -> detail enrichment, including a 404 detail page."""

from dataclasses import replace

import pytest

from sources.jnu import (EVENTS_URL, JNU_EVENTS, merge_listing_and_detail, parse_event_detail,
                         parse_events_listing)
from src import storage
from src.errors import ParseError
from src.runner import run_source

N390 = "https://www.jnu.ac.in/node/159898390"
N442 = "https://www.jnu.ac.in/node/159898442"
N904 = "https://www.jnu.ac.in/node/159897904"


def test_parse_listing_discovers_detail_urls(read_fixture):
    items = parse_events_listing(read_fixture("jnu/events/listing.html"), EVENTS_URL)
    assert len(items) == 5
    assert items[0]["item_url"] == N390
    assert items[-1]["item_url"] == "https://www.jnu.ac.in/node/999999999"


def test_parse_detail_rich_page(read_fixture):
    d = parse_event_detail(read_fixture("jnu/events/detail_159897904.html"), N904)
    assert d["title"] == "SCSS organises 4th International Conference on Networks and Cryptology"
    assert d["start_raw"].startswith("2026-10-08") and d["end_raw"].startswith("2026-10-10")
    assert d["location"] == "School of Computer & Systems Sciences, Jawaharlal Nehru University"
    assert d["registration_url"] == "https://www.netcrypt.org.in"
    assert "Call for papers".lower() in d["description"].lower()
    assert not d["description"].startswith("Image")


def test_parse_detail_image_only_page(read_fixture):
    d = parse_event_detail(read_fixture("jnu/events/detail_159898390.html"), N390)
    assert d["description"] is None           # the poster is an image; no text to extract
    assert d["image_urls"] == ["https://www.jnu.ac.in/sites/default/files/2026-09/scis_29Sep26.jpg"]


def test_parse_detail_unexpected_html(read_fixture):
    with pytest.raises(ParseError):
        parse_event_detail(read_fixture("jnu/events/detail_broken.html"), N390)


def test_merge_prefers_detail_but_keeps_listing_values():
    listing = {"title": "Listing title", "start_raw": "2026-09-29", "end_raw": "2026-09-29"}
    detail = {"title": "Detail title", "start_raw": None, "description": "Long text", "image_urls": []}
    merged = merge_listing_and_detail(listing, detail)
    assert merged["title"] == "Detail title"
    assert merged["start_raw"] == "2026-09-29"   # detail was empty -> listing value kept
    assert merged["description"] == "Long text"
    assert merge_listing_and_detail(listing, None) == listing


def test_detail_404_does_not_break_the_crawl(fake_fetcher, db_path, logs):
    """Checkpoint 5: one 404 detail page -> other records still processed and stored."""
    fetcher = fake_fetcher({
        EVENTS_URL: "jnu/events/listing.html",
        N390: "jnu/events/detail_159898390.html",
        N442: "jnu/events/detail_broken.html",      # unexpected HTML
        N904: "jnu/events/detail_159897904.html",   # not in the listing fixture -> never requested
        # node/159898416, node/159898439? not routed -> 404; node/999999999 -> 404
    })
    result = run_source(JNU_EVENTS, db_path=db_path, detail_limit=5, fetcher=fetcher)

    assert result["status"] == "success"
    assert storage.count_items(db_path) == 5                       # all listing records stored
    stored = {i["item_url"]: i for i in storage.get_items(db_path)}
    assert stored[N390]["extra"]["detail_status"] == "ok"
    assert stored[N442]["extra"]["detail_status"].startswith("failed")
    assert stored["https://www.jnu.ac.in/node/999999999"]["extra"]["detail_status"].startswith("failed")
    assert stored["https://www.jnu.ac.in/node/999999999"]["title"]  # listing data survived

    failures = [r.message for r in logs.records if "DETAIL_FAILED" in r.message]
    assert any("999999999" in m and "status=404" in m for m in failures)
    assert any("ParseError" in m for m in failures)


def test_detail_limit_controls_requests(fake_fetcher, db_path):
    fetcher = fake_fetcher({EVENTS_URL: "jnu/events/listing.html", N390: "jnu/events/detail_159898390.html"})
    run_source(JNU_EVENTS, db_path=db_path, detail_limit=2, fetcher=fetcher)
    assert len(fetcher.calls) == 1 + 2   # listing + only 2 detail pages


def test_pdf_items_are_not_fetched_as_detail(fake_fetcher, db_path):
    from sources.jnu import JNU_NOTICES
    notices_with_detail = replace(JNU_NOTICES, parse_detail=parse_event_detail, detail_limit=10, max_pages=1)
    fetcher = fake_fetcher({"https://www.jnu.ac.in/notices": "jnu/notices/normal_page.html"})
    run_source(notices_with_detail, db_path=db_path, fetcher=fetcher)
    assert all(not c.lower().endswith(".pdf") for c in fetcher.calls)


def test_registration_link_is_unwrapped_from_webmail_redirect(read_fixture):
    """Real page: 'Register here:' link wrapped in mail.mgovcloud.in/zm/reUrlCheck.do?url=..."""
    d = parse_event_detail(read_fixture("jnu/events/detail_159898442.html"), N442)
    assert d["registration_url"].startswith("https://docs.google.com/forms/")
    assert all("mgovcloud" not in link for link in d["links"])
