# Assignment 6 — Schema Validation by Inspection

Sample: **10 live records** from `data/monitor.db` (2026-09-26): 5 × `jnu_notices` (announcement),
5 × `jnu_events` that were detail-enriched (event). Shared schema is defined in `src/schema.py`.

## Field-by-field

| Field | Present | Raw source representation | Normalized representation | Req? | Generic / source-specific |
|---|---|---|---|---|---|
| `source_name` | 10/10 | (none — set by runner from registry) | `"jnu_notices"` | required | generic (provenance) |
| `source_url` | 10/10 | page URL crawled | `"https://www.jnu.ac.in/notices?page=1"` | optional | generic (provenance) |
| `item_url` | 10/10 | `href="/sites/default/files/…pdf"`, `href="/node/159898390"`, `https://jnu.ac.in/convocation` | absolute, `www.` canonical; landing pages get `#notice-<hash>` | **required** | generic (**identifier**) |
| `item_type` | 10/10 | implied by page | `"announcement"` / `"event"` | required | generic |
| `title` | 10/10 | `<a>Circular regarding holiday…</a>` / `<div class="field__item">` | whitespace-collapsed string | **required** | generic |
| `published_at` | 5/5 notices | `Mon, 07-09-2026` (DD-MM-YYYY) | `"2026-09-07"` ISO date | optional | generic |
| `event_start` | 5/5 events | `<time datetime="2026-09-29T12:00:00Z">29/09/2026</time>` | `"2026-09-29"` | optional | generic |
| `event_end` | 5/5 events | same as above | `"2026-09-29"` | optional | generic |
| `location` | 0/10 | venue text inside detail rich-text (only on text-heavy pages) | string or `null` | optional | generic field, source-specific extraction |
| `speakers` | 3/5 events | inside title: "…lecture by Dr. Divya P. Kumar" | `["Dr. Divya P. Kumar"]` | optional | generic field, source-specific extraction |
| `organizations` | 10/10 | inside title: "SCIS organises…", "CIPOD, SIS organises…" | `["SCIS", "Jawaharlal Nehru University"]` | optional | generic |
| `description` | 1/10 | detail "Event Details" rich text (mostly a poster image) | plain text or `null` | optional | generic |
| `raw_text` | 10/10 | row cells | `"Circular … \| Mon, 07-09-2026"` (Sl. No. excluded) | optional | generic (provenance) |
| `fetched_at` | 10/10 | — | `"2026-09-26T15:52:01+05:30"` | optional | generic (provenance) |
| `http_status` | 10/10 | response status | `200` | optional | generic (provenance) |
| `first_seen_at` / `last_seen_at` | 10/10 | — | set by storage, never by adapters | — | generic (provenance) |
| `extra.date_raw` | notices | `Mon, 07-09-2026` | kept verbatim | — | source-specific |
| `extra.document_type` | notices | from link extension | `pdf` (91/100) / `html` (7) / `image` (2) | — | source-specific |
| `extra.link_url` | notices | the real link | absolute URL | — | source-specific |
| `extra.start_raw`/`end_raw` | events | `<time datetime>` | verbatim | — | source-specific |
| `extra.image_urls` | events | poster `<img src>` | list of absolute URLs | — | source-specific |
| `extra.registration_url` | 1 event | `Register here: <a href=mgovcloud…?url=…>` | unwrapped Google Form URL | — | source-specific (could be promoted later) |
| `extra.title_hi` | 1 event | Hindi duplicate row | Hindi title | — | source-specific |
| `extra.discovered_on` | all | page URL | URL | — | provenance |
| `extra.detail_status` | enriched events | — | `ok` / `failed: HTTP 404` | — | provenance |

## Answers

**1. Which fields genuinely belong in the shared schema?**
Identity + provenance (`source_name, source_url, item_url, item_type, raw_text, fetched_at,
http_status, first_seen_at, last_seen_at`) for every type, then per type:
event → `title, event_start, event_end, location, speakers, organizations, description`;
announcement → `title, published_at, organizations, description`;
faculty → `name, title, department, bio, research_areas`.
Even when JNU fills a field 0/10 times (`location`), it stays because other institutions will fill it.

**2. Which fields should remain source-specific?**
Everything in `extra`: `date_raw`, `document_type`, `link_url`, `start_raw/end_raw`,
`image_urls`, `title_hi`, `sl_no`. They are useful for debugging or JNU-only features but are not
comparable across institutions. `build_record()` pushes any unknown key into `extra` instead of
creating a new column, so one odd page can't grow the schema.

**3. Which values should be lists?**
`speakers`, `organizations`, `research_areas` (and `extra.image_urls`, `extra.links`).
One event can have many speakers or co-organisers (e.g. "CIPOD, SIS"); a string would force
later splitting. `validate()` rejects a non-list value for these.

**4. Which fields are identifiers?**
`item_url` is the identity: `UNIQUE` in SQLite, used for dedup across pages, runs and sources.
Rules: absolute URL, `www.` host canonicalised, and a synthetic `#notice-<sha1(title|date)>` /
`#item-<…>` suffix when the link is shared by several items or missing. `content_hash` (storage)
identifies a *version* of the item.

**5. Which fields represent provenance rather than content?**
`source_name, source_url, raw_text, fetched_at, http_status, first_seen_at, last_seen_at,
extra.discovered_on, extra.detail_status`. They are **excluded from the content hash**, so an item
seen from a different page or at a different time is `existing`, not `changed` (tested:
`tests/test_storage.py::test_provenance_change_is_not_a_content_change`).

## Checkpoint

Two institutions write into the same `items` table with the same field names: see
`tests/test_storage.py::test_different_institutions_share_one_table` (a JNU notice and a TISS
record side by side). The DB stores searchable columns (`item_url, source_name, item_type, title,
primary_date`) plus the full normalized record as JSON.
