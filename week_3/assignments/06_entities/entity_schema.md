# Entity Storage and Relationships — Relational Schema

**Author:** Mayank (SSRISS Intern)  
**Target:** Relational Modeling of Events, Speakers & Organizations (JNU)  
**Assignment:** Assignment 6 — Store Event ↔ Entity Relationships  
**Date:** October 2026  

---

## 1. Schema Architecture & Entity-Relationship Model

To connect events, scholars, and academic institutions across time without data redundancy, entities must not be confined to flat JSON blobs. A normalized relational schema in SQLite establishes many-to-many relationships with role attribution and verbatim provenance:

```text
       +---------------------------------------------+
       |                   items                     |
       +---------------------------------------------+
       | id (PK)                                     |
       | item_url (UNIQUE)                           |
       | item_type ("event" / "announcement")        |
       | title                                       |
       | source_name                                 |
       | raw_text                                    |
       | created_at                                  |
       +---------------------------------------------+
              | 1                             | 1
              |                               |
              | N                             | N
+-------------------------------+ +-------------------------------+
|          item_people          | |       item_organizations      |
+-------------------------------+ +-------------------------------+
| id (PK)                       | | id (PK)                       |
| item_id (FK -> items.id)      | | item_id (FK -> items.id)      |
| person_id (FK -> people.id)   | | organization_id (FK -> org.id)|
| role ("speaker", "chair", etc)| | role ("organizer", "host", etc|
| affiliation_raw               | | source_text                   |
| source_text                   | | created_at                    |
| created_at                    | | UNIQUE(item_id, org_id, role) |
| UNIQUE(item_id, person_id,    | +-------------------------------+
|        role)                  |                 | N
+-------------------------------+                 |
              | N                                 | 1
              | 1                         +-----------------------+
+-------------------------------+         |     organizations     |
|             people            |         +-----------------------+
+-------------------------------+         | id (PK)               |
| id (PK)                       |         | normalized_name (UQ)  |
| normalized_name (UNIQUE)      |         | display_name          |
| display_name                  |         | created_at            |
| created_at                    |         +-----------------------+
+-------------------------------+
```

---

## 2. DDL Schema Definition (SQLite)

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_url    TEXT UNIQUE NOT NULL,
    item_type   TEXT DEFAULT 'event',
    title       TEXT,
    source_name TEXT,
    raw_text    TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE people (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_name TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE organizations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_name TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE item_people (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    person_id       INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    affiliation_raw TEXT,
    source_text     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE(item_id, person_id, role)
);

CREATE TABLE item_organizations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    source_text     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE(item_id, organization_id, role)
);

CREATE INDEX idx_item_people_person ON item_people(person_id);
CREATE INDEX idx_item_orgs_org ON item_organizations(organization_id);
```

---

## 3. Mandatory Checkpoint Queries

### Query 1: Which events in my local database mention this exact normalized person name?

```sql
SELECT 
    i.id AS event_id,
    i.title AS event_title,
    i.item_url,
    p.display_name AS person_name,
    ip.role,
    ip.affiliation_raw,
    ip.source_text
FROM item_people ip
JOIN items i ON ip.item_id = i.id
JOIN people p ON ip.person_id = p.id
WHERE p.normalized_name = 'divya p kumar'
ORDER BY i.id;
```

**Query Execution Sample:**
```text
event_id: 1
event_title: SCIS organises a lecture by Dr. Divya P. Kumar
item_url: https://www.jnu.ac.in/node/159898390
person_name: Dr. Divya P. Kumar
role: speaker
affiliation_raw: Centre for Computational Biology
source_text: Speaker: Dr. Divya P. Kumar, Centre for Computational Biology
```

---

### Query 2: Which organizations have appeared as organizers in my collected sample?

```sql
SELECT DISTINCT
    o.id AS organization_id,
    o.display_name AS organization_name,
    o.normalized_name,
    io.role,
    COUNT(io.item_id) AS event_count
FROM item_organizations io
JOIN organizations o ON io.organization_id = o.id
WHERE io.role IN ('organizer', 'co_organizer')
GROUP BY o.id, io.role
ORDER BY event_count DESC, o.display_name ASC;
```

**Query Execution Sample:**
```text
organization_id: 1 | School of Computational and Integrative Sciences | organizer | 3 events
organization_id: 2 | School of Computer and Systems Sciences         | organizer | 1 event
organization_id: 3 | School of Sanskrit and Indic Studies           | organizer | 1 event
organization_id: 4 | Cryptology Research Society of India           | co_organizer | 1 event
```

---

## 4. Architectural Checkpoint: Relational Decomposition vs. Flat JSON Blobs

A naive approach embeds speaker names and department strings directly inside JSON columns in the `items` table. The relational model provides four critical structural advantages:

1. **Many-to-Many Connectivity:** A scholar can deliver a keynote at SCIS in September, chair a symposium at SCSS in October, and moderate a panel at SIS in November. With join table `item_people`, one unified person row links to all three events under distinct roles (`speaker`, `chair`, `moderator`).
2. **Zero Redundancy on Profile Updates:** If an institutional name or faculty display spelling is refined, only one row in `organizations` or `people` requires updating.
3. **Index-Backed Query Performance:** Answering *"How many conferences has SCIS organized?"* executes as an index seek on `idx_item_orgs_org`, avoiding expensive full-table regex scans over JSON strings.
4. **Verbatim Audit Provenance:** The join tables (`item_people`, `item_organizations`) retain the exact `source_text` line that justified the link, preserving strict auditability.
