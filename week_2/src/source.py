"""
The contract every source adapter fills in. Only `parse_listing` and
`normalize_item` are mandatory; pagination and detail enrichment are optional
capabilities the runner uses only if they are provided.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

ListingParser = Callable[[str, str], list[dict[str, Any]]]      # (html, page_url) -> raw items
NextPageFinder = Callable[[str, str], str | None]               # (html, page_url) -> next url
DetailParser = Callable[[str, str], dict[str, Any]]             # (html, item_url) -> detail fields
Normalizer = Callable[[dict[str, Any]], dict[str, Any]]         # raw item -> schema record


@dataclass
class SourceConfig:
    name: str                       # stable id, used in logs and DB (e.g. "jnu_notices")
    display_name: str
    institution: str
    listing_url: str
    item_type: str                  # "event" | "announcement" | "faculty"
    parse_listing: ListingParser
    normalize_item: Normalizer
    get_next_page_url: NextPageFinder | None = None
    parse_detail: DetailParser | None = None
    max_pages: int = 1              # pagination budget per run
    detail_limit: int = 0           # max detail pages fetched per run (0 = off)
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def capabilities(self) -> list[str]:
        caps = ["listing"]
        if self.get_next_page_url:
            caps.append("pagination")
        if self.parse_detail:
            caps.append("detail")
        return caps
