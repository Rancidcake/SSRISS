"""
Shared test setup.

- The network is BLOCKED for every test (autouse). If any test accidentally
  talks to the live site it fails - this is how we prove the suite is offline.
- `fake_fetcher` maps URLs to fixture files so the full runner (fetch -> parse
  -> detail -> normalize -> store) can be exercised without HTTP.
"""

import logging
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.errors import FetchError  # noqa: E402
from src.fetch import FetchResult  # noqa: E402
from src.logging_config import LOGGER_NAME  # noqa: E402

FIXTURES = ROOT / "fixtures"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise OSError("network access is disabled during tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr("src.fetch.POLITENESS_DELAY", 0)


@pytest.fixture
def read_fixture():
    def _read(relative: str) -> str:
        return (FIXTURES / relative).read_text(encoding="utf-8")
    return _read


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def logs(caplog):
    """Capture the 'monitor' logger (it does not propagate to root)."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)
    yield caplog
    logger.removeHandler(caplog.handler)


@pytest.fixture
def fake_fetcher():
    """fake_fetcher({url: "fixture/path.html" | 404}) -> fetch-compatible callable that records calls."""
    def build(routes: dict):
        calls = []

        def fetch(url: str) -> FetchResult:
            calls.append(url)
            target = routes.get(url)
            if target is None:
                raise FetchError("HTTP 404", url=url, status=404)
            if isinstance(target, int):
                raise FetchError(f"HTTP {target}", url=url, status=target)
            return FetchResult(url, 200, (FIXTURES / target).read_text(encoding="utf-8"), 1)

        fetch.calls = calls
        return fetch
    return build
