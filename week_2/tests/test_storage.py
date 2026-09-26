"""Shared storage: idempotency, change detection, atomic writes."""

import pytest

from src import storage
from src.errors import StorageError
from src.schema import build_record


def notice(url="https://www.jnu.ac.in/a.pdf", title="Holiday notice", **kw):
    return build_record("announcement", source_name="jnu_notices", item_url=url, title=title,
                        published_at="2026-09-07", **kw)


def test_new_then_existing(db_path):
    assert storage.store_records(db_path, [notice()], seen_at="t1") == {"new": 1, "existing": 0, "changed": 0}
    assert storage.store_records(db_path, [notice()], seen_at="t2") == {"new": 0, "existing": 1, "changed": 0}
    [row] = storage.get_items(db_path)
    assert (row["first_seen_at"], row["last_seen_at"]) == ("t1", "t2")


def test_changed_content_is_detected(db_path):
    storage.store_records(db_path, [notice()])
    counts = storage.store_records(db_path, [notice(title="Holiday notice (revised)")])
    assert counts["changed"] == 1
    assert storage.get_items(db_path)[0]["title"] == "Holiday notice (revised)"


def test_provenance_change_is_not_a_content_change(db_path):
    """A notice sliding from page 1 to page 2 is the same notice."""
    storage.store_records(db_path, [notice(source_url="https://www.jnu.ac.in/notices",
                                           extra={"discovered_on": "https://www.jnu.ac.in/notices"})])
    counts = storage.store_records(db_path, [notice(source_url="https://www.jnu.ac.in/notices?page=1",
                                                    fetched_at="later",
                                                    extra={"discovered_on": "https://www.jnu.ac.in/notices?page=1"})])
    assert counts == {"new": 0, "existing": 1, "changed": 0}


def test_failed_batch_is_rolled_back(db_path):
    storage.store_records(db_path, [notice()])
    bad = notice(url="https://www.jnu.ac.in/b.pdf")
    bad["item_url"] = None  # violates NOT NULL mid-batch
    with pytest.raises(StorageError, match="rolled back"):
        storage.store_records(db_path, [notice(url="https://www.jnu.ac.in/c.pdf"), bad])
    assert storage.count_items(db_path) == 1  # c.pdf was NOT half-written


def test_unwritable_database_raises_storage_error(tmp_path):
    with pytest.raises(StorageError):
        storage.store_records(str(tmp_path), [notice()])  # a directory, not a file


def test_different_institutions_share_one_table(db_path):
    other = build_record("announcement", source_name="tiss_news", item_url="https://tiss.edu/x", title="TISS news")
    storage.store_records(db_path, [notice(), other])
    assert storage.count_items(db_path) == 2
    assert storage.count_items(db_path, "tiss_news") == 1
