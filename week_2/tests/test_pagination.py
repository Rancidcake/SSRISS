"""Assignment 4A - bounded pagination over local fixtures."""

from sources import JNU_NOTICES_FIXTURE
from sources.jnu import get_next_page_url, parse_notices_listing
from src import storage
from src.pagination import canonical_url, collect_listing
from src.runner import run_source

from conftest import FIXTURES

PAGE_1 = (FIXTURES / "pagination" / "page_1.html").as_uri()
PAGE_2 = (FIXTURES / "pagination" / "page_2.html").as_uri()
LOOP = (FIXTURES / "pagination" / "loop_page.html").as_uri()


def collect(start, max_pages=10):
    return collect_listing(start, parse_notices_listing, get_next_page_url, max_pages=max_pages)


def test_get_next_page_url(read_fixture):
    assert get_next_page_url(read_fixture("pagination/page_1.html"), PAGE_1) == PAGE_2
    assert get_next_page_url(read_fixture("pagination/page_3.html"), PAGE_1) is None


def test_traverses_all_pages_and_stops_at_last():
    result = collect(PAGE_1)
    assert result["pages"] == 3
    assert result["stop_reason"] == "no_next"
    assert len(result["items"]) == 14  # 15 rows, 1 duplicate across pages 1-2
    assert result["duplicates"] == 1


def test_records_remember_the_page_they_were_found_on():
    items = collect(PAGE_1)["items"]
    assert items[0]["extra"]["discovered_on"] == PAGE_1
    assert items[5]["extra"]["discovered_on"] == PAGE_2


def test_max_pages_limit():
    result = collect(PAGE_1, max_pages=2)
    assert result["pages"] == 2
    assert result["stop_reason"] == "max_pages"


def test_loop_is_detected():
    result = collect(LOOP)
    assert result["pages"] == 1
    assert result["stop_reason"] == "already_visited"


def test_stops_on_empty_page(fake_fetcher):
    fetcher = fake_fetcher({
        "https://www.jnu.ac.in/notices": "jnu/notices/normal_page.html",       # next -> ?page=1
        "https://www.jnu.ac.in/notices?page=1": "jnu/notices/empty_listing.html",
    })
    result = collect_listing("https://www.jnu.ac.in/notices", parse_notices_listing, get_next_page_url,
                             max_pages=5, fetcher=fetcher)
    assert result["stop_reason"] == "empty_page"
    assert len(result["items"]) == 10


def test_later_page_failure_keeps_earlier_records(fake_fetcher):
    fetcher = fake_fetcher({"https://www.jnu.ac.in/notices": "jnu/notices/normal_page.html"})  # ?page=1 -> 404
    result = collect_listing("https://www.jnu.ac.in/notices", parse_notices_listing, get_next_page_url,
                             max_pages=5, fetcher=fetcher)
    assert result["stop_reason"] == "fetch_error"
    assert len(result["items"]) == 10


def test_canonical_url():
    assert canonical_url("https://WWW.jnu.ac.in/notices/?page=0#top") == "https://www.jnu.ac.in/notices"
    assert canonical_url("https://www.jnu.ac.in/notices?b=2&page=1&a=1") == \
        "https://www.jnu.ac.in/notices?a=1&b=2&page=1"


def test_duplicate_across_pages_creates_one_db_row(db_path):
    """Checkpoint 4A: the duplicate record must not create a duplicate database row."""
    result = run_source(JNU_NOTICES_FIXTURE, db_path=db_path)
    assert result["status"] == "success"
    assert storage.count_items(db_path) == 14
    urls = [i["item_url"] for i in storage.get_items(db_path)]
    assert len(urls) == len(set(urls))
