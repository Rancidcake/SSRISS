# JNU Official Notices Scraper (`assignments/05_parsing/jnu/`)

This directory contains the production fetcher and HTML DOM parser for Jawaharlal Nehru University's official notice board (`https://www.jnu.ac.in/notices`).

## Architecture & Responsibilities

- **`scraper.py`**:
  - `fetch(url: str) -> str`: Executes low-level HTTP requests enforcing an explicit 10-second timeout and custom `User-Agent: WebMonitor/1.0 (JNU Academic Monitoring)`. Performs exception handling for network/timeout errors.
  - `parse_items(html: str, base_url: str) -> list[dict]`: Parses raw HTML document using BeautifulSoup, extracts table rows (`<tr>`), normalizes absolute URLs, and classifies items (`pdf_notice` vs `html_notice`).
  - `run_scraper(use_live: bool)`: Main runner that orchestrates fetching and parsing, persisting `sample_response.html` and `output.json`.

## Notice Classification Logic (`pdf_notice` vs `html_notice`)

JNU relies heavily on attached PDF circulars. The parser inspects the canonical `item_url`:
- If `item_url` contains `.pdf` or ends with `.pdf`, `item_type` is set to `"pdf_notice"`.
- Otherwise, `item_type` is set to `"html_notice"`.

*Note: PDF contents are not extracted in Week 1 per system requirements.*

## Output Files

1. **`sample_response.html`**: A cached local snapshot of raw server HTML from `https://www.jnu.ac.in/notices` to enable offline development and testing.
2. **`output.json`**: Extracted JSON array containing structured raw notice dictionaries.

## Usage Instructions

Run live extraction and output generation:
```bash
python3 assignments/05_parsing/jnu/scraper.py
```

Run offline extraction against the cached snapshot:
```python
from scraper import run_scraper
run_scraper(use_live=False)
```
