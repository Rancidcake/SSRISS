# Aggregator Candidate Matrix — Jawaharlal Nehru University (JNU)

**Author:** Mayank (SSRISS Intern)  
**Primary Institution:** Jawaharlal Nehru University (JNU), New Delhi  
**Assignment:** Week 3 — Central Aggregators, Discovery & Entity Extraction  
**Date:** October 2026  

---

## 1. Candidate Surfaces Evaluated

### Candidate 1: JNU Central Events & Seminars Portal (Best Target)

- **Name:** JNU Central Events Listing & Research Archive
- **URL:** `https://www.jnu.ac.in/jnuevents` (Current) & `https://www.jnu.ac.in/events-archive` (Historical Archive)
- **Institution/organization:** Jawaharlal Nehru University (JNU)
- **Surface type:** Central university-wide academic event listing and archive
- **HTML / RSS / Atom / sitemap / other:** HTML (Drupal 9/10 `view-id-jnu_events` table)
- **Content types:** Conferences, memorial lectures, symposiums, research seminars, workshops, book launches, endowment lectures
- **Approximate update frequency:** 3–8 new events per week during active semesters; ~15 active listings on current page, ~1,200+ historical records across ~41 archive pages
- **Departments/units represented:** University-wide aggregator covering all schools and special centres, including:
  - School of Computational and Integrative Sciences (SCIS)
  - School of Computer & Systems Sciences (SCSS)
  - School of International Studies (SIS)
  - School of Sanskrit and Indic Studies (SSIS)
  - School of Physical Sciences (SPS)
  - School of Social Sciences (SSS)
  - School of Environmental Sciences (SES)
  - Centre for Historical Studies (CHS)
  - Centre for the Study of Law and Governance (CSLG)
- **Detail-page links?:** Yes, every event entry links to a dedicated canonical node page (`/node/<id>`) containing detailed abstracts, schedules, venues, and registration forms.
- **Pagination/archive?:** Yes; current page presents active events while `/events-archive` provides a standard Drupal pager (`?page=0, 1, 2...`) with 30 items per page.
- **Speaker information?:** Highly explicit in titles and detail bodies (e.g., "lecture by Dr. Divya P. Kumar", "address by Prof. D. S. Hooda", keynote speaker affiliations).
- **Organization information?:** Highly explicit in titles and abstracts (e.g., "SCIS organises...", "SCSS in collaboration with IEEE", "CIPOD, SIS").
- **Access considerations:** Public HTML, no authentication required, no anti-bot CAPTCHAs, predictable HTML structure rendered by server-side Drupal views.
- **Why this is high-yield or low-yield:** **High-yield.** A single GET request to `/jnuevents` surfaces events from dozens of independent university schools, academic departments, and autonomous research centres. Detail pages are rich with speaker, venue, and organizational relations.

---

### Candidate 2: JNU Central Notices, Circulars & Announcements (Backup Target)

- **Name:** JNU Central Notices & Circulars
- **URL:** `https://www.jnu.ac.in/notices`
- **Institution/organization:** Jawaharlal Nehru University (JNU)
- **Surface type:** Central administrative notice board & university announcements
- **HTML / RSS / Atom / sitemap / other:** HTML (Drupal `view-id-notices` table)
- **Content types:** Administrative circulars, tenders, admission notifications, academic council announcements, public advisories
- **Approximate update frequency:** 15–25 notices per week; ~50 items per page across ~4 active pages
- **Departments/units represented:** Central Administration, Registrar, Academic Council, Dean of Students, Finance Branch, Engineering Department, Evaluation Branch
- **Detail-page links?:** Limited. Most rows link directly to uploaded PDF files (`/sites/default/files/...`) or shared landing pages (e.g., `/convocation`).
- **Pagination/archive?:** Yes, standard Drupal pager (`?page=1`, `?page=2`, etc.) with bounded depth.
- **Speaker information?:** Absent or minimal; notices announce administrative decisions rather than scholarly lectures with speakers.
- **Organization information?:** Good institutional coverage (Registrar, Central Administration, Schools), but predominantly administrative rather than academic.
- **Access considerations:** Public HTML, reliable server uptime, large PDF payloads if following document links.
- **Why this is high-yield or low-yield:** **Medium-yield.** Highly valuable for institutional monitoring and administrative governance tracking, but low-yield for speaker/academic entity extraction because notice content resides inside binary PDFs rather than structured semantic HTML.

---

### Candidate 3: Single School / Faculty Profile Page (Not Recommended)

- **Name:** School of Computational and Integrative Sciences (SCIS) Faculty Listing
- **URL:** `https://www.jnu.ac.in/scis/faculty`
- **Institution/organization:** Jawaharlal Nehru University (SCIS)
- **Surface type:** Department-specific faculty directory
- **HTML / RSS / Atom / sitemap / other:** HTML
- **Content types:** Static faculty profile entries (name, designation, research interest, email)
- **Approximate update frequency:** Very low (updated once or twice a year upon faculty onboarding/promotions)
- **Departments/units represented:** Exclusively SCIS (single unit)
- **Detail-page links?:** Profile sub-pages (`/faculty/xyz`) or mailto links
- **Pagination/archive?:** None (single static listing)
- **Speaker information?:** Faculty names only; zero event context, no talk titles, no temporal metadata
- **Organization information?:** Monolithic (only SCIS)
- **Access considerations:** Public HTML, low bandwidth
- **Why this is high-yield or low-yield:** **Low-yield.** Monitoring this surface yields zero new event discoveries over months. Crawling ten or twenty such departmental faculty pages produces high network churn with virtually zero temporal signal or event metadata.

---

## 2. Aggregator Candidate Ranking

```text
1. Best target:      JNU Central Events & Seminars Portal (https://www.jnu.ac.in/jnuevents)
2. Backup target:    JNU Central Notices & Circulars (https://www.jnu.ac.in/notices)
3. Not recommended: Single School / Faculty Directory (https://www.jnu.ac.in/scis/faculty)
```

### Rationale for Ranking

1. **JNU Central Events (`/jnuevents` + `/events-archive`)** is the uncontested best target because it satisfies every requirement of the Week 3 entity monitoring specification. It aggregates seminars, lectures, and conferences from all 13 Schools and 55+ Centres of JNU into a unified semantic table. The listing explicitly names organizing departments and speakers in predictable grammatical constructs ("SCIS organises a lecture by Dr. Divya P. Kumar"), and provides structured detail pages with datetime timestamps, venues, abstracts, and registration URLs.
2. **JNU Central Notices (`/notices`)** serves as a dependable backup for volume monitoring and freshness tracking, but is secondary for Week 3 because circulars are primarily administrative documents pointing to static PDF attachments rather than structured HTML detail pages with speakers and chairs.
3. **Faculty Directory Pages** are explicitly not recommended for a temporal monitoring system. They lack discovery depth, do not reflect real-time campus activity, and crawling dozens of individual school pages would violate the core architectural goal of high-yield central aggregation.

---

## 3. Checkpoint Justification: Why One Central Aggregator Beats Ten Isolated Crawls

A naive web monitoring pipeline attempts to achieve coverage by crawling deeper: locating individual faculty homepages, departmental notice boards, and student club portals. This approach suffers from acute architectural pathologies:

1. **Information Yield per HTTP Request:**
   - A single GET request to `https://www.jnu.ac.in/jnuevents` discovers 15–30 academic events across SCIS, SCSS, SIS, SSIS, and SSS simultaneously.
   - Crawling 10 isolated department homepages requires at least 10–20 HTTP requests, 80% of which return zero new events due to stale local maintenance.
2. **Maintenance Surface & Fragility:**
   - University departments frequently redesign individual microsites with arbitrary CMS frameworks (WordPress, Joomla, hand-coded PHP). Maintaining scrapers for 10 distinct departmental layouts requires 10 distinct CSS selector maps.
   - A central aggregator is maintained by university central IT under a standardized CMS template (Drupal Views), meaning a single robust adapter maintains high coverage across all campus units.
3. **Bounded Scope & Frontier Safety:**
   - Departmental websites frequently link outwards to faculty personal blogs, external Google Drive folders, or infinite calendar archives, risking crawler traps.
   - Central aggregators expose clean, bounded pagination parameters (`?page=N`) with consistent canonical URLs (`/node/<id>`).
4. **Entity Linkage & Graph Value:**
   - Central listings expose inter-departmental collaborations (e.g., SCIS co-organizing with SPS) in a single unified schema, allowing our entity extraction engine to construct meaningful many-to-many relationship graphs without cross-domain identity reconciliation problems.
