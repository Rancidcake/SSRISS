#!/usr/bin/env python3
"""test_entity_schema.py - Unit tests for Entity Relational Store & Schema (Assignment 6)"""

import pytest
from entity_relational_store import (
    EntityRelationalStore,
    normalize_person_name,
    normalize_org_name,
)
from entity_extractor import ExtractedPerson, ExtractedOrganization, EventEntities


@pytest.fixture
def store():
    s = EntityRelationalStore(":memory:")
    yield s
    s.close()


def test_name_normalization():
    assert normalize_person_name("Prof. D. S. Hooda") == "d s hooda"
    assert normalize_person_name("Dr. Divya P. Kumar") == "divya p kumar"
    assert normalize_person_name("Amb. Ruchira Kamboj") == "ruchira kamboj"
    assert normalize_person_name("  Santishree   Pandit  ") == "santishree pandit"


def test_org_normalization():
    assert normalize_org_name("School of Computational and Integrative Sciences") == "school of computational and integrative sciences"
    assert normalize_org_name("SCIS, JNU.") == "scis jnu"


def test_insert_and_deduplicate_person(store):
    id1 = store.get_or_create_person("Dr. Divya P. Kumar")
    id2 = store.get_or_create_person("Divya P. Kumar")
    assert id1 == id2
    assert store.count_people() == 1


def test_insert_and_deduplicate_org(store):
    id1 = store.get_or_create_organization("School of Computational Sciences")
    id2 = store.get_or_create_organization("  school of computational sciences  ")
    assert id1 == id2
    assert store.count_organizations() == 1


def test_store_event_with_entities(store):
    item = {
        "item_url": "https://www.jnu.ac.in/node/159898390",
        "title": "SCIS Lecture by Dr. Divya P. Kumar",
        "source_name": "jnu_events",
        "raw_text": "Speaker: Dr. Divya P. Kumar\nChair: Prof. Indira Ghosh\nOrganized by: SCIS",
    }
    entities = EventEntities(
        people=[
            ExtractedPerson(
                name="Dr. Divya P. Kumar",
                role="speaker",
                affiliation_raw="Centre for Computational Biology",
                source_text="Speaker: Dr. Divya P. Kumar",
            ),
            ExtractedPerson(
                name="Prof. Indira Ghosh",
                role="chair",
                affiliation_raw=None,
                source_text="Chair: Prof. Indira Ghosh",
            ),
        ],
        organizations=[
            ExtractedOrganization(
                name="SCIS",
                role="organizer",
                source_text="Organized by: SCIS",
            )
        ],
    )

    item_id = store.store_event_with_entities(item, entities)
    assert item_id == 1
    assert store.count_items() == 1
    assert store.count_people() == 2
    assert store.count_organizations() == 1
    assert store.count_item_people() == 2
    assert store.count_item_organizations() == 1


def test_checkpoint_query_events_by_person_name(store):
    """Test Question 1: Which events in my local database mention this exact normalized person name?"""
    # Store Event 1
    store.store_event_with_entities(
        {"item_url": "https://www.jnu.ac.in/node/101", "title": "Talk 1"},
        EventEntities(
            people=[ExtractedPerson("Dr. Divya P. Kumar", "speaker", "Bioinformatics", "Speaker: Dr. Divya P. Kumar")]
        ),
    )
    # Store Event 2 (same person as chair)
    store.store_event_with_entities(
        {"item_url": "https://www.jnu.ac.in/node/102", "title": "Symposium 2"},
        EventEntities(
            people=[ExtractedPerson("Divya P. Kumar", "chair", None, "Chair: Divya P. Kumar")]
        ),
    )
    # Store Event 3 (different person)
    store.store_event_with_entities(
        {"item_url": "https://www.jnu.ac.in/node/103", "title": "Other Event"},
        EventEntities(
            people=[ExtractedPerson("Prof. D. S. Hooda", "speaker", None, "Speaker: Prof. D. S. Hooda")]
        ),
    )

    results = store.get_events_by_person_name("divya p kumar")
    assert len(results) == 2
    assert results[0]["event_title"] == "Talk 1"
    assert results[0]["role"] == "speaker"
    assert results[1]["event_title"] == "Symposium 2"
    assert results[1]["role"] == "chair"


def test_checkpoint_query_organizer_organizations(store):
    """Test Question 2: Which organizations have appeared as organizers in my collected sample?"""
    store.store_event_with_entities(
        {"item_url": "https://www.jnu.ac.in/node/101", "title": "Talk 1"},
        EventEntities(
            organizations=[ExtractedOrganization("SCIS", "organizer", "Organized by: SCIS")]
        ),
    )
    store.store_event_with_entities(
        {"item_url": "https://www.jnu.ac.in/node/102", "title": "Talk 2"},
        EventEntities(
            organizations=[
                ExtractedOrganization("SCIS", "organizer", "Organized by: SCIS"),
                ExtractedOrganization("IEEE JNU Student Branch", "co_organizer", "Co-organized by: IEEE"),
            ]
        ),
    )

    orgs = store.get_organizer_organizations()
    assert len(orgs) == 2
    scis_org = [o for o in orgs if o["organization_name"] == "SCIS"][0]
    assert scis_org["event_count"] == 2
    ieee_org = [o for o in orgs if o["organization_name"] == "IEEE JNU Student Branch"][0]
    assert ieee_org["event_count"] == 1


def test_cascade_delete(store):
    item_id = store.store_event_with_entities(
        {"item_url": "https://www.jnu.ac.in/node/101", "title": "Talk 1"},
        EventEntities(
            people=[ExtractedPerson("Dr. Divya P. Kumar", "speaker", None, "Speaker: Dr. Divya P. Kumar")],
            organizations=[ExtractedOrganization("SCIS", "organizer", "Organized by: SCIS")],
        ),
    )
    assert store.count_item_people() == 1
    assert store.count_item_organizations() == 1

    # Delete item
    with store._conn:
        store._conn.execute("DELETE FROM items WHERE id = ?", (item_id,))

    # Join records should be cascaded
    assert store.count_item_people() == 0
    assert store.count_item_organizations() == 0
    # Entity definitions remain in directory
    assert store.count_people() == 1
    assert store.count_organizations() == 1
