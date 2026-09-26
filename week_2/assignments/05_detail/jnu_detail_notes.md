# Assignment 5 — Detail-Page Enrichment (JNU Events)

Code: `sources/jnu.py` → `parse_events_listing`, `parse_event_detail`, `merge_listing_and_detail`;
generic orchestration in `src/runner.py::_enrich`.

## Flow

```text
/jnuevents (listing)            discover: title, start, end, item_url=/node/<id>
      │  only the first `detail_limit` items (5) — PDFs/images are never fetched as "detail"
      ▼
/node/<id> (detail)             enrich: title, start/end (<time datetime>), description,
      │                          venue, registration URL (redirect unwrapped), poster image, links
      ▼
merge_listing_and_detail()      detail value wins if non-empty, else listing value kept
      ▼
normalize_event()               + organising unit and speaker parsed from the title
```

## Live result (2026-09-26)

`python3 run.py run jnu_events` → `DETAIL source=jnu_events attempted=5 ok=5 failed=0`, 13 events stored.
Example enriched record (`node/159898442`):

| field | from listing | after detail |
|---|---|---|
| title | SCIS organises a lecture by Prof. D. S. Hooda | same |
| event_start / end | 2026-09-30 / 2026-09-30 | same |
| speakers | — | `["Prof. D. S. Hooda"]` (title) |
| organizations | — | `["SCIS", "Jawaharlal Nehru University"]` |
| description | — | "Register here: … Registration is free but …" |
| extra.registration_url | — | `https://docs.google.com/forms/d/…` (unwrapped from `mail.mgovcloud.in/zm/reUrlCheck.do?url=…`) |
| extra.image_urls | — | poster JPG |

When the same event was fetched again after the registration fix, storage reported `changed=1`,
so enrichment changes are picked up.

## Failure isolation (checkpoint)

- A detail fetch error (404, timeout) or a detail `ParseError` only marks that item:
  `extra.detail_status = "failed: HTTP 404"` + `WARNING DETAIL_FAILED ... (listing record kept)`.
- Live demo (`logs/failure_examples.log`, scenario 7): one node rewritten to `/node/999999999` →
  `attempted=3 ok=2 failed=1`, **all 13 records stored**, run `status=success`.
- Test: `tests/test_detail.py::test_detail_404_does_not_break_the_crawl`.

## Observations

- Many JNU event pages contain **only a poster image**. The real details (venue, time) are pixels,
  so `description` and `location` stay `null` (no OCR; out of scope). That's why only 1 of 5 sampled
  events has a description.
- Why not fetch every detail page? Listing already gives title + dates. Detail pages cost 1 request
  each (+1 s politeness), and the content rarely changes. `detail_limit` caps it per run.
