# Assignment 9 — Template Swap Review (Mayank ↔ Soumyadipta)

> ⚠️ **MAYANK MUST DO THIS PART.** It depends on Soumyadipta's (TISS) framework, which is not
> in this repository. The questions and hints below are a skeleton; replace every `TODO`.
>
> **The other direction** (Soumyadipta adding a source to *this* framework) is prepared:
> send them `ADDING_A_SOURCE.md`.

## Setup

- Partner framework: `TODO: repo link / folder`
- New source I added to it: `TODO: e.g. an IIT/IISER/other university public event or notice page
  that nobody has implemented yet (not JNU, not TISS)`
- Listing URL: `TODO`
- Records collected (controlled sample): `TODO: e.g. 10 records, 1 page`
- Files I created: `TODO: e.g. sources/<new>.py, fixtures/<new>/listing.html`
- Files I had to modify in their core (if any): `TODO`

## 1. What could be reused unchanged?
TODO. Hint: fetcher? runner? storage? logging? schema? scheduler? Say which and how you know
(e.g. "I only called run_source(...) and it worked").

## 2. What had to be source-specific?
TODO. Hint: URL, selectors, date format, how the next page is found, identity rules.

## 3. What generic abstraction was missing?
TODO. Hint: was there a place to put per-source limits? a way to plug in a detail parser?
a shared date parser? a registry, or did you have to edit the runner to add your source?

## 4. Did you find code that was generic in name but actually source-specific?
TODO. Hint: look for TISS URLs, TISS selectors, hard-coded `source_name`, TISS date formats or
TISS field names inside their "generic" files (runner/storage/normalizer).
(For comparison, our own example: in Week 1, `storage.py` defaulted `source_name` to
`"jnu_official_notices"` and the normalizer hard-coded `"Jawaharlal Nehru University"`. Week 2
moved both into the adapter / runner.)

## 5. What would you refactor before Week 3?
TODO. 2–4 concrete bullets.

## Feedback received from Soumyadipta on MY framework
TODO: paste what they reported after following ADDING_A_SOURCE.md
(what was easy, what broke, what they had to change in `src/`).
