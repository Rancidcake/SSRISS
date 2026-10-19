# URL Scope Filter — Test Cases & Frontier Boundary Rules

**Author:** Mayank (SSRISS Intern)  
**Target:** Jawaharlal Nehru University (`www.jnu.ac.in`)  
**Configuration Evaluated:**
```json
{
  "allowed_hostname": "www.jnu.ac.in",
  "allowed_path_prefixes": ["/node", "/jnuevents", "/events-archive", "/notices"],
  "excluded_path_prefixes": [
    "/user", "/admin", "/login", "/search", "/filter", "/calendar",
    "/sites/default/files"
  ],
  "allow_external": false,
  "strip_all_query_params": false,
  "ignored_query_params": [
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source"
  ]
}
```

---

## 1. Concrete Scope Test Cases

### Case 1: Valid Event Detail
- **URL:** `https://www.jnu.ac.in/node/159898390`
- **Allowed?:** **YES**
- **Why?:** Matches allowed hostname `www.jnu.ac.in`, matches allowed path prefix `/node/`, is not a binary file, and contains no excluded keywords.

### Case 2: Valid News / Notices Detail
- **URL:** `https://www.jnu.ac.in/notices/annual-report-2026`
- **Allowed?:** **YES**
- **Why?:** Hostname matches target, path starts with allowed prefix `/notices`, no excluded segments present.

### Case 3: External Registration Site (e.g. Google Forms / NetCrypt)
- **URL:** `https://docs.google.com/forms/d/1XKf3OSvnc02rfU7tu8Zl1Mv3vuPtOg2s7G3gvWmjY3Y/edit`
- **Allowed?:** **NO**
- **Why?:** Hostname (`docs.google.com`) is off-domain and `allow_external` is set to `false`. External registration forms are extracted into item metadata (`registration_url`) by the detail parser, but must never enter the crawl frontier.

### Case 4: Social Media Link
- **URL:** `https://twitter.com/JNU_Official_New/status/18392019482`
- **Allowed?:** **NO**
- **Why?:** Off-domain host (`twitter.com`). Disallowed by hostname boundary filter.

### Case 5: Direct PDF Download
- **URL:** `https://www.jnu.ac.in/sites/default/files/notices/circular_oct_2026.pdf`
- **Allowed?:** **NO**
- **Why?:** Matches excluded path prefix `/sites/default/files` and ends with banned binary extension `.pdf`. Binary files are handled as linked resources, not parsed HTML frontier items.

### Case 6: Administrative Login URL
- **URL:** `https://www.jnu.ac.in/user/login`
- **Allowed?:** **NO**
- **Why?:** Matches excluded path prefix `/user/` (and `/login`). Crawlers must never request authentication or administration pages.

### Case 7: Search Query URL
- **URL:** `https://www.jnu.ac.in/search/node?keys=cryptology`
- **Allowed?:** **NO**
- **Why?:** Matches excluded prefix `/search/`. Search results pages generate dynamic, unbounded keyword spaces that lead to crawl explosions.

### Case 8: Duplicate URL with Fragment Anchor
- **URL:** `https://www.jnu.ac.in/node/159898390#speaker-bio`
- **Allowed?:** **YES (Canonicalized)**
- **Why?:** The URL is valid, but the fragment `#speaker-bio` is stripped during canonicalization to `https://www.jnu.ac.in/node/159898390`. If the canonical URL was already seen, the frontier filter rejects it as duplicate.

### Case 9: Same Page with Marketing / Tracking Query Parameters
- **URL:** `https://www.jnu.ac.in/node/159898390?utm_source=twitter&utm_medium=social&fbclid=IwAR29...`
- **Allowed?:** **YES (Canonicalized)**
- **Why?:** The filter strips tracking keys (`utm_*`, `fbclid`), yielding the canonical URL `https://www.jnu.ac.in/node/159898390`. This prevents artificial duplication in the database.

### Case 10: Infinite Calendar Loop URL
- **URL:** `https://www.jnu.ac.in/jnuevents?month=11&year=2028`
- **Allowed?:** **NO**
- **Why?:** Query string contains `month=` and `year=`, matching calendar pagination trap rules.

---

## 2. Checkpoint: Why Aggregators Must Not Blindly Follow Links

Central aggregators and university homepages feature dense hyperlinking across diverse systems (CMS navigation, footers, social widgets, archives, registration gateways). Blindly following all links leads directly to:

1. **Crawl Frontier Explosion & Infinite Traps:**
   - Navigating calendar controls (`?month=12&year=2030`) creates an infinite space of empty or duplicate pages.
2. **Denial of Service / Unintended State Mutation:**
   - Following logout, administrative, or registration URLs can log out monitoring sessions or submit malformed inquiries to webmasters.
3. **Wasted Bandwidth on Non-HTML Binaries:**
   - University listings feature thousands of PDF circulars, PowerPoint slides, and zip archives. Loading these into an HTML parser causes crashes and wastes bandwidth.
4. **Context Drift:**
   - Clicking external partner links (e.g., IEEE, Springer, Twitter) transitions the scraper from monitoring university announcements into crawling commercial publishers or social media platforms.
