"""
The one generic entry point: run_source(source).

    fetch -> parse (with pagination) -> detail enrichment -> normalize -> store -> log

Nothing in here knows about JNU or any other institution. Every failure is
logged with source, URL, stage, error type and message, and recorded in the
`runs` table. A failed run never leaves half-written data (see storage.py).
"""

import threading
import time
import uuid
from typing import Any, Callable

from src import storage
from src.errors import FetchError, SchemaError, StageError
from src.fetch import FetchResult, fetch
from src.logging_config import get_logger
from src.pagination import collect_listing
from src.schema import now_iso, validate
from src.source import SourceConfig

_running: set[str] = set()
_running_lock = threading.Lock()


def run_source(
    source: SourceConfig,
    db_path: str = storage.DEFAULT_DB_PATH,
    max_pages: int | None = None,
    detail_limit: int | None = None,
    fetcher: Callable[[str], FetchResult] = fetch,
) -> dict[str, Any]:
    log = get_logger()
    run_id = uuid.uuid4().hex[:8]
    started = time.monotonic()
    run: dict[str, Any] = {"run_id": run_id, "source_name": source.name, "started_at": now_iso(),
                           "status": "running", "pages": 0, "parsed": 0}

    # Guard against overlapping runs of the same source inside this process
    with _running_lock:
        if source.name in _running:
            log.warning(f"SKIP source={source.name} reason=already_running")
            return {**run, "status": "skipped"}
        _running.add(source.name)

    stage = "fetch"
    url = source.listing_url
    log.info(f"START source={source.name} run_id={run_id} url={url} capabilities={','.join(source.capabilities)}")
    try:
        # FETCH + PARSE (pagination aware)
        listing = collect_listing(
            url, source.parse_listing, source.get_next_page_url,
            max_pages=max_pages if max_pages is not None else source.max_pages,
            source_name=source.name, fetcher=fetcher,
        )
        stage = "parse"
        raw_items = listing["items"]
        run.update(pages=listing["pages"], parsed=len(raw_items), stop_reason=listing["stop_reason"])
        if not raw_items:
            log.warning(f"EMPTY source={source.name} url={url} stage=parse "
                        f"message=listing returned 0 records (page empty or selectors no longer match)")

        # DETAIL ENRICHMENT (optional capability)
        stage = "detail"
        limit = detail_limit if detail_limit is not None else source.detail_limit
        if source.parse_detail and limit > 0:
            _enrich(source, raw_items, limit, fetcher)

        # NORMALIZE
        stage = "normalize"
        records = []
        for raw in raw_items:
            raw["source_name"] = source.name  # the registry name is the provenance, not the adapter
            try:
                record = source.normalize_item(raw)
                record["fetched_at"] = record.get("fetched_at") or now_iso()
                record["http_status"] = record.get("http_status") or listing["first_status"]
                validate(record)
                records.append(record)
            except (SchemaError, KeyError, ValueError, TypeError) as e:
                # one bad record is skipped, not fatal
                log.warning(f"NORMALIZE_SKIP source={source.name} item_url={raw.get('item_url')} "
                            f"error_type={type(e).__name__} message={e}")
        log.info(f"NORMALIZE source={source.name} records={len(records)} skipped={len(raw_items) - len(records)}")

        # STORE
        stage = "store"
        counts = storage.store_records(db_path, records)
        log.info(f"STORE source={source.name} new={counts['new']} existing={counts['existing']} "
                 f"changed={counts['changed']}")
        run.update(counts, status="success")

    except Exception as e:
        failed_stage = e.stage if isinstance(e, StageError) else stage
        failed_url = getattr(e, "url", url)
        run.update(status="failed", failed_stage=failed_stage, error=f"{type(e).__name__}: {e}")
        log.error(f"FAILED source={source.name} run_id={run_id} stage={failed_stage} url={failed_url} "
                  f"error_type={type(e).__name__} message={e}")
        if not isinstance(e, StageError):
            log.debug("traceback", exc_info=True)
    finally:
        with _running_lock:
            _running.discard(source.name)

    duration_ms = int((time.monotonic() - started) * 1000)
    run.update(finished_at=now_iso(), duration_ms=duration_ms)
    storage.record_run(db_path, run)
    log.info(f"END source={source.name} run_id={run_id} status={run['status']} duration_ms={duration_ms}")
    return run


def _enrich(source: SourceConfig, raw_items: list[dict[str, Any]], limit: int,
            fetcher: Callable[[str], FetchResult]) -> None:
    """Fetch up to `limit` detail pages. A failed detail page never drops its listing record."""
    log = get_logger()
    candidates = [i for i in raw_items if _is_html_detail(i.get("item_url", ""))][:limit]
    ok = failed = 0
    for item in candidates:
        extra = item.setdefault("extra", {})
        item_url = item["item_url"]
        try:
            result = fetcher(item_url)
            detail = source.parse_detail(result.text, item_url)
            item["detail"] = detail
            extra["detail_status"] = "ok"
            ok += 1
        except FetchError as e:
            extra["detail_status"] = f"failed: {e}"
            failed += 1
            log.warning(f"DETAIL_FAILED source={source.name} stage=detail url={item_url} "
                        f"error_type=FetchError status={e.status} message={e} (listing record kept)")
        except Exception as e:
            extra["detail_status"] = f"failed: {type(e).__name__}"
            failed += 1
            log.warning(f"DETAIL_FAILED source={source.name} stage=detail url={item_url} "
                        f"error_type={type(e).__name__} message={e} (listing record kept)")
    log.info(f"DETAIL source={source.name} attempted={len(candidates)} ok={ok} failed={failed}")


def _is_html_detail(url: str) -> bool:
    lower = url.lower().split("?")[0]
    return bool(url) and not lower.endswith((".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx"))
