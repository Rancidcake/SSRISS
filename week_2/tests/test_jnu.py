"""Assignment 0 - JNU parser tests, entirely from saved fixtures."""

import pytest

from sources.jnu import (EVENTS_URL, NOTICES_URL, get_next_page_url, normalize_event, normalize_notice,
                         parse_events_listing, parse_notices_listing)
from src import storage
from src.errors import ParseError
from src.schema import COMMON_FIELDS, TYPE_FIELDS


def notices(read_fixture, name):
    return parse_notices_listing(read_fixture(f"jnu/notices/{name}"), NOTICES_URL)


def test_parse_expected_number_of_items(read_fixture):
    assert len(notices(read_fixture, "normal_page.html")) == 10


def test_parse_title(read_fixture):
    items = notices(read_fixture, "normal_page.html")
    assert items[0]["title"] == "Circular regarding holiday on 11.09.2026"
    assert all(i["title"] == i["title"].strip() and "  " not in i["title"] for i in items)


def test_parse_url(read_fixture):
    items = notices(read_fixture, "normal_page.html")
    assert items[0]["item_url"] == "https://www.jnu.ac.in/sites/default/files/inline-files/CIRCULAR09072026.pdf"
    assert all(i["item_url"].startswith("https://") for i in items)  # relative hrefs made absolute


def test_missing_optional_field(read_fixture):
    items = notices(read_fixture, "missing_optional_field.html")
    assert len(items) == 4
    no_date, no_link, html_page = items[1], items[2], items[3]

    assert no_date["date_raw"] is None
    assert normalize_notice({**no_date, "source_name": "jnu_notices"})["published_at"] is None

    # a row without a link still gets a unique, stable identity
    assert no_link["item_url"].startswith("https://www.jnu.ac.in/notices#item-")
    assert no_link["document_type"] == "none"
    assert notices(read_fixture, "missing_optional_field.html")[2]["item_url"] == no_link["item_url"]

    assert html_page["document_type"] == "html"
    assert html_page["link_url"] == "https://www.jnu.ac.in/convocation"
    assert html_page["item_url"].startswith("https://www.jnu.ac.in/convocation#notice-")


def test_empty_listing(read_fixture):
    assert notices(read_fixture, "empty_listing.html") == []


def test_changed_card_structure_raises(read_fixture):
    """A redesign must fail loudly, not look like 'no new notices'."""
    with pytest.raises(ParseError, match="layout changed"):
        notices(read_fixture, "changed_card_structure.html")


def test_wrong_page_raises():
    with pytest.raises(ParseError, match="not found"):
        parse_notices_listing("<html><body><h1>Maintenance</h1></body></html>", NOTICES_URL)


def test_normalization_shape(read_fixture):
    raw = notices(read_fixture, "normal_page.html")[0]
    record = normalize_notice({**raw, "source_name": "jnu_notices"})

    expected = set(COMMON_FIELDS) | set(TYPE_FIELDS["announcement"]) | {"extra"}
    assert set(record) == expected
    assert record["item_type"] == "announcement"
    assert record["published_at"] == "2026-09-07"
    assert record["organizations"] == ["Jawaharlal Nehru University"]
    assert record["extra"]["document_type"] == "pdf"
    assert record["extra"]["date_raw"] == "Mon, 07-09-2026"


def test_duplicate_item(read_fixture, db_path):
    items = notices(read_fixture, "duplicate_item.html")
    assert len(items) == 3  # parser reports what is on the page...
    records = [normalize_notice({**i, "source_name": "jnu_notices"}) for i in items]
    counts = storage.store_records(db_path, records)
    assert counts == {"new": 2, "existing": 1, "changed": 0}
    assert storage.count_items(db_path) == 2  # ...storage keeps one row per item_url


def test_next_page_url_from_real_pager(read_fixture):
    assert get_next_page_url(read_fixture("jnu/notices/normal_page.html"), NOTICES_URL) == \
        "https://www.jnu.ac.in/notices?page=1"
    assert get_next_page_url(read_fixture("jnu/notices/missing_optional_field.html"), NOTICES_URL) is None


# --- regression tests against full live snapshots (captured 2026-09-26) ------

def test_live_snapshot_notices_regression(read_fixture):
    page0 = parse_notices_listing(read_fixture("jnu/live_snapshots/notices_page0.html"), NOTICES_URL)
    page1 = parse_notices_listing(read_fixture("jnu/live_snapshots/notices_page1.html"), NOTICES_URL + "?page=1")
    assert len(page0) == 50 and len(page1) == 50
    assert sum(i["document_type"] == "pdf" for i in page0) >= 40


def test_live_snapshot_events_regression(read_fixture):
    items = parse_events_listing(read_fixture("jnu/live_snapshots/jnuevents.html"), EVENTS_URL)
    # 15 rows, but 2 are Hindi copies (/hi/node/N) of English rows -> folded into 13 events
    assert len(items) == 13
    assert all(i["item_url"].startswith("https://www.jnu.ac.in/node/") for i in items)
    netcrypt = next(i for i in items if i["item_url"].endswith("/node/159897904"))
    assert netcrypt["extra"]["title_hi"].startswith("एससीएसएस")
    assert parse_events_listing(read_fixture("jnu/live_snapshots/jnuevents_page1_empty.html"), EVENTS_URL) == []


def test_event_normalization_extracts_org_and_speaker(read_fixture):
    raw = parse_events_listing(read_fixture("jnu/events/listing.html"), EVENTS_URL)[0]
    record = normalize_event({**raw, "source_name": "jnu_events"})
    assert record["title"] == "SCIS organises a lecture by Dr. Divya P. Kumar"
    assert record["event_start"] == "2026-09-29"
    assert record["organizations"] == ["SCIS", "Jawaharlal Nehru University"]
    assert record["speakers"] == ["Dr. Divya P. Kumar"]


def test_serial_number_shift_is_not_a_change(read_fixture, db_path):
    """Sl. No. shifts whenever JNU posts a new notice; that must not mark old notices as changed."""
    html = read_fixture("jnu/notices/normal_page.html")
    first = [normalize_notice({**i, "source_name": "jnu_notices"}) for i in parse_notices_listing(html, NOTICES_URL)]
    shifted_html = html.replace('headers="view-counter-table-column">', 'headers="view-counter-table-column">9')
    shifted = [normalize_notice({**i, "source_name": "jnu_notices"})
               for i in parse_notices_listing(shifted_html, NOTICES_URL)]
    storage.store_records(db_path, first)
    assert storage.store_records(db_path, shifted) == {"new": 0, "existing": 10, "changed": 0}


def test_notices_sharing_a_landing_page_stay_separate(read_fixture):
    """Live bug found 2026-09-26: 3 different convocation notices all link to /convocation."""
    items = [i for f in ("notices_page0", "notices_page1")
             for i in parse_notices_listing(read_fixture(f"jnu/live_snapshots/{f}.html"), NOTICES_URL)]
    convocation = [i for i in items if i["link_url"] and i["link_url"].endswith("/convocation")]
    assert len(convocation) == 3
    assert len({i["item_url"] for i in convocation}) == 3
    assert {i["link_url"] for i in convocation} == {"https://www.jnu.ac.in/convocation"}  # host canonicalised
