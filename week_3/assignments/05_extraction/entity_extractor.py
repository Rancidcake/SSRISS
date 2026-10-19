#!/usr/bin/env python3
"""entity_extractor.py - Explicit Entity Extraction for Event Records (Assignment 5)

Extracts structured people and organization entities strictly from explicit
field markers (e.g., "Speaker:", "Organized by:", "Chair:", "Moderator:").

Core Rules Enforced:
1. Extract ONLY what the source text explicitly supports.
2. Preserve raw text (names, titles, raw affiliations).
3. Do NOT infer political orientation or ideology.
4. Do NOT infer affiliations not explicitly shown in the field/line.
5. Do NOT merge two people solely because their names look similar.
6. Provenance: Every extracted entity retains a `source_text` pointer
   referencing the exact line that produced it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExtractedPerson:
    """A person entity extracted from explicit event fields."""
    name: str
    role: str
    affiliation_raw: Optional[str]
    source_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "affiliation_raw": self.affiliation_raw,
            "source_text": self.source_text,
        }


@dataclass
class ExtractedOrganization:
    """An organization entity extracted from explicit event fields."""
    name: str
    role: str
    source_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "source_text": self.source_text,
        }


@dataclass
class EventEntities:
    """Container for all entities extracted from an event record."""
    people: List[ExtractedPerson] = field(default_factory=list)
    organizations: List[ExtractedOrganization] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "people": [p.to_dict() for p in self.people],
            "organizations": [o.to_dict() for o in self.organizations],
        }


# Field patterns for people roles: (compiled regex, canonical role)
PEOPLE_FIELD_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^(?:Keynote\s+Speaker|Guest\s+Speaker|Invited\s+Speaker|Distinguished\s+Speaker)\s*:\s*(.+)$", re.IGNORECASE), "speaker"),
    (re.compile(r"^(?:Speaker|Speakers)\s*:\s*(.+)$", re.IGNORECASE), "speaker"),
    (re.compile(r"^(?:General\s+Chair|Session\s+Chair|Chair|Chairs)\s*:\s*(.+)$", re.IGNORECASE), "chair"),
    (re.compile(r"^(?:Co-chair|Co-Chair)\s*:\s*(.+)$", re.IGNORECASE), "co_chair"),
    (re.compile(r"^(?:Moderator|Moderators)\s*:\s*(.+)$", re.IGNORECASE), "moderator"),
    (re.compile(r"^(?:Panelist|Panelists)\s*:\s*(.+)$", re.IGNORECASE), "panelist"),
    (re.compile(r"^(?:Chief\s+Guest)\s*:\s*(.+)$", re.IGNORECASE), "chief_guest"),
    (re.compile(r"^(?:Instructor|Instructors)\s*:\s*(.+)$", re.IGNORECASE), "instructor"),
    (re.compile(r"^(?:Coordinator|Coordinators)\s*:\s*(.+)$", re.IGNORECASE), "coordinator"),
    (re.compile(r"^(?:Welcome\s+Address)\s*:\s*(.+)$", re.IGNORECASE), "welcome_address"),
    (re.compile(r"^(?:Vote\s+of\s+Thanks)\s*:\s*(.+)$", re.IGNORECASE), "vote_of_thanks"),
]

# Field patterns for organization roles: (compiled regex, canonical role)
ORG_FIELD_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^(?:Organized\s+by|Organisers?|Organizers?)\s*:\s*(.+)$", re.IGNORECASE), "organizer"),
    (re.compile(r"^(?:Co-organized\s+by|Co-organisers?|Co-organizers?|In\s+collaboration\s+with)\s*:\s*(.+)$", re.IGNORECASE), "co_organizer"),
    (re.compile(r"^(?:Hosted\s+by|Host)\s*:\s*(.+)$", re.IGNORECASE), "host"),
]

# Title-level fallback regex patterns for JNU
TITLE_ORG_PATTERN = re.compile(r"^([A-Z0-9,\s]+?)\s+(?:organi[sz]es|is celebrating|celebrates|invites|Special\s+Seminar|Colloquium|Seminar)\b", re.IGNORECASE)
TITLE_SPEAKER_PATTERN = re.compile(r"\b(?:lecture|talk|seminar|address|keynote|colloquium)?\b.*?\bby\s+(.+)$", re.IGNORECASE)


def _parse_person_entry(raw_entry: str, role: str, line_text: str) -> ExtractedPerson:
    """Parse name and optional raw affiliation from an individual person entry.

    e.g. "Dr. Divya P. Kumar, Centre for Computational Biology"
    -> Name: "Dr. Divya P. Kumar", Affiliation: "Centre for Computational Biology"
    """
    clean = raw_entry.strip().rstrip(".")
    affiliation = None

    # Check for affiliation separated by comma
    if "," in clean:
        parts = [p.strip() for p in clean.split(",") if p.strip()]
        # Check if first part looks like a name with honorific/initials
        # e.g., "Prof. D. S. Hooda, Former Head..."
        name_part = parts[0]
        # If second part is also an honorific or short title, be cautious
        if len(parts) > 1:
            affiliation = ", ".join(parts[1:])
            name = name_part
        else:
            name = clean
    else:
        name = clean

    return ExtractedPerson(
        name=name.strip(),
        role=role,
        affiliation_raw=affiliation.strip() if affiliation else None,
        source_text=line_text.strip(),
    )


def extract_entities_from_text(text: str) -> EventEntities:
    """Extract people and organization entities from structured text lines."""
    people: List[ExtractedPerson] = []
    organizations: List[ExtractedOrganization] = []

    lines = [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]

    for line in lines:
        matched_person = False
        for pattern, role in PEOPLE_FIELD_PATTERNS:
            m = pattern.match(line)
            if m:
                content = m.group(1).strip()
                # Handle multiple people delimited by semicolons
                entries = [e.strip() for e in content.split(";") if e.strip()]
                for entry in entries:
                    people.append(_parse_person_entry(entry, role, line))
                matched_person = True
                break

        if matched_person:
            continue

        for pattern, role in ORG_FIELD_PATTERNS:
            m = pattern.match(line)
            if m:
                content = m.group(1).strip()
                entries = [e.strip() for e in content.split(";") if e.strip()]
                for entry in entries:
                    organizations.append(ExtractedOrganization(
                        name=entry.rstrip("."),
                        role=role,
                        source_text=line.strip(),
                    ))
                break

    return EventEntities(people=people, organizations=organizations)


def extract_entities(record: Dict[str, Any]) -> EventEntities:
    """Extract entities from both raw_text and title of an event record."""
    raw_text = record.get("raw_text") or ""
    entities = extract_entities_from_text(raw_text)

    # If no organizations or people found in body, inspect title for explicit JNU patterns
    title = record.get("title") or ""
    if not entities.organizations and title:
        m_org = TITLE_ORG_PATTERN.match(title)
        if m_org:
            org_candidate = m_org.group(1).strip()
            if len(org_candidate) > 1 and not org_candidate.lower().startswith("the"):
                entities.organizations.append(ExtractedOrganization(
                    name=org_candidate,
                    role="organizer",
                    source_text=title,
                ))

    if not entities.people and title:
        m_spk = TITLE_SPEAKER_PATTERN.search(title)
        if m_spk:
            entities.people.append(ExtractedPerson(
                name=m_spk.group(1).strip().rstrip("."),
                role="speaker",
                affiliation_raw=None,
                source_text=title,
            ))

    return entities
