# Assignment 03 — DOM Mapping

This document maps the structural HTML/DOM components for both the fictional HTML fixture (`fixture.html`) and the live institutional target (Jawaharlal Nehru University — `https://www.jnu.ac.in/notices`).

---

## Part A: Fictional Fixture DOM Map (`fixture.html`)

### Record Container Identification
- **Record Boundary Element:** `<div class="notice-card" id="notice-...">`
- **Parent Container:** `<div id="notices-container">`
- **Container Boundary Justification:** Each notice item is encapsulated within a discrete `<div class="notice-card">` element. All child attributes (title link, date, speaker, location, summary) are contained strictly inside this element node.

### Detailed Field-by-Field Map

#### 1. Record Container
- **Field:** Event / Notice Card
- **HTML tag:** `div`
- **Important class/id/attribute:** `class="notice-card"`, `id="notice-101"`
- **Parent:** `div#notices-container`
- **Relevant children:** `h2.notice-title`, `div.notice-meta`, `p.notice-summary`

#### 2. Title & Item URL
- **Field:** Title & Link
- **HTML tag:** `a` inside `h2`
- **Important class/id/attribute:** `class="notice-link"`, `href="..."`
- **Parent:** `h2.notice-title` (Child of `div.notice-card`)
- **Relevant children:** Text node (Title text)

#### 3. Date
- **Field:** Notice Date
- **HTML tag:** `time`
- **Important class/id/attribute:** `class="notice-date"`, `datetime="YYYY-MM-DD"`
- **Parent:** `div.notice-meta` (Child of `div.notice-card`)
- **Relevant children:** Text node (e.g. `15 September 2026`)

#### 4. Speaker
- **Field:** Speaker / Publishing Authority
- **HTML tag:** `span`
- **Important class/id/attribute:** `class="speaker-name"`
- **Parent:** `div.notice-meta`
- **Relevant children:** Text node (e.g. `Dr. Aris Thorne` or `Office of the Registrar`)

#### 5. Location
- **Field:** Event Location / Department
- **HTML tag:** `span`
- **Important class/id/attribute:** `class="location-name"`
- **Parent:** `div.notice-meta`
- **Relevant children:** Text node (e.g. `Main Academic Auditorium, Room 101`)

---

## Part B: Real Institutional Target DOM Map (JNU Main Notices Page)

**Target Surface:** `https://www.jnu.ac.in/notices`

### Record Container Identification
- **Record Boundary Element:** `<tr>` inside `<tbody>` of table `<table class="views-table ...">`
- **Parent Container:** `<tbody>`
- **Container Boundary Justification:** Each row (`<tr>`) represents exactly one official university notice record. All cell elements (`<td>`) within a row belong to that specific notice entry.

### Detailed Field-by-Field Map

#### 1. Record Container
- **Field:** Notice Table Row
- **HTML tag:** `tr`
- **Important class/id/attribute:** None (child row inside table body)
- **Parent:** `tbody` -> `table.views-table`
- **Relevant children:** `td` cells (Column 1: Serial No, Column 2: Title, Column 3: Notice Date, Column 4: Download Link)

#### 2. Serial Number
- **Field:** Sl. NO.
- **HTML tag:** `td` (1st column)
- **Important class/id/attribute:** `views-field-counter` or position `td:nth-child(1)`
- **Parent:** `tr`
- **Relevant children:** Text node (e.g. `1`, `2`, `3`)

#### 3. Title
- **Field:** Notice Title
- **HTML tag:** `td` (2nd column)
- **Important class/id/attribute:** `views-field-title` or position `td:nth-child(2)`
- **Parent:** `tr`
- **Relevant children:** Text node containing notice description.

#### 4. Notice Date
- **Field:** Notice Date
- **HTML tag:** `td` (3rd column)
- **Important class/id/attribute:** position `td:nth-child(3)`
- **Parent:** `tr`
- **Relevant children:** Text node formatted as `Mon, 07-09-2026`.

#### 5. Item URL (Notice Document / Detail Page)
- **Field:** Item URL & Download Link
- **HTML tag:** `a` inside `td` (4th column or embedded in Title column)
- **Important class/id/attribute:** `href="/sites/default/files/inline-files/...pdf"`
- **Parent:** `td`
- **Relevant children:** Image icon or link text.

#### 6. Speaker / Authority
- **Field:** Speaker / Organization
- **HTML tag:** Not available as a distinct listing cell.
- **Note:** Information embedded within Title text (e.g., "Circular by Dean of Students").

#### 7. Location
- **Field:** Location
- **HTML tag:** Not available on listing page.
- **Note:** Academic notices apply institution-wide unless specified inside attached PDF document.
