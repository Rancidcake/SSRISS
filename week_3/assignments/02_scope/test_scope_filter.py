#!/usr/bin/env python3
"""test_scope_filter.py - Unit tests for URL scope filter & canonicalization (Assignment 2)"""

import pytest
from scope_filter import UrlScopeFilter, canonicalize_url, is_allowed_item_url

CONFIG = {
    "allowed_hostname": "www.jnu.ac.in",
    "allowed_path_prefixes": ["/node", "/jnuevents", "/events-archive", "/notices"],
    "excluded_path_prefixes": [
        "/user", "/admin", "/login", "/search", "/filter", "/calendar",
        "/sites/default/files"
    ],
    "allow_external": False,
    "strip_all_query_params": False,
    "ignored_query_params": [
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "ref", "source"
    ],
}


def test_canonicalize_url_strips_fragments():
    raw = "https://www.jnu.ac.in/node/159898390#section-details"
    expected = "https://www.jnu.ac.in/node/159898390"
    assert canonicalize_url(raw, CONFIG) == expected


def test_canonicalize_url_strips_tracking_params():
    raw = "https://www.jnu.ac.in/node/159898390?utm_source=twitter&utm_medium=cpc&real_param=123"
    expected = "https://www.jnu.ac.in/node/159898390?real_param=123"
    assert canonicalize_url(raw, CONFIG) == expected


def test_canonicalize_url_host_alias():
    raw = "https://jnu.ac.in/node/159898390/"
    expected = "https://www.jnu.ac.in/node/159898390"
    assert canonicalize_url(raw, CONFIG) == expected


def test_valid_event_detail_allowed():
    url = "https://www.jnu.ac.in/node/159898390"
    assert is_allowed_item_url(url, CONFIG) is True


def test_valid_notice_allowed():
    url = "https://www.jnu.ac.in/notices"
    assert is_allowed_item_url(url, CONFIG) is True


def test_external_registration_site_denied():
    url = "https://docs.google.com/forms/d/1XKf3OSvnc02rfU7tu8Zl1Mv3vuPtOg2s7G3gvWmjY3Y"
    assert is_allowed_item_url(url, CONFIG) is False


def test_social_media_denied():
    url = "https://twitter.com/JNU_Official_New"
    assert is_allowed_item_url(url, CONFIG) is False


def test_binary_pdf_denied():
    url = "https://www.jnu.ac.in/sites/default/files/notices/circular.pdf"
    assert is_allowed_item_url(url, CONFIG) is False


def test_login_denied():
    url = "https://www.jnu.ac.in/user/login"
    assert is_allowed_item_url(url, CONFIG) is False


def test_search_denied():
    url = "https://www.jnu.ac.in/search/node?keys=test"
    assert is_allowed_item_url(url, CONFIG) is False


def test_calendar_trap_denied():
    url = "https://www.jnu.ac.in/jnuevents?month=11&year=2028"
    assert is_allowed_item_url(url, CONFIG) is False


def test_unallowed_path_prefix_denied():
    url = "https://www.jnu.ac.in/about-us"
    assert is_allowed_item_url(url, CONFIG) is False


def test_scope_filter_duplicate_rejection():
    f = UrlScopeFilter(CONFIG)
    url1 = "https://www.jnu.ac.in/node/159898390"
    url2 = "https://www.jnu.ac.in/node/159898390#anchor"
    url3 = "https://www.jnu.ac.in/node/159898390?utm_source=mail"

    assert f.accept(url1) is True
    assert f.is_duplicate(url2) is True
    assert f.accept(url2) is False
    assert f.accept(url3) is False
    assert len(f.seen_canonical_urls) == 1
