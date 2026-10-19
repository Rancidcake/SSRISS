#!/usr/bin/env python3
"""test_entity_extractor.py - Unit tests for explicit entity extractor (Assignment 5)"""

import json
import os
import pytest
from entity_extractor import extract_entities, extract_entities_from_text

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "events_sample.json")


@pytest.fixture
def sample_events():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_extract_entities_from_fixture_records(sample_events):
    assert len(sample_events) >= 10
    total_people = 0
    total_orgs = 0

    for rec in sample_events:
        entities = extract_entities(rec)
        total_people += len(entities.people)
        total_orgs += len(entities.organizations)

        # Check provenance
        for p in entities.people:
            assert p.source_text, f"Missing source_text for person {p.name}"
            assert p.role in {
                "speaker", "chair", "co_chair", "moderator", "panelist",
                "chief_guest", "instructor", "coordinator", "welcome_address", "vote_of_thanks"
            }
        for o in entities.organizations:
            assert o.source_text, f"Missing source_text for organization {o.name}"
            assert o.role in {"organizer", "co_organizer", "host"}

    assert total_people >= 15
    assert total_orgs >= 10


def test_explicit_speaker_with_affiliation():
    text = "Speaker: Dr. Divya P. Kumar, Centre for Computational Biology\nOrganized by: SCIS"
    entities = extract_entities_from_text(text)

    assert len(entities.people) == 1
    p = entities.people[0]
    assert p.name == "Dr. Divya P. Kumar"
    assert p.role == "speaker"
    assert p.affiliation_raw == "Centre for Computational Biology"
    assert p.source_text == "Speaker: Dr. Divya P. Kumar, Centre for Computational Biology"

    assert len(entities.organizations) == 1
    o = entities.organizations[0]
    assert o.name == "SCIS"
    assert o.role == "organizer"


def test_no_inferred_affiliations():
    text = "Chair: Prof. Indira Ghosh"
    entities = extract_entities_from_text(text)
    assert len(entities.people) == 1
    assert entities.people[0].name == "Prof. Indira Ghosh"
    assert entities.people[0].affiliation_raw is None


def test_semicolon_delimited_panelists():
    text = "Panelists: Prof. Niraja Gopal Jayal, King's College London; Dr. Pratap Bhanu Mehta"
    entities = extract_entities_from_text(text)
    assert len(entities.people) == 2
    assert entities.people[0].name == "Prof. Niraja Gopal Jayal"
    assert entities.people[0].affiliation_raw == "King's College London"
    assert entities.people[1].name == "Dr. Pratap Bhanu Mehta"
    assert entities.people[1].affiliation_raw is None


def test_title_fallback_extraction():
    record = {
        "title": "SCIS organises a lecture by Dr. Divya P. Kumar",
        "raw_text": "Venue: Committee Room",  # no explicit field lines in body
    }
    entities = extract_entities(record)
    assert len(entities.organizations) == 1
    assert entities.organizations[0].name == "SCIS"
    assert len(entities.people) == 1
    assert entities.people[0].name == "Dr. Divya P. Kumar"
