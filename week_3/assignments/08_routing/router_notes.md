# Multi-Content Central Aggregators — Content Router Notes

**Author:** Mayank (SSRISS Intern)  
**Target:** Central Multi-Content Surface Routing (JNU)  
**Assignment:** Assignment 8 — Content Router  
**Date:** October 2026  

---

## 1. Multi-Content Aggregators in Academic Institutions

A central university portal rarely exposes only clean academic events. The main landing pages and views contain a heterogeneous mix of records:
- Academic lectures, seminars, and conferences (`event`)
- Administrative circulars, tenders, and notices (`announcement`)
- Faculty profile directories (`faculty`)
- Downloadable PDF documents, ordinances, and forms (`pdf_document`)
- External registration links (Google Forms, ConfBay, IEEE) (`external_link`)
- Uncategorized utilities, feedback forms, and microsites (`unknown`)

---

## 2. Structural Evidence Routing vs. Topic Interpretation

The content router enforces a strict architectural boundary: **Routing decisions are derived entirely from deterministic structural evidence, never topic or ideological interpretation.**

### 2.1 Permissible Structural Signals
1. **Network Location:** URLs whose hostname does not contain `jnu.ac.in` are immediately classified as `external_link`.
2. **Resource Signatures:** URLs ending in `.pdf` or tagged with MIME type `application/pdf` are classified as `pdf_document`.
3. **URL Hierarchy:** Canonical paths like `/jnuevents`, `/notices`, and `/faculty` explicitly map to `event`, `announcement`, and `faculty`.
4. **CMS Structural Tags:** Drupal view categories or taxonomy tags (`section="notices"`, `section="events"`).

### 2.2 Prohibited Narrative Heuristics
The router does not perform sentiment analysis or keyword searches on socio-political topics to guess document types. For example, a notice discussing "National Security Policy" is classified as an `announcement` if it originates from `/notices`, and an `event` if it is a scheduled lecture in `/jnuevents`. The subject matter never dictates the data structure.

---

## 3. Checkpoint: Preserving Unknowns vs. Schema Coercion

A dangerous antipattern in scrapers is schema coercion: when encountering an unfamiliar record, forcing it into the default `event` model by populating empty dates or dummy titles.

Our architecture enforces the following invariant:
- Items that do not structurally match a supported content parser are classified as `unknown`.
- Their `DiscoveryRecord` is fully logged and stored in the discovery table.
- Detail parsing is safely bypassed, avoiding parser crashes and preventing database pollution with synthetic event records.
- System administrators can monitor the count of `unknown` items; if the count spikes, it indicates that the university has launched a new section (e.g., `/podcasts/` or `/press-releases/`) warranting a new dedicated adapter.
