# Conservative Normalization & Entity Matching Policy

**Author:** Mayank (SSRISS Intern)  
**Target:** Entity Resolution Policy (People & Organizations)  
**Assignment:** Assignment 7 — Entity Matching Exercise  
**Date:** October 2026  

---

## 1. Concrete Matching Decisions on Assignment Benchmark Pairs

| Entity Type | Entity A | Entity B | Match Decision | Detailed Technical Rationale |
|---|---|---|---|---|
| **Person** | `Prof. Ananya Rao` | `Ananya Rao` | **safe automatic match** | Identical token sequence (`ananya rao`) after stripping standard academic honorific (`Prof.`) and normalizing whitespace and punctuation. |
| **Person** | `Prof Ananya Rao` | `Ananya Rao` | **safe automatic match** | Identical token sequence; unpunctuated honorific prefix cleanly removed. |
| **Person** | `A. Rao` | `Ananya Rao` | **possible match requiring review** | Single initial matching first character with shared surname. Extremely common in academic citations; high risk of merging different scholars (e.g., Arvind Rao, Ashok Rao, Ananya Rao). |
| **Person** | `Ananya R.` | `Ananya Rao` | **possible match requiring review** | Shared first name with truncated surname initial. Could be Ananya Roy, Ananya Ray, or Ananya Rao. Must be routed to human review. |
| **Person** | `Dr. Arvind Sharma` | `Dr. Anand Sharma` | **do not match automatically** | Distinct first names despite identical title and surname. Completely separate individuals. |
| **Person** | `Prof. D. S. Hooda` | `D.S. Hooda` | **safe automatic match** | Identical initial sequence (`d s`) and surname (`hooda`) once dots, honorifics, and whitespace are normalized. |
| **Organization** | `Centre for Policy Research` | `Center for Policy Research` | **safe automatic match** | Predictable British vs American dialectical spelling variation (`centre` vs `center`); denotes the identical institution. |
| **Organization** | `Centre for Policy Research` | `Centre for Policy Research (CPR)` | **safe automatic match** | The parenthetical acronym `(CPR)` exactly matches the computed initialism of `Centre for Policy Research`. Verified expansion. |
| **Organization** | `CPR` | `Centre for Policy Research` | **possible match requiring review** | Standalone 3-letter acronym is polysemic. Could refer to CPR India, Cardiopulmonary Resuscitation, Canadian Pacific Railway, or Center for Progressive Reform. Cannot safely link without contextual grounding. |
| **Organization** | `School of Computer and Systems Sciences` | `School of Computational and Integrative Sciences` | **do not match automatically** | Distinct university schools within JNU (SCSS vs SCIS), despite linguistic and structural similarity. |

---

## 2. Fundamental Policy Rule: Favor False Splits over False Merges

A foundational axiom of semantic graphs and academic monitoring systems is:

> **A False Split is an inconvenience; a False Merge is catastrophic corruption.**

### 2.1 The Asymmetry of Errors

1. **False Split (Two entities representing the same real-world person):**
   - *Scenario:* `Ananya Rao` and `A. Rao` exist as two separate rows in the `people` table.
   - *Impact:* An event search for `Ananya Rao` misses an event listed under `A. Rao`.
   - *Recovery:* A human reviewer or a high-confidence co-authorship algorithm can trivially merge two distinct entity IDs at any time using a lightweight database alias or merge operation:
     ```sql
     UPDATE item_people SET person_id = 1 WHERE person_id = 2;
     DELETE FROM people WHERE id = 2;
     ```
2. **False Merge (Two distinct real-world people collapsed into one entity ID):**
   - *Scenario:* A fuzzy matcher collapses `Arvind Rao` and `Ananya Rao` into the same person record because both were written as `A. Rao`.
   - *Impact:* The database claims that Ananya Rao published research in two completely unrelated fields (e.g., Cryptology and Sanskrit Literature) and served on contradictory committees. All downstream analytics, collaboration networks, and institutional briefings become corrupted.
   - *Recovery:* Unraveling a false merge requires painstakingly inspecting every historical event row, locating the original HTML snapshots, and manually teasing apart hundreds of interconnected join records.

### 2.2 Week 3 Resolution Heuristics

1. **Permissible Safe Transformations:**
   - Stripping surrounding whitespace and collapsing multiple spaces.
   - Case-insensitive folding (`SCIS` -> `scis`).
   - Removing recognized honorific prefixes (`Prof.`, `Dr.`, `Amb.`, `Shri`, `Smt.`, `Mr.`, `Ms.`).
   - Normalizing dialectical variants (`centre` <-> `center`).
   - Stripping decorative punctuation (periods, commas, hyphens).
2. **Strictly Prohibited Heuristics:**
   - Automatically equating single-initial strings with full names (`A. Rao` == `Ananya Rao`).
   - Dropping surnames or middle names to force matches.
   - Guessing institutional affiliations not present in the source text.
   - Levenshtein/Jaro-Winkler string distance thresholds for automatic identity resolution.
