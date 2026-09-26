"""
Generic HTTP client. Timeout, User-Agent and politeness delay live here and
ONLY here - source adapters never import `requests` themselves.

`file://` URLs are served from disk so local fixtures can be crawled through
exactly the same code path as live pages (used by tests and the scheduler demo).
"""

import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.request import url2pathname

import requests

from src.errors import FetchError
from src.logging_config import get_logger

DEFAULT_TIMEOUT = 15  # seconds
USER_AGENT = "WebMonitor/2.0 (JNU academic monitoring; internship project)"
POLITENESS_DELAY = 1.0  # seconds between live requests

_last_request_at = 0.0


@dataclass
class FetchResult:
    url: str
    status: int
    text: str
    duration_ms: int


def _fetch_file(url: str) -> FetchResult:
    started = time.monotonic()
    path = url2pathname(urlsplit(url).path)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        raise FetchError(f"local file not found: {path}", url=url, status=404)
    return FetchResult(url, 200, text, int((time.monotonic() - started) * 1000))


def fetch(url: str, timeout: float = DEFAULT_TIMEOUT) -> FetchResult:
    """Fetch a URL and return its body. Raises FetchError on any failure."""
    global _last_request_at
    log = get_logger()

    scheme = urlsplit(url).scheme
    if scheme == "file":
        result = _fetch_file(url)
        log.info(f"FETCH url={url} status={result.status} duration_ms={result.duration_ms}")
        return result
    if scheme not in ("http", "https"):
        raise FetchError(f"invalid URL (scheme {scheme!r} not supported)", url=url)

    wait = POLITENESS_DELAY - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)

    started = time.monotonic()
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    except requests.Timeout:
        raise FetchError(f"timeout after {timeout}s", url=url)
    except requests.ConnectionError as e:
        raise FetchError(f"connection failed: {type(e).__name__}: {_short(e)}", url=url)
    except requests.RequestException as e:
        raise FetchError(f"{type(e).__name__}: {_short(e)}", url=url)
    finally:
        _last_request_at = time.monotonic()

    duration_ms = int((time.monotonic() - started) * 1000)
    log.info(f"FETCH url={url} status={response.status_code} duration_ms={duration_ms}")

    if response.status_code >= 400:
        raise FetchError(f"HTTP {response.status_code}", url=url, status=response.status_code)
    return FetchResult(url, response.status_code, response.text, duration_ms)


def _short(e: Exception, limit: int = 200) -> str:
    text = str(e)
    return text if len(text) <= limit else text[:limit] + "..."
