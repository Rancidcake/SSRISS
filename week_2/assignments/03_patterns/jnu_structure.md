# Assignment 3 — Structural Map: Jawaharlal Nehru University (JNU)

Verified live on **2026-09-26** (snapshots in `fixtures/jnu/live_snapshots/`).
The whole public site is **Drupal 10**; every listing is a Drupal *view*
(`div.view-id-<name>`), rendered server-side as an HTML `<table>`, with the standard Drupal pager.

> **Correction to Week 1 recon:** `https://www.jnu.ac.in/events` and `/news` return **HTTP 404**.
> The real pages are `/jnuevents` (upcoming), `/events-archive` (past) and `/jnunews`.

---

### Surface 1 — Notices & Circulars
```text
Surface:                JNU Notices & Circulars
Listing URL:            https://www.jnu.ac.in/notices
Record type:            announcement
Listing → detail?:      No. Title links straight to the file (91% PDF, 7% HTML landing page, 2% image)
Pagination?:            Yes. Drupal pager, ?page=0..3, 50 rows/page, <a rel="next">
Archive?:               The pagination IS the archive (oldest pages ~2023)
Fields on listing:      Sl. No., title, notice date ("Mon, 07-09-2026"), link (PDF/HTML)
Fields on detail:       None in HTML — content is inside the PDF (out of scope)
HTML / PDF / other:     HTML table → PDF files
Suitable for template?: Yes — "paginated table listing, no detail" pattern
Why?:                   Stable Drupal classes (td.views-field-title, td.views-field-field-notice-date)
Implemented:            sources/jnu.py → jnu_notices
```

### Surface 2 — Upcoming Events
```text
Surface:                JNU Events (upcoming)
Listing URL:            https://www.jnu.ac.in/jnuevents
Record type:            event
Listing → detail?:      Yes. Each row → /node/<id>
Pagination?:            No pager rendered (~15 rows). ?page=1 returns the real empty state.
Archive?:               Yes, separate page (Surface 3)
Fields on listing:      event start date, event end date, title, detail URL
Fields on detail:       title, start, end (<time datetime>), "Event Details" rich text:
                        poster image, description, venue, registration link, contact
HTML / PDF / other:     HTML; many detail pages are only a poster image (no text)
Suitable for template?: Yes — "listing → detail" pattern
Why?:                   Same Drupal field classes on every node (field--name-field-event-*)
Quirks:                 2 of 15 rows are Hindi copies (/hi/node/N) of English rows → folded;
                        registration links wrapped in a webmail redirect (mgovcloud) → unwrapped
Implemented:            sources/jnu.py → jnu_events
```

### Surface 3 — Events Archive
```text
Surface:                JNU Events Archive
Listing URL:            https://www.jnu.ac.in/events-archive
Record type:            event
Listing → detail?:      Yes, same /node/<id> pages as Surface 2
Pagination?:            Yes. ?page=0..40, 30 rows/page (~1,200 events), rel="next"
Archive?:               Yes. Also exposed filters (field_event_from_date_value, field_event_date_value)
Fields on listing:      ONLY end date + title (no start-date column!)
Fields on detail:       same as Surface 2 (start date recovered from detail)
HTML / PDF / other:     HTML
Suitable for template?: Yes — "paginated listing → detail" (the full pattern)
Why?:                   Same view (view-id-jnu_events) as Surface 2 → SAME parser, config only
Implemented:            sources/jnu.py → jnu_events_archive (max_pages=2, detail_limit=3)
```

### Surface 4 — Faculty directory (mapped, not implemented)
```text
Surface:                Faculty Directory / Faculty search by School/Centre
Listing URL:            https://www.jnu.ac.in/faculty-details2 , https://www.jnu.ac.in/faculty-search
Record type:            faculty
Listing → detail?:      Directory → school/centre → profile; profiles largely on https://jnu.irins.org (external)
Pagination?:            Not on the landing page
Suitable for template?: Partly — "directory → profile", but profiles live on a different system (IRINS)
Why not now?:           Two different sites; better as a separate adapter in Week 3
```

### Surface 5 — JNU News (mapped, not implemented)
`https://www.jnu.ac.in/jnunews` — 200, but content is a small block of links/PDFs rather than
a Drupal listing view; low value for monitoring.

---

## Patterns that look reusable across institutions

| Pattern | JNU example | Likely at other institutes |
|---|---|---|
| Table/card listing with title + date + link | notices, events | IIT Bombay, IISER Pune, TISS news/events |
| Page-number pagination (`?page=N`, `rel=next`) | notices, events-archive | any Drupal/WordPress site (`/page/N/`) |
| Listing → detail by stable URL | `/node/<id>` | IITB `/events/<slug>`, TISS `/event/<slug>` |
| Archive separate from "upcoming" | `/jnuevents` vs `/events-archive` | common |
| Mixed content (PDF + HTML + image + external link) | notices | very common in Indian university notice boards |

## Potential common template

```text
SourceConfig(name, listing_url, item_type, parse_listing, normalize_item,
             [get_next_page_url], [parse_detail], max_pages, detail_limit)
  + generic: fetch (timeout/UA/politeness), bounded pagination, detail enrichment
             with per-item error isolation, schema validation, SQLite upsert, logging, scheduling
```
For **any Drupal site** even `get_next_page_url` is reusable as-is (`nav.pager a[rel=next]`).

## Source-specific exceptions (stay inside sources/jnu.py)

- Container selectors: `div.view-id-notices`, `div.view-id-jnu_events`
- Empty state = view without `.view-content` (vs changed layout = `.view-content` without rows)
- Date formats: `Mon, 07-09-2026` (DD-MM-YYYY) on notices; `<time datetime="…T12:00:00Z">` on events
  (12:00Z is Drupal's placeholder time for date-only fields — only the date is kept)
- Archive listing has only the end-date column
- Hindi translation rows (`/hi/node/N`) inside the English listing
- Several notices share one HTML landing page (`/convocation`) → identity needs title+date
- `jnu.ac.in` vs `www.jnu.ac.in` used interchangeably in links
- Organising unit & speaker only available by parsing the title ("SCIS organises a lecture by Dr. X")

## Similar / different vs. other interns' sources

- **Similar:** everyone has a listing page with title + date + link, and at least one listing→detail surface.
  The runner, fetcher, storage, schema, pagination loop and scheduler do not care which site it is.
- **Different:** JNU is a pure Drupal table site, so pagination and "empty" detection are very
  regular. A WordPress site (common for IISER/TISS department pages) would use `/page/N/` and
  `<article>` cards instead of tables; that only changes the adapter's `parse_listing` and
  `get_next_page_url`.
