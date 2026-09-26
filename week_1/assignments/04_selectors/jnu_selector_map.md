# Assignment 04 — Selector Workbook: JNU & Fixture Selector Map

This document provides both CSS selectors and XPath expressions for extracting notice records from `fixture.html` and JNU's live notices page (`https://www.jnu.ac.in/notices`).

---

## 1. Fixture Selector Table (`fixture.html`)

| Field | CSS Selector | XPath Expression |
|---|---|---|
| **Record Container** | `div.notice-card` | `//div[contains(@class, "notice-card")]` |
| **Title** | `h2.notice-title > a` | `.//h2[contains(@class, "notice-title")]/a` |
| **URL** | `h2.notice-title > a[href]` | `.//h2[contains(@class, "notice-title")]/a/@href` |
| **Date** | `time.notice-date` | `.//time[contains(@class, "notice-date")]/text()` |
| **Speaker** | `span.speaker-name` | `.//span[contains(@class, "speaker-name")]/text()` |
| **Location** | `span.location-name` | `.//span[contains(@class, "location-name")]/text()` |

*Note for relative evaluation: Title, URL, Date, Speaker, and Location XPath expressions use relative pathing `.//` rooted inside the evaluated Record Container node.*

---

## 2. Real Target Selector Table (JNU Live Notices Page)

| Field | CSS Selector | XPath Expression |
|---|---|---|
| **Record Container** | `table.views-table tbody tr`, `table tbody tr` | `//table//tbody//tr` |
| **Title** | `td:nth-child(2)` | `.//td[2]/text()` |
| **URL** | `td:nth-child(4) a[href]`, `td a[href]` | `.//td[4]//a/@href` or `.//td//a/@href` |
| **Date** | `td:nth-child(3)` | `.//td[3]/text()` |
| **Speaker** | *Not available on listing page.* | *Not available on listing page.* |
| **Location** | *Not available on listing page.* | *Not available on listing page.* |

> [!NOTE]
> Fields marked as *"Not available on listing page"* are not present in the HTML listing table at `https://www.jnu.ac.in/notices`. Retaining these as `None` in raw extracted dictionaries preserves schema consistency without introducing synthetic assumptions.

---

## 3. Robustness Challenge Analysis

To test selector resilience, suppose the fixture DOM undergoes structural updates:

### Mutation Scenario A: Class Name Augmentation
- **Original markup:** `<div class="notice-card">`
- **Mutated markup:** `<div class="notice-card featured urgent">`

| Selector | Status | Rationale |
|---|---|---|
| `div[class="notice-card"]` | **BROKE** | Exact attribute match fails because additional class names exist. |
| `div.notice-card` | **SURVIVED** | CSS class membership checks whether `.notice-card` is present in the token list. |
| `//div[@class="notice-card"]` | **BROKE** | Exact string equality fails in XPath. |
| `//div[contains(@class, "notice-card")]` | **SURVIVED** | Substring search matches regardless of additional classes. |

### Mutation Scenario B: Structural Wrapper Insertion
- **Original markup:** `<h2 class="notice-title"><a href="...">Title</a></h2>`
- **Mutated markup:** `<div class="title-header-wrapper"><h2 class="notice-title"><a href="...">Title</a></h2></div>`

| Selector | Status | Rationale |
|---|---|---|
| `.notice-card > h2 > a` | **SURVIVED** | Direct parent-child chain remains intact between card, h2, and link. |
| `#notices-container > div > h2 > a` | **BROKE** | Hardcoded positional path broke due to inserted wrapper `div`. |
| `.notice-card .notice-link` | **SURVIVED** | Descendant combinator matches link regardless of intermediate div depth. |
| `//div[@id="notices-container"]/div/h2/a` | **BROKE** | Absolute child axis `/` requires exact depth. |
| `//div[contains(@class, "notice-card")]//a[contains(@class, "notice-link")]` | **SURVIVED** | Relative descendant axis `//` bypasses intermediate node changes. |

### Key Takeaways for Resilient Selectors:
1. **Prefer semantic class names over positional paths**: Use `.notice-card .notice-link` instead of `div > div:nth-child(2) > a`.
2. **Use descendant combinators**: Prefer space in CSS (`.container .target`) or `//` in XPath over strict child operators (`>`) when structural wrappers may be introduced.
3. **Use class containment in XPath**: Always use `[contains(@class, "...")]` rather than exact string equality `[@class="..."]`.
