# Assignment 4 — Pagination & Archive Traversal (JNU)

Code: `src/pagination.py` (generic loop), `sources/jnu.py::get_next_page_url` (JNU/Drupal pager).

## 4A — Local fixture exercise

`fixtures/pagination/page_1.html … page_3.html` — 3 pages × 5 notices, real JNU notices markup.
"Revised library timings" appears on **page 1 and page 2** (duplicate). Page 3 has no next link.
`loop_page.html` links to itself (loop trap).

```bash
python3 run.py run jnu_notices_fixture
```
```text
PARSE source=jnu_notices_fixture page=1 ... records=5
PARSE source=jnu_notices_fixture page=2 ... records=5
DUPLICATE source=jnu_notices_fixture item_url=https://www.jnu.ac.in/sites/default/files/inline-files/library.pdf page=2 (skipped)
PARSE source=jnu_notices_fixture page=3 ... records=5
PAGINATION source=jnu_notices_fixture pages=3 records=14 duplicates=1 stop=no_next
STORE source=jnu_notices_fixture new=14 existing=0 changed=0
```
Checkpoint: 15 rows → **14 DB rows**; rerun → `new=0 existing=14`.
Tests: `tests/test_pagination.py` (next link, all stop conditions, duplicate → one DB row).

## 4B — Real JNU pagination

Controlled live runs on 2026-09-26:

| Source | Pages available | Pages crawled | Records | Stop |
|---|---|---|---|---|
| `jnu_notices` (`/notices`) | 4 (50/page) | 2 | 100 | `max_pages` |
| `jnu_events_archive` (`/events-archive`) | 41 (30/page) | 2 | 58* | `max_pages` |

\* 60 rows, 2 were Hindi copies of English rows and were folded.
Every stored record keeps the page it was discovered on in `extra.discovered_on`.

### 1. What pagination pattern does the source use?
Drupal views pager, page-number style with a query parameter: `?page=0` (= no parameter), `?page=1`, …
Markup: `<nav class="pager"><li class="pager__item--next"><a href="?page=1" rel="next">`. There is also
a "Last »" link (`?page=3` for notices, `?page=40` for the archive).

### 2. How do you find the next page?
`get_next_page_url(html, current_url)` selects `nav.pager a[rel=next]` (fallback
`li.pager__item--next a`) and resolves the relative `?page=N` with `urljoin(current_url, href)`.
I follow the *next* link instead of generating `?page=N` myself, so if JNU changes the
parameter name the crawler still works (or stops cleanly).

### 3. What prevents infinite traversal?
In `collect_listing()` — any one of these stops the loop, and the reason is logged (`stop=`):
- `no_next` — no next link (last page)
- `max_pages` — per-source budget (`SourceConfig.max_pages`, overridable with `--max-pages`)
- `HARD_PAGE_LIMIT = 20` — global cap, whatever the config says
- `already_visited` — canonicalised next URL was already crawled (`?page=0` ≡ no param, query sorted,
  fragment dropped, host lower-cased) → catches loops (tested with `loop_page.html`)
- `empty_page` — a page with 0 records
- `off_site` — next link to a different host
- `fetch_error` — a later page fails → stop but **keep** records from earlier pages

### 4. How do you handle duplicates between pages?
Two layers:
1. During traversal, a `seen_items` set of `item_url` drops repeats (logged as `DUPLICATE ... (skipped)`).
   On a live listing, a new notice pushes the last row of page 1 onto page 2, so this does happen.
2. In storage, `item_url` is `UNIQUE` and writes are upserts, so even across runs an item is one row.
   The content hash ignores provenance (`source_url`, `discovered_on`, `fetched_at`), so a notice that
   slides from page 1 to page 2 counts as `existing`, not `changed`.

Identity pitfall found on the live site: 3 *different* notices ("7th Convocation", "9th Convocation",
"Special Convocation") all link to the same `/convocation` page. Using the link as identity would
silently merge them. Rule adopted: a PDF/image link is the identity; an HTML landing page is
not, so those notices get `link#notice-<hash(title,date)>`.

### 5. What would you use as the production crawl limit?
- `jnu_notices`: **max_pages=1 every 6 h** normally (50 newest notices; JNU posts a few a week),
  plus a one-off backfill of all 4 pages. 2 pages is the current config for safety margin.
- `jnu_events`: 1 page (there is only one), detail_limit 5 per run (the 5 soonest upcoming events; see adapter notes for the limitation).
- `jnu_events_archive`: **max_pages=2 weekly**. Never crawl all 41 pages on a schedule. If history
  is needed, one supervised backfill with the 1 s politeness delay (~41 requests).
