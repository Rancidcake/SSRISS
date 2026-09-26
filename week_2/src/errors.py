"""
Stage-tagged exceptions. The runner uses the `stage` attribute to report
exactly where a crawl failed: fetch, parse, normalize, store (or detail).
"""


class StageError(Exception):
    stage = "unknown"


class FetchError(StageError):
    stage = "fetch"

    def __init__(self, message: str, url: str, status: int | None = None):
        super().__init__(message)
        self.url = url
        self.status = status


class ParseError(StageError):
    """Raised when HTML does not look like the page the parser was written for."""
    stage = "parse"


class SchemaError(StageError):
    stage = "normalize"


class StorageError(StageError):
    stage = "store"
