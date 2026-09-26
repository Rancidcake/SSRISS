# Assignment 02 — Surface Reconnaissance: Jawaharlal Nehru University (JNU)

**Target Institution:** Jawaharlal Nehru University  
**Main Domain:** `https://www.jnu.ac.in`  
**OSINT Engineer:** Senior Technical Auditor  

---

## A. Domain and Access Boundaries

### 1. Main Domain & Subdomains
- **Primary Domain:** `https://www.jnu.ac.in` (Drupal 10 CMS)
- **Subdomains Identified:**
  - `admissions.jnu.ac.in` (NTA / Admission Portal)
  - `jnu.ac.in/content/notices` (Legacy Notice Redirect Path)
  - `junee.jnu.ac.in` (Entrance Examination Portal)

### 2. `robots.txt` Evaluation
- **URL:** `https://www.jnu.ac.in/robots.txt`
- **Key Disallow Rules:**
  ```text
  Disallow: /core/
  Disallow: /profiles/
  Disallow: /admin/
  Disallow: /user/register
  Disallow: /user/password
  Disallow: /user/login
  Disallow: /user/logout
  ```
- **Allow Rules / Public Surfaces:** Public listing paths like `/notices`, `/events`, and `/news` are **not** restricted.
- **Politeness Guidance:** Moderate polling interval (e.g. 5–15 minutes), explicit User-Agent header, timeout enforceability.

### 3. Sitemap & RSS/Atom Availability
- **Sitemap:** `https://www.jnu.ac.in/sitemap.xml` returned HTTP `404 Not Found`. No explicit sitemap index header detected.
- **RSS/Atom Feeds:** RSS endpoints (`/rss.xml` / `/feed`) are disabled on the Drupal deployment.
- **Conclusion:** Structured HTML page extraction on `/notices` is the most direct, reliable, and appropriate public surface for monitoring.

---

## B. Relevant Public Content Surfaces

### Surface Candidate 1: JNU Official Notices & Circulars (Primary Target)
- **URL:** `https://www.jnu.ac.in/notices`
- **Surface Type:** Server-Rendered HTML Listing Table
- **What it Contains:** Academic circulars, registration schedules, exam notices, course add/drop announcements, administrative updates.
- **Listing Page vs Detail Page:** Server-rendered single listing table with direct links to attached `.pdf` notices or internal detail pages.
- **HTML / PDF / Other:** Mixed HTML listing table pointing directly to `.pdf` circular downloads (`/sites/default/files/inline-files/...pdf`) and `.html` notice pages.
- **Pagination:** Single high-yield table rendering 50+ active recent items.
- **Approximate Number of Useful Records Visible:** ~50–100 records per snapshot.
- **Monitoring Assessment:** **EXCELLENT**. High update frequency, structured table layout (`<tr>` / `<td>`), clean metadata fields (Sl No, Title, Date, Download URL).

### Surface Candidate 2: JNU Events & Seminars
- **URL:** `https://www.jnu.ac.in/events`
- **Surface Type:** HTML Cards / Grid View
- **What it Contains:** Conferences, guest lectures, department seminars, cultural workshops.
- **Listing Page vs Detail Page:** Card listing with thumbnail previews linking to event details.
- **HTML / PDF / Other:** HTML markup with embedded images and event detail links.
- **Pagination:** Paginated Drupal view (`?page=0`, `?page=1`).
- **Approximate Number of Useful Records Visible:** ~10–15 records per page.
- **Monitoring Assessment:** **MODERATE**. Lower update frequency compared to academic notices, non-standard layout variations across event types.

### Surface Candidate 3: JNU News & Press Releases
- **URL:** `https://www.jnu.ac.in/news`
- **Surface Type:** List View
- **What it Contains:** Institutional press releases, achievements, official statements.
- **Listing Page vs Detail Page:** Headline summary list leading to detail news posts.
- **HTML / PDF / Other:** HTML detail pages with optional press PDF attachments.
- **Pagination:** Paginated list view.
- **Approximate Number of Useful Records Visible:** ~15 records per page.
- **Monitoring Assessment:** **SECONDARY**. Informational focus; lower urgency for academic compliance monitoring compared to notice circulars.

---

## C. Primary Target Surface Recommendation

**Selected Surface:** **JNU Main Notices Page** (`https://www.jnu.ac.in/notices`)

### Detailed Justification:

1. **Utility & Timeliness:** The notices surface is the single source of truth for time-sensitive academic announcements (registration dates, fee submission deadlines, circulars).
2. **Efficiency vs Whole-Site Crawling:** Monitoring `/notices` yields 100% of official university announcements in a single HTTP request (~98 KB payload), eliminating unnecessary crawling of static pages across the domain.
3. **Architecture:** Server-rendered HTML Drupal table (`<table class="views-table">`). No client-side JavaScript rendering (React/Angular) required, permitting execution via standard Python HTTP `requests` + `BeautifulSoup`.
4. **Access & Politeness:** Fully public, compliant with `robots.txt`, zero authentication or rate-limit friction under standard polling.
5. **Extractable Fields:**
   - Notice Title (`title`)
   - Notice Date (`date_raw`)
   - Download Link (`item_url`)
   - Classification (`pdf_notice` vs `html_notice`)
   - Serial Number (`sl_no`)
