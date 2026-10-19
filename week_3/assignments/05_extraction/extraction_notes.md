# Explicit Entity Extraction — Methodology & Invariants

**Author:** Mayank (SSRISS Intern)  
**Target:** Event Speakers, Chairs & Organizing Units (JNU)  
**Assignment:** Assignment 5 — Entity Extraction from Explicit Fields  
**Date:** October 2026  

---

## 1. Grounding Principles & Operational Invariants

Week 3 mandates explicit entity extraction based strictly on observable, deterministic surface text. The extraction engine operates under six inviolable constraints:

1. **Extract ONLY What the Source Text Explicitly Supports:**
   - Entities are instantiated only when preceded by unambiguous structural markers (e.g., `Speaker:`, `Keynote Speaker:`, `Session Chair:`, `Organized by:`, `Moderator:`).
   - Unlabeled names in the body of an announcement are ignored.
2. **Strict Verbatim Provenance (`source_text`):**
   - Every `ExtractedPerson` and `ExtractedOrganization` record stores the exact, unmutated line of source text that generated it (`source_text`).
   - If an extraction is ever questioned, an auditor can immediately trace the database entry back to its originating string.
3. **ZERO Inferred Affiliations:**
   - If a line reads `Speaker: Dr. Divya P. Kumar, Centre for Computational Biology`, the affiliation `Centre for Computational Biology` is extracted because it was explicitly provided on that line.
   - If a line reads `Speaker: Prof. Santishree Dhulipudi Pandit` without naming JNU, the extractor records `affiliation_raw = null`. The extractor never assumes or injects institutional affiliation based on outside knowledge.
4. **ZERO Political, Ideological, or Sentiment Inference:**
   - The monitor strictly records who spoke, in what capacity, and which unit organized the event. It does not classify events by political leaning, ideology, or sentiment.
5. **Preservation of Raw Display Text:**
   - Extracted names preserve their original academic honorifics and capitalization (`Prof. D. S. Hooda`, `Dr. Divya P. Kumar`).
   - Honorific stripping and normalization occur in downstream resolution tables, never by mutating the raw entity.
6. **Conservative Role Mapping:**
   - Roles are normalized to an enumeration of explicit capacities:
     - People: `speaker`, `chair`, `co_chair`, `moderator`, `panelist`, `chief_guest`, `instructor`, `coordinator`, `welcome_address`, `vote_of_thanks`.
     - Organizations: `organizer`, `co_organizer`, `host`.

---

## 2. Extraction Examples from JNU Event Corpus

### Example 1: Speaker with Explicit Affiliation
- **Source Line:** `Speaker: Dr. Divya P. Kumar, Centre for Computational Biology`
- **Extracted Structure:**
  ```json
  {
    "name": "Dr. Divya P. Kumar",
    "role": "speaker",
    "affiliation_raw": "Centre for Computational Biology",
    "source_text": "Speaker: Dr. Divya P. Kumar, Centre for Computational Biology"
  }
  ```

### Example 2: Multi-Role Session with Unaffiliated Chair
- **Source Lines:**
  ```text
  Organized by: School of Computational and Integrative Sciences
  Chair: Prof. Indira Ghosh
  ```
- **Extracted Structure:**
  ```json
  {
    "people": [
      {
        "name": "Prof. Indira Ghosh",
        "role": "chair",
        "affiliation_raw": null,
        "source_text": "Chair: Prof. Indira Ghosh"
      }
    ],
    "organizations": [
      {
        "name": "School of Computational and Integrative Sciences",
        "role": "organizer",
        "source_text": "Organized by: School of Computational and Integrative Sciences"
      }
    ]
  }
  ```

### Example 3: Delimited Panelists
- **Source Line:** `Panelists: Prof. Niraja Gopal Jayal, King's College London; Dr. Pratap Bhanu Mehta`
- **Extracted Structure:**
  ```json
  {
    "people": [
      {
        "name": "Prof. Niraja Gopal Jayal",
        "role": "panelist",
        "affiliation_raw": "King's College London",
        "source_text": "Panelists: Prof. Niraja Gopal Jayal, King's College London; Dr. Pratap Bhanu Mehta"
      },
      {
        "name": "Dr. Pratap Bhanu Mehta",
        "role": "panelist",
        "affiliation_raw": null,
        "source_text": "Panelists: Prof. Niraja Gopal Jayal, King's College London; Dr. Pratap Bhanu Mehta"
      }
    ]
  }
  ```

---

## 3. Checkpoint: Provenance Verification

Every extracted entity in our SQLite schema points back to `source_text`. If a database row records:
```text
Person ID: 42
Name: Prof. Bart Preneel
Role: speaker
Affiliation: KU Leuven
Source Text: Keynote Speaker: Prof. Bart Preneel, KU Leuven
```
The link between the entity and the ground-truth HTML card is mathematically traceable and fully auditable.
