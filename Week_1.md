# Week 1 — Technical Web Monitoring Fundamentals

> **Purpose:** Build the common foundation we need before the team begins creating reusable academic-site templates in Week 2.
>
> **How to use this document:** Work through the sections **in order**. Each section contains learning material followed by an assignment. **Complete the assignment and its checkpoint before moving to the next section.**
>
> The focus this week is fundamentals and correctness, not the number of websites scraped. The target mental model by the end of the week is:
>
> **public surface → HTTP request → HTML/DOM → selectors → extraction → normalization → storage**

---

## Targets for hands-on work

The learning material is the same for everyone. When an assignment calls for institution-specific work, use these targets:

| Intern | Institution |
|---|---|
| **Saanvi** | IISER Pune |
| **Parth** | IIT Bombay |
| **Mayank** | JNU |
| **Soumyadipta** | TISS |

The goal is **not** to exhaustively crawl these institutions in Week 1. They are simply four different real-world surfaces on which to practice the same concepts.

---

# 0. Environment and Working Conventions

Before beginning the technical material, everyone should have the same basic environment.

## Required setup

- Python 3.10+ recommended
- Git
- VS Code / Cursor / preferred IDE
- Chrome or Firefox with Developer Tools

Suggested packages:

```bash
pip install requests beautifulsoup4 lxml pytest
```

Recommended project structure to begin with:

```text
web-monitor/
├── README.md
├── requirements.txt
├── src/
├── sources/
├── fixtures/
├── tests/
└── data/
```

## Working rules for the week

1. Do not write a crawler before understanding the page/surface.
2. Prefer RSS/Atom, sitemaps, structured pages, and ordinary HTML over browser automation.
3. No attempts to evade 403s, CAPTCHAs, rate limits, login walls, or other access boundaries.
4. Every network request must use a timeout.
5. Separate fetching, parsing, normalization, and persistence.
6. Save small HTML fixtures for testing instead of repeatedly hitting a live site.
7. Correctness first. Speed and scale come later.

---

# 1. Understand How the Web and HTTP Work

Before extracting anything from a website, understand what actually happens when a browser or Python program requests a URL.

## Concepts to learn

You should be able to explain:

- Client vs server
- URL structure
  - scheme
  - hostname
  - path
  - query parameters
  - fragment
- HTTP vs HTTPS
- Request → response lifecycle
- HTTP methods, especially `GET`
- Request headers
- Response headers
- `User-Agent`
- `Content-Type`
- Common HTTP status codes:
  - `200`
  - `301` / `302`
  - `400`
  - `401`
  - `403`
  - `404`
  - `429`
  - `500`
  - `502`
  - `503`
- Redirects
- Timeouts
- HTML responses vs JSON responses vs PDFs/files
- Why browsers are only one type of HTTP client

## Read

### MDN — Overview of HTTP
https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview

Focus on:

- Components of HTTP-based systems
- Basic aspects of HTTP
- HTTP flow
- HTTP messages

### Requests — Quickstart
https://requests.readthedocs.io/en/latest/user/quickstart/

Focus on:

- Making a request
- Response content
- JSON response content
- Response status codes
- Response headers
- Redirection and history
- Timeouts

## Watch

### HTTP Crash Course & Exploration — Traversy Media
https://www.youtube.com/watch?v=iYM2zFP3Zn0

The goal is not to rote-learn. You should finish with a clear mental model of what is sent by a client and what comes back from a server.

---

## Assignment 1 — HTTP Detective

Write:

```text
assignments/01_http/http_probe.py
```

The script should accept a URL and print at least:

```text
requested_url
final_url
status_code
content_type
content_length
redirect_history
selected_response_headers
first_200_characters_of_body
```

Your code must:

- use `requests`
- specify a timeout
- handle request failures without crashing with an unreadable stack trace
- distinguish between HTML and non-HTML responses

Test it against several safe/public URLs representing different behaviors:

1. A normal HTML page
2. A redirect
3. A JSON response
4. A URL that returns `404`
5. A `robots.txt` file

Optional – create:

```text
assignments/01_http/findings.md
```

Answer:

1. What is the difference between the requested URL and final URL?
2. How can your program determine whether the server returned HTML?
3. What should a crawler do after receiving `429`?
4. What should your crawler do after receiving `403`?
5. Why should every HTTP request have a timeout?
6. Why is repeatedly retrying a failing endpoint dangerous?

### Checkpoint before moving on

You should be able to explain every line of `http_probe.py` without relying on an AI assistant to explain it for you.

---

# 2. Crawling Boundaries, `robots.txt`, and Surface Selection

A technically possible crawl is not automatically an appropriate crawl.

The project should start from the **lowest-complexity appropriate public surface**.

Prefer roughly this order when available:

```text
RSS / Atom
    ↓
Sitemap
    ↓
Structured event/news listing
    ↓
Ordinary server-rendered HTML
    ↓
More complex mechanisms only when genuinely required
```

## Concepts to learn

- What `robots.txt` does
- What `robots.txt` does **not** do
- Sitemap basics
- RSS / Atom basics
- Publicly accessible vs suitable for automated collection
- Rate limiting
- Polite crawling
- Explicit access boundaries
- Why `403`, login walls, CAPTCHAs, etc. should not trigger attempts at circumvention
- Why high-yield listing/aggregation pages are generally better than crawling an entire domain
- Difference between:
  - listing page
  - detail page
  - archive
  - pagination
  - sitemap
  - feed

## Read

### Google Search Central — Introduction to `robots.txt`
https://developers.google.com/search/docs/crawling-indexing/robots/intro

### Google Search Central — Crawling and Indexing Overview
https://developers.google.com/search/docs/crawling-indexing

You do not need to learn Google's search-ranking behavior. Focus on the mechanics of crawling controls, sitemaps, and discoverable public surfaces.

---

## Assignment 2 — Surface Reconnaissance

Investigate your assigned institution manually.

Do **not** build its scraper yet.

Create:

```text
assignments/02_recon/<institution>_surface_notes.md
```

Document:

### A. Domain and access

- Main domain
- `robots.txt` URL
- Relevant rules you observed
- Whether a sitemap is discoverable
- Whether RSS/Atom appears to exist

### B. Relevant public content surfaces

Find likely surfaces for:

- events
- seminars/talks
- news/announcements
- research-related updates

For each candidate surface record:

```text
URL:
Surface type:
What it contains:
Listing page or detail page:
HTML / PDF / other:
Pagination:
Approximate number of useful records visible:
Why this is or is not a good monitoring surface:
```

### C. Surface recommendation

Choose **one** page/surface that you think would be a good Week 1 extraction target.

Explain:

1. Why this surface is useful.
2. Why it is preferable to crawl a larger portion of the domain.
3. Whether it is ordinary HTML or something more complicated.
4. Any access/politeness considerations.
5. What fields appear extractable.

### Checkpoint before moving on

Another intern should be able to read your notes and understand **where they would start collecting information and why**, without opening the site themselves.

---

# 3. HTML and the DOM

Now learn to stop seeing webpages primarily as visual pages and start seeing them as structured documents.

## Concepts to learn

- HTML elements and tags
- Attributes
- `id`
- `class`
- Links and `href`
- Images and `src`
- Semantic elements
- Parent / child relationships
- Siblings
- Nested structures
- Repeated record/card structures
- Raw HTML vs the browser's DOM
- Browser Developer Tools:
  - Elements / Inspector
  - View source
  - Network tab at a basic level

## Read

### MDN — Introduction to the DOM
https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction

### MDN — Introduction to HTML
https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content/Basic_HTML_syntax

Read for structure, not for frontend-design expertise.

## Watch

### JavaScript DOM Crash Course — Traversy Media
https://www.youtube.com/watch?v=0ik6X4DJKCc

Even though the video uses JavaScript, your objective is to understand:

- DOM structure
- nodes/elements
- parent-child relationships
- selecting elements
- how browsers represent HTML

---

## Assignment 3 — DOM Mapping

Use a small instructor-provided or self-created HTML file containing 8–10 fictional university events.

Each record should resemble something like:

```html
<div class="event-card">
    <h2 class="title">
        <a href="/events/ai-policy">AI and Public Policy</a>
    </h2>
    <time datetime="2026-09-10">10 September 2026</time>
    <span class="speaker">Dr. Example</span>
    <span class="location">Auditorium</span>
</div>
```

Using browser Developer Tools, identify:

- the repeated event container
- title
- link
- date
- speaker
- location

Create:

```text
assignments/03_dom/dom_map.md
```

For every field describe:

```text
Field:
HTML tag:
Important class/id/attribute:
Parent:
Relevant children:
How I know this belongs to one event record:
```

Then inspect the real institutional surface chosen in Assignment 2 and produce the same map for it.

### Checkpoint before moving on

Given unfamiliar HTML, you should be able to identify the **record boundary** — i.e., which repeated element represents one event/news item — before writing any scraping code.

---

# 4. CSS Selectors and XPath

Selectors are how a scraper identifies the pieces of the DOM that matter.

## CSS concepts to learn

Master these first:

```css
div
.event-card
#events
a[href]
a[href="/example"]
.event-card a
.event-card > a
.event-card .title
:first-child
:nth-child(...)
```

Understand the difference between:

```css
parent child
```

and:

```css
parent > child
```

Do not try to memorize every CSS selector.

## XPath concepts to learn

Understand basic XPath expressions such as:

```xpath
//div
//a
//div[@class="event-card"]
//div[contains(@class, "event-card")]
//div//a
//a/@href
```

CSS selectors will often be sufficient, but the team should be comfortable reading basic XPath because it is frequently useful in extraction tooling.

## Read

### MDN — CSS Selectors
https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Selectors

### MDN — CSS Selectors and Combinators
https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Selectors/Selectors_and_combinators

### MDN — XPath
https://developer.mozilla.org/en-US/docs/Web/XML/XPath

---

## Assignment 4 — Selector Workbook

For the fictional HTML fixture from Assignment 3, write both a CSS selector and an XPath expression for:

- all records
- title
- URL
- date
- speaker
- location

Use this table:

| Field | CSS selector | XPath |
|---|---|---|
| Record | | |
| Title | | |
| URL | | |
| Date | | |
| Speaker | | |
| Location | | |

Next, create the same table for your assigned real-world institutional surface.

Save it as:

```text
assignments/04_selectors/<institution>_selector_map.md
```

If a field is not available on the listing page, explicitly write:

```text
Not available on listing page.
May require visiting the detail page.
```

Do **not** invent a selector for information that is not there.

### Robustness challenge

Modify the fictional fixture slightly. For example:

```html
<div class="event-card featured">
```

or insert an extra wrapper:

```html
<div class="title-wrapper">
    <h2 class="title">...</h2>
</div>
```

Identify:

1. Which selectors broke?
2. Why did they break?
3. Which selectors survived?
4. How could you make the brittle selectors less dependent on exact DOM position?

### Checkpoint before moving on

You should be able to write selectors from inspected HTML rather than asking an AI tool to generate selectors without understanding them.

---

# 5. Fetch and Parse HTML with Python

Now connect the earlier concepts:

```text
URL
 ↓
HTTP request
 ↓
HTML response
 ↓
BeautifulSoup
 ↓
selected elements
 ↓
Python values
```

## Concepts to learn

### `requests`

Be comfortable with:

```python
requests.get(...)
response.status_code
response.headers
response.text
response.content
response.url
response.history
response.raise_for_status()
```

And always understand why this matters:

```python
timeout=...
```

### Beautiful Soup

Be comfortable with:

```python
BeautifulSoup(...)
.find(...)
.find_all(...)
.select(...)
.select_one(...)
.get(...)
.get_text(...)
```

Also understand:

- missing elements
- stripping whitespace
- extracting attributes
- repeated records
- relative links vs absolute URLs

## Read

### Requests Quickstart
https://requests.readthedocs.io/en/latest/user/quickstart/

Revisit it now that you are using Requests for extraction.

### Beautiful Soup — Official Documentation
https://www.crummy.com/software/BeautifulSoup/bs4/doc/

Focus on:

- Quick Start
- Navigating the tree
- Searching the tree
- CSS selectors

## Watch

### freeCodeCamp — Web Scraping with Python: Beautiful Soup Crash Course
https://www.youtube.com/watch?v=XVv6mJpFOb0

Recommended portion for Week 1: HTML structure, local files, `find` / `find_all`, browser inspect tools, Requests and website HTML, scraping a real website

---

## Assignment 5A — Local Fixture Parser

**Do this against the saved fictional HTML first or a live website of your choice.**

Implement:

```python
def parse_events(html: str, base_url: str) -> list[dict]:
    ...
```

For every fictional event (in case of saved fictional HTML), extract:

```text
title
item_url
date_raw
speaker_raw
location_raw
raw_text
```

Requirements:

- one dictionary per record
- relative URLs converted to absolute URLs
- missing optional fields represented consistently (`None` or empty list as appropriate)
- surrounding whitespace cleaned
- parser does not crash if one optional field is missing

Or in case of any other live page, fetch the appropriate data.

Save:

```text
assignments/05_parsing/fixture_parser.py
assignments/05_parsing/fixture_output.json
```

### Checkpoint

Delete the speaker from one event in your fixture.

Your parser should still successfully return all events.

---

## Assignment 5B — First Small Real-World Extraction

Only after the local parser works, adapt the same ideas to your institution.

Maximum target: **5–10 records**, either from events or faculty page.

This is intentionally small.

Implement the conceptual separation:

```python
def fetch(url: str) -> str:
    ...

def parse_items(html: str, base_url: str) -> list[dict]:
    ...
```

Requirements:

- explicit timeout
- descriptive `User-Agent`
- meaningful request error handling
- no browser automation
- no attempts to bypass restricted access
- absolute URLs
- only fields actually visible on the selected public surface

Save one response as a local fixture so you can continue development without repeatedly hitting the live site.

Suggested outputs:

```text
assignments/05_parsing/<institution>/
├── scraper.py
├── sample_response.html
├── output.json
└── README.md
```

### Individual focus

In addition to the common requirements:

- **Saanvi / IISER Pune:** pay special attention to date strings and how they could eventually be normalized.
- **Parth / IIT Bombay:** pay special attention to relative vs absolute URLs and canonical item URLs.
- **Mayank / JNU:** identify HTML records vs links whose destination is a PDF or another document type. Do not build PDF extraction yet.
- **Soumyadipta / TISS:** pay special attention to selector robustness when record cards have small structural differences.

If the live site does not exhibit the assigned pattern, reproduce the challenge in a local HTML fixture rather than forcing it onto the site.

### Checkpoint before moving on

You should be able to explain the difference between **fetching** and **parsing** and why they should be separate functions.

---

# 6. Extraction vs Normalization

A monitoring system should not confuse the value displayed on a webpage with the standardized value used downstream.

Example:

```text
Displayed text:
"Sept. 10, 2026 — 6:30 pm"

        ↓ extraction

date_raw:
"Sept. 10, 2026 — 6:30 pm"

        ↓ normalization

event_start:
"2026-09-10T18:30:00+05:30"
```

## Concepts to learn

- raw value vs normalized value
- consistent field names
- optional/null values
- lists vs scalar values
- timestamps
- absolute/canonical URLs
- preserving provenance
- why raw text should often be retained
- why site-specific quirks should not leak into the generic schema

## Common Week 1 schema

Use a shared schema rather than inventing four incompatible outputs.

```json
{
  "source_name": "example_source",
  "source_url": "https://example.org/events",
  "item_url": "https://example.org/events/example-event",
  "item_type": "event",
  "title": "Example Event",
  "event_start": null,
  "event_end": null,
  "location": null,
  "speakers": [],
  "organizations": [],
  "raw_text": "Original extracted text...",
  "fetched_at": "2026-09-01T12:00:00Z",
  "http_status": 200
}
```
or in case of faculties

```json
{
  "source_name": "example_source",
  "source_url": "https://example.org/faculties",
  "item_url": "https://example.org/faculties/faculty-name",
  "item_type": "faculty",
  "name": "Professor name",
  "title": str,
  "bio": str,
  "research_areas": str,
  "fetched_at": "2026-09-01T12:00:00Z",
  "http_status": 200
}
```


For Week 1, prioritize **consistent shape** over perfect extraction of every possible field.

---

## Assignment 6 — Normalization Layer

Refactor your scraper so that parsing and normalization are separate:

```python
def parse_items(html: str, base_url: str) -> list[dict]:
    # Extract values as represented by the source.
    ...

def normalize_item(raw_item: dict) -> dict:
    # Convert raw values into the shared output schema.
    ...
```

Produce:

```text
assignments/06_normalization/<institution>_normalized.jsonl
```

Each output row must conform to the shared schema.

Then document in:

```text
normalization_notes.md
```

At least three assumptions your current parser/normalizer makes, for example:

- assumed timezone
- date format assumption
- missing speaker handling
- URL construction assumption
- title cleanup
- location ambiguity

### Checkpoint before moving on

You should be able to answer:

> If the institution changes how it displays dates tomorrow, which function should ideally change: HTTP fetching, parsing, normalization, or database storage?

---

# 7. Persistence with SQLite

A monitor is more useful when it knows what it has already seen.

## Concepts to learn

- database
- table
- row
- column
- primary key
- unique constraint
- `INSERT`
- `SELECT`
- basic `UPDATE`
- persistence across program runs
- idempotency
- deduplication
- first-seen vs last-seen timestamps
- content hashes at a conceptual level

## Read

### Python `sqlite3` Tutorial
https://docs.python.org/3/library/sqlite3.html

Focus on the tutorial/basic usage. You do not need advanced SQL or database administration this week.

## Suggest a shared table schema

How would you save the data you fetched in an appropriate schema? Make that in your local machine and see if records are getting saved as expected.

The exact production schema can evolve later. The important lesson now is **why** these concepts exist.

---

## Assignment 7 — Store and Deduplicate

Implement:

```python
def init_db():
    ...

def upsert_item(item: dict):
    ...

def get_item(item_url: str):
    ...
```

Run the same local fixture twice.

Expected conceptual result:

```text
RUN 1
8 new records

RUN 2
0 new records
8 already-known records
```

Then modify one event in the fixture and run it again.

Your system should be able to recognize that the item already exists and that its content has changed.

Record the behavior in:

```text
assignments/07_storage/storage_experiment.md
```

Answer:

1. How are duplicates identified?
2. What happens if the same URL appears twice?
3. What would `first_seen_at` mean?
4. What would `last_seen_at` mean?
5. Why might a `content_hash` be useful?
6. Why is "scraping the page again" different from "discovering a new item"?

### Checkpoint before moving on

Running the same input multiple times should **not** blindly create duplicate records.

---
### Peer review

- **Saanvi ↔ Parth**
- **Mayank ↔ Soumyadipta**

Each reviewer should provide at least three substantive comments addressing things such as:

- readability
- separation of responsibilities
- selector brittleness
- error handling
- missing values
- repeated execution
- access/politeness behavior
- tests
- README clarity

### Checkpoint before moving on

You should be able to add a fifth simple HTML source primarily by creating a new source/parser module rather than rewriting the HTTP, storage, and logging layers.

---

# Week 1 Definition of Done

Week 1 is **not** complete because all tutorials were watched.

Every intern should be able to take a relatively simple, unfamiliar public HTML listing and independently work through:

```text
1. Check the relevant public surface and access considerations
2. Understand the HTTP response
3. Inspect the HTML/DOM
4. Identify the repeated record container
5. Write reasonable selectors
6. Fetch with Requests
7. Parse with Beautiful Soup
8. Separate parsing from normalization
9. Produce the common schema
10. Persist records in SQLite
11. Avoid duplicate records on rerun
12. Explain what assumptions could break
```

A useful final test is to give each intern a simple HTML event/news page they have **never seen before** and ask them to perform the above process without copying an existing site parser.

---

# What Is Explicitly Out of Scope for Week 1

Do **not** spend Week 1 on:

- CAPTCHA bypasses
- proxy rotation
- anti-bot evasion
- authenticated/private surfaces
- distributed crawling

Those may become relevant later. Week 1 should create a strong enough foundation that future complexity is added deliberately rather than used to compensate for weak fundamentals.

---

# Compact Resource List

Use this as a reference after completing the curriculum in order.

### HTTP
- MDN — Overview of HTTP  
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview
- Requests — Quickstart  
  https://requests.readthedocs.io/en/latest/user/quickstart/
- Traversy Media — HTTP Crash Course  
  https://www.youtube.com/watch?v=iYM2zFP3Zn0

### Crawling boundaries
- Google — Introduction to `robots.txt`  
  https://developers.google.com/search/docs/crawling-indexing/robots/intro
- Google — Crawling and Indexing  
  https://developers.google.com/search/docs/crawling-indexing

### HTML / DOM / selectors
- MDN — DOM Introduction  
  https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction
- MDN — Basic HTML Syntax  
  https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content/Basic_HTML_syntax
- MDN — CSS Selectors  
  https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Selectors
- MDN — Selectors and Combinators  
  https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Selectors/Selectors_and_combinators
- MDN — XPath  
  https://developer.mozilla.org/en-US/docs/Web/XML/XPath
- Traversy Media — DOM Crash Course  
  https://www.youtube.com/watch?v=0ik6X4DJKCc

### Parsing
- Beautiful Soup — Official Documentation  
  https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- freeCodeCamp — Beautiful Soup Crash Course  
  https://www.youtube.com/watch?v=XVv6mJpFOb0

### Storage / tests / logging
- Python — `sqlite3`  
  https://docs.python.org/3/library/sqlite3.html
- pytest — Getting Started  
  https://docs.pytest.org/en/stable/getting-started.html
- Python — Logging HOWTO  
  https://docs.python.org/3/howto/logging.html

### Scheduling
- APScheduler — Documentation  
  https://apscheduler.readthedocs.io/
