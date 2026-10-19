#!/usr/bin/env python3
"""test_entity_matching.py - Unit tests for entity matching resolution policy (Assignment 7)"""

import json
import os
import pytest
from entity_matcher import (
    MatchDecision,
    match_entities,
    match_people,
    match_organizations,
)

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "matching_pairs.json")


@pytest.fixture
def benchmark_pairs():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_matching_policy_against_all_fixture_pairs(benchmark_pairs):
    for pair in benchmark_pairs:
        res = match_entities(pair["entity_type"], pair["entity_a"], pair["entity_b"])
        assert res.decision.value == pair["expected_decision"], (
            f"Failed on [{pair['entity_type']}] '{pair['entity_a']}' vs '{pair['entity_b']}': "
            f"Expected '{pair['expected_decision']}', got '{res.decision.value}'"
        )


def test_person_safe_automatic_match():
    res1 = match_people("Prof. Ananya Rao", "Ananya Rao")
    assert res1.decision == MatchDecision.SAFE_AUTOMATIC_MATCH

    res2 = match_people("Prof Ananya Rao", "Ananya Rao")
    assert res2.decision == MatchDecision.SAFE_AUTOMATIC_MATCH

    res3 = match_people("Dr. Divya P. Kumar", "Divya P Kumar")
    assert res3.decision == MatchDecision.SAFE_AUTOMATIC_MATCH


def test_person_review_required():
    res1 = match_people("A. Rao", "Ananya Rao")
    assert res1.decision == MatchDecision.POSSIBLE_MATCH_REQUIRING_REVIEW

    res2 = match_people("Ananya R.", "Ananya Rao")
    assert res2.decision == MatchDecision.POSSIBLE_MATCH_REQUIRING_REVIEW


def test_person_do_not_match():
    res = match_people("Dr. Arvind Sharma", "Dr. Anand Sharma")
    assert res.decision == MatchDecision.DO_NOT_MATCH_AUTOMATICALLY


def test_org_safe_automatic_match():
    res1 = match_organizations("Centre for Policy Research", "Center for Policy Research")
    assert res1.decision == MatchDecision.SAFE_AUTOMATIC_MATCH

    res2 = match_organizations("Centre for Policy Research", "Centre for Policy Research (CPR)")
    assert res2.decision == MatchDecision.SAFE_AUTOMATIC_MATCH


def test_org_review_required():
    res = match_organizations("CPR", "Centre for Policy Research")
    assert res.decision == MatchDecision.POSSIBLE_MATCH_REQUIRING_REVIEW


def test_org_do_not_match():
    res = match_organizations(
        "School of Computer and Systems Sciences",
        "School of Computational and Integrative Sciences",
    )
    assert res.decision == MatchDecision.DO_NOT_MATCH_AUTOMATICALLY
