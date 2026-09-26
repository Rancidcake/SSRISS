"""
Source registry. Adding a new site = write sources/<site>.py exposing a
SourceConfig, then add it to SOURCES below. Nothing in src/ changes.

The *_fixture variants point the real JNU adapters at saved HTML under
fixtures/ (file:// URLs) - used for offline demos and the scheduler demo.
"""

from dataclasses import replace
from pathlib import Path

from sources.jnu import JNU_EVENTS, JNU_EVENTS_ARCHIVE, JNU_NOTICES
from src.source import SourceConfig

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

JNU_NOTICES_FIXTURE = replace(
    JNU_NOTICES,
    name="jnu_notices_fixture",
    display_name="JNU Notices (local pagination fixture)",
    listing_url=(FIXTURES / "pagination" / "page_1.html").as_uri(),
    max_pages=5,
)

SOURCES: dict[str, SourceConfig] = {
    s.name: s for s in [JNU_NOTICES, JNU_EVENTS, JNU_EVENTS_ARCHIVE, JNU_NOTICES_FIXTURE]
}


def get_source(name: str) -> SourceConfig:
    if name not in SOURCES:
        raise KeyError(f"unknown source {name!r}; known: {', '.join(sorted(SOURCES))}")
    return SOURCES[name]
