# Discovery Inspection Findings — Feeds, Sitemaps & Central Listings

**Author:** Mayank (SSRISS Intern)  
**Target:** Jawaharlal Nehru University (`jnu.ac.in`) & Academic Aggregators  
**Date:** October 2026  

---

## 1. Surface Inspection Results for Target Institution

An automated reconnaissance of public endpoints on `www.jnu.ac.in` was conducted to determine the availability and utility of standard syndication and discovery mechanisms:

| Discovery Mechanism | Endpoint Tested | Status on Live Target | Usability for Monitoring |
|---|---|---|---|
| **RSS 2.0 Feed** | `https://www.jnu.ac.in/rss.xml`<br>`https://www.jnu.ac.in/feed` | **404 Not Found** (Drupal RSS feed view disabled for anonymous users) | Unusable on live JNU without local fixture adapter |
| **Atom Feed** | `https://www.jnu.ac.in/atom.xml` | **404 Not Found** | Unusable on live JNU |
| **XML Sitemap** | `https://www.jnu.ac.in/sitemap.xml` | **Exposed** (Drupal XMLSitemap module), but lists static institutional nodes; updates lag live events | Low freshness for high-cadence event alerts |
| **HTML Central Listing** | `https://www.jnu.ac.in/jnuevents`<br>`https://www.jnu.ac.in/events-archive` | **200 OK** (Active, server-rendered Drupal View) | **Highest yield**, real-time updates, rich tabular metadata |

Because JNU does not expose a live, dedicated RSS feed for events, we implemented:
1. Direct HTML central listing discovery from `https://www.jnu.ac.in/jnuevents`, and
2. Technical parsers for RSS 2.0 and XML Sitemaps backed by local fixtures (`sample_feed.xml`, `sample_sitemap.xml`, `sample_sitemap_index.xml`) to complete the architectural exercises.

---

## 2. Sample Output from Discovery Inspectors

### 2.1 Feed Discovery Inspector (`inspect_feed.py`)
```text
=== Feed Discovery Inspection: fixtures/sample_feed.xml ===

Item #1:
  URL: https://www.jnu.ac.in/node/159898390
  title: SCIS organises a lecture by Dr. Divya P. Kumar
  published/updated: Tue, 29 Sep 2026 12:00:00 +0530
  discovery source: rss_feed

Item #2:
  URL: https://www.jnu.ac.in/node/159898442
  title: SCIS organises a lecture by Prof. D. S. Hooda
  published/updated: Wed, 30 Sep 2026 12:00:00 +0530
  discovery source: rss_feed
```

### 2.2 Sitemap Discovery Inspector (`inspect_sitemap.py`)
```text
=== XML Sitemap Inspection: fixtures/sample_sitemap.xml ===

Item #1:
  URL: https://www.jnu.ac.in/jnuevents
  title: None
  published/updated/lastmod: 2026-09-28T09:30:00Z
  discovery source: xml_sitemap

Item #2:
  URL: https://www.jnu.ac.in/node/159898390
  title: None
  published/updated/lastmod: 2026-09-29T12:00:00Z
  discovery source: xml_sitemap
```

---

## 3. Crucial Conceptual Distinctions

### 3.1 Discovering a URL vs. Extracting a Complete Event Record

A fundamental design flaw in naive scrapers is conflating **Discovery** with **Extraction**. They are two distinct pipeline stages with distinct operational responsibilities:

```text
+-------------------------------------------------------------+
| DISCOVERY STAGE                                             |
| Purpose: Frontier identification & change candidate triage  |
| Input:   Listing HTML, RSS feed, or XML sitemap             |
| Output:  Candidate URL + temporal hint (lastmod / pubDate)  |
| Cost:    1 HTTP GET request discovers 20-50 candidate URLs  |
+-------------------------------------------------------------+
                              |
                              v  (Scope Filter & Hash Check)
+-------------------------------------------------------------+
| EXTRACTION STAGE                                            |
| Purpose: Deep semantic entity & event representation        |
| Input:   Specific canonical event page (/node/<id>)         |
| Output:  Full record: Title, Datetimes, Venue, Abstract,    |
|          Speakers, Chairs, Sponsoring Schools, Links        |
| Cost:    1 HTTP GET request per new/changed item            |
+-------------------------------------------------------------+
```

1. **Information Completeness:**
   - A discovered URL merely informs the system that a potential entity exists at `https://www.jnu.ac.in/node/159898390`. A sitemap does not provide the speaker's name, chair, or talk abstract.
   - An extracted event record contains the fully normalized, verified payload with relational entity links.
2. **Efficiency & Politeness:**
   - Separating discovery allows the monitor to check 50 items in seconds. If 48 have unchanged content hashes or old `lastmod` timestamps, detail fetching is bypassed entirely.
   - Crawling detail pages without prior discovery triage results in 50 wasteful HTTP requests per run.

### 3.2 Protocol-Agnostic Downstream Invariant

The downstream pipeline (scope filtering, deduplication, content hashing, database upsertion, entity relation mapping) must be completely decoupled from the upstream discovery transport. Whether a candidate item URL originates from:
- an HTML card listing,
- an RSS 2.0 or Atom feed, or
- an XML sitemap / sitemap index,

the discovery layer emits the identical unified shape:
```json
{
  "source_name": "jnu_events",
  "discovered_url": "https://www.jnu.ac.in/node/159898390",
  "discovery_method": "html_listing",
  "discovered_title": "SCIS organises a lecture by Dr. Divya P. Kumar",
  "source_timestamp": "2026-09-29T12:00:00Z",
  "discovered_at": "2026-10-19T15:45:00Z"
}
```
This decoupling ensures that if JNU enables an RSS feed tomorrow or changes their CMS from Drupal to another platform, zero downstream extraction or storage code requires modification.
