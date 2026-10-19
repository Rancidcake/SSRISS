#!/usr/bin/env python3
"""entity_matcher.py - Entity Matching Policy & Decision Engine (Assignment 7)

Implements conservative entity resolution policies for People and Organizations.

Core Policy:
- Favor FALSE SPLITS over FALSE MERGES when identity is uncertain.
- Weak or partial similarity produces 'possible match requiring review',
  NEVER 'safe automatic match'.
- Distinct entities produce 'do not match automatically'.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple


class MatchDecision(str, Enum):
    SAFE_AUTOMATIC_MATCH = "safe automatic match"
    POSSIBLE_MATCH_REQUIRING_REVIEW = "possible match requiring review"
    DO_NOT_MATCH_AUTOMATICALLY = "do not match automatically"


@dataclass
class MatchResult:
    entity_type: str
    entity_a: str
    entity_b: str
    decision: MatchDecision
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "decision": self.decision.value,
            "rationale": self.rationale,
        }


# ---------------------------------------------------------------------------
# Normalization Utilities
# ---------------------------------------------------------------------------

_HONORIFIC_REGEX = re.compile(
    r"^(?:prof(?:essor)?|dr|mr|ms|mrs|shri|smt|amb(?:assador)?|justice|adv(?:ocate)?)\.?\s+",
    re.IGNORECASE,
)


def _normalize_person(name: str) -> str:
    """Strip honorifics, punctuation, and lowercase person name."""
    clean = name.strip().lower()
    clean = _HONORIFIC_REGEX.sub("", clean).strip()
    clean = re.sub(r"[\.,]", " ", clean)
    return " ".join(clean.split())


def _normalize_org(org: str) -> Tuple[str, Optional[str]]:
    """Normalize organization name, standardizing British/American spelling
    and separating any trailing parenthetical acronym.
    
    Returns: (normalized_name, extracted_acronym)
    """
    clean = org.strip().lower()
    extracted_acronym = None

    paren_match = re.search(r"\(([^)]+)\)$", clean)
    if paren_match:
        inner = paren_match.group(1).strip()
        if len(inner) <= 6 and inner.isalpha():
            extracted_acronym = inner.lower()
            clean = clean[:paren_match.start()].strip()

    # Standardize British vs American spelling
    clean = re.sub(r"\bcentre\b", "center", clean)
    clean = re.sub(r"[\.,]", " ", clean)
    clean = " ".join(clean.split())
    return clean, extracted_acronym


def _get_acronym(phrase: str) -> str:
    stopwords = {"for", "and", "of", "the", "in", "to", "on", "a", "an"}
    words = [w for w in phrase.split() if w not in stopwords]
    return "".join(w[0] for w in words if w)


# ---------------------------------------------------------------------------
# Decision Engines
# ---------------------------------------------------------------------------

def match_people(name_a: str, name_b: str) -> MatchResult:
    """Evaluate candidate person match under conservative resolution policy."""
    norm_a = _normalize_person(name_a)
    norm_b = _normalize_person(name_b)

    # 1. Exact match after stripping honorifics & whitespace
    if norm_a == norm_b:
        return MatchResult(
            entity_type="person",
            entity_a=name_a,
            entity_b=name_b,
            decision=MatchDecision.SAFE_AUTOMATIC_MATCH,
            rationale="Exact token match after stripping honorifics, punctuation, and case normalization.",
        )

    tokens_a = norm_a.split()
    tokens_b = norm_b.split()

    if not tokens_a or not tokens_b:
        return MatchResult(
            entity_type="person",
            entity_a=name_a,
            entity_b=name_b,
            decision=MatchDecision.DO_NOT_MATCH_AUTOMATICALLY,
            rationale="One or both names are empty.",
        )

    # 2. Check for initial + surname overlap (e.g. "A Rao" vs "Ananya Rao", "Ananya R" vs "Ananya Rao")
    # Same surname (last token) and first token initial matches
    surname_a = tokens_a[-1]
    surname_b = tokens_b[-1]

    first_a = tokens_a[0]
    first_b = tokens_b[0]

    if surname_a == surname_b and len(tokens_a) == len(tokens_b):
        # Case: A. Rao vs Ananya Rao
        if (len(first_a) == 1 and first_b.startswith(first_a)) or (len(first_b) == 1 and first_a.startswith(first_b)):
            return MatchResult(
                entity_type="person",
                entity_a=name_a,
                entity_b=name_b,
                decision=MatchDecision.POSSIBLE_MATCH_REQUIRING_REVIEW,
                rationale="Single initial matches first letter of full name with identical surname; high false-merge risk.",
            )

    # Case: Ananya R. vs Ananya Rao
    if first_a == first_b:
        if (len(surname_a) == 1 and surname_b.startswith(surname_a)) or (len(surname_b) == 1 and surname_a.startswith(surname_b)):
            return MatchResult(
                entity_type="person",
                entity_a=name_a,
                entity_b=name_b,
                decision=MatchDecision.POSSIBLE_MATCH_REQUIRING_REVIEW,
                rationale="First names match but surname is abbreviated to an initial; requires review.",
            )

    # 3. Default: do not match automatically
    return MatchResult(
        entity_type="person",
        entity_a=name_a,
        entity_b=name_b,
        decision=MatchDecision.DO_NOT_MATCH_AUTOMATICALLY,
        rationale="Distinct first names or non-matching tokens; treated as separate individuals to prevent false merge.",
    )


def match_organizations(org_a: str, org_b: str) -> MatchResult:
    """Evaluate candidate organization match under conservative resolution policy."""
    base_a, acr_a = _normalize_org(org_a)
    base_b, acr_b = _normalize_org(org_b)

    # 1. Exact match after spelling normalization (centre -> center)
    if base_a == base_b:
        return MatchResult(
            entity_type="organization",
            entity_a=org_a,
            entity_b=org_b,
            decision=MatchDecision.SAFE_AUTOMATIC_MATCH,
            rationale="Exact match after British/American spelling normalization and whitespace cleaning.",
        )

    # 2. One has parenthetical acronym that matches the other
    if acr_b and (base_a == base_b or acr_b == _get_acronym(base_a)):
        return MatchResult(
            entity_type="organization",
            entity_a=org_a,
            entity_b=org_b,
            decision=MatchDecision.SAFE_AUTOMATIC_MATCH,
            rationale="Organization title matches alongside verified parenthetical acronym expansion.",
        )
    if acr_a and (base_a == base_b or acr_a == _get_acronym(base_b)):
        return MatchResult(
            entity_type="organization",
            entity_a=org_a,
            entity_b=org_b,
            decision=MatchDecision.SAFE_AUTOMATIC_MATCH,
            rationale="Organization title matches alongside verified parenthetical acronym expansion.",
        )

    # 3. Bare acronym vs full name (e.g. "CPR" vs "Center for Policy Research")
    raw_a_clean = re.sub(r"[^a-zA-Z]", "", org_a).lower()
    raw_b_clean = re.sub(r"[^a-zA-Z]", "", org_b).lower()

    if len(raw_a_clean) <= 5 and raw_a_clean == _get_acronym(base_b):
        return MatchResult(
            entity_type="organization",
            entity_a=org_a,
            entity_b=org_b,
            decision=MatchDecision.POSSIBLE_MATCH_REQUIRING_REVIEW,
            rationale="Standalone acronym matches initials of organization; requires human review to avoid collision.",
        )
    if len(raw_b_clean) <= 5 and raw_b_clean == _get_acronym(base_a):
        return MatchResult(
            entity_type="organization",
            entity_a=org_a,
            entity_b=org_b,
            decision=MatchDecision.POSSIBLE_MATCH_REQUIRING_REVIEW,
            rationale="Standalone acronym matches initials of organization; requires human review to avoid collision.",
        )

    # 4. Default: distinct organizations
    return MatchResult(
        entity_type="organization",
        entity_a=org_a,
        entity_b=org_b,
        decision=MatchDecision.DO_NOT_MATCH_AUTOMATICALLY,
        rationale="Distinct organizational names and initials; must not be merged automatically.",
    )


def match_entities(entity_type: str, entity_a: str, entity_b: str) -> MatchResult:
    if entity_type == "person":
        return match_people(entity_a, entity_b)
    elif entity_type == "organization":
        return match_organizations(entity_a, entity_b)
    else:
        raise ValueError(f"Unknown entity_type '{entity_type}'")
