"""ScreenScraper description bounds and merge contracts."""

from copy import deepcopy

import pytest

from handler.metadata.ss_descriptions import (
    accepted_synopsis,
    merge_ss_metadata,
    select_summary,
)


def test_regions_entities_supported():
    assert accepted_synopsis(
        [
            {"langue": " de_DE ", "text": " Deutsch &amp; mehr "},
            {"langue": "unknown", "text": "bad"},
        ]
    ) == {"de-DE": {"source_language": "de-DE", "summary": "Deutsch & mehr"}}


@pytest.mark.parametrize("bad", [None, {}, 3, "text"])
def test_invalid_container(bad):
    assert accepted_synopsis(bad) == {}


def test_bad_entries():
    assert (
        accepted_synopsis(
            [
                None,
                "bad",
                {},
                {"langue": 1, "text": "bad"},
                {"langue": "fr", "text": " "},
            ]
        )
        == {}
    )


def test_size_and_total_bounds():
    entries = [
        {"langue": "de", "text": "x" * 32001},
        {"langue": "en", "text": "x" * 32000},
        {"langue": "fr", "text": "y" * 32000},
        {"langue": "de", "text": "too much"},
    ]
    assert accepted_synopsis(entries) == {
        "en": {"source_language": "en", "summary": "x" * 32000},
        "fr": {"source_language": "fr", "summary": "y" * 32000},
    }


def test_count_bound():
    assert (
        len(
            accepted_synopsis(
                [{"langue": f"de-{i:02d}", "text": str(i)} for i in range(30)]
            )
        )
        == 18
    )


def test_partial_merge():
    current: dict = {
        "text_variants": {
            "de": {"source_language": "de", "summary": "Old"},
            "en": {"source_language": "en", "summary": "English"},
        },
        "box2d_url": "old",
    }
    incoming = {
        "text_variants": {
            "de": {"source_language": "de", "summary": ""},
            "fr": {"source_language": "fr", "summary": "French"},
            "en": {"source_language": "de", "summary": "Wrong"},
        },
        "box2d_url": None,
        "manual_metadata": {"descriptions": {"en": "Untrusted"}},
    }
    before = deepcopy((current, incoming))
    merged = merge_ss_metadata(current, incoming)
    assert merged["text_variants"] == {
        **current["text_variants"],
        "fr": {"source_language": "fr", "summary": "French"},
    }
    assert merged["box2d_url"] == "old"
    assert "manual_metadata" not in merged
    assert (current, incoming) == before


def test_exact_base_english_selection():
    variants = accepted_synopsis(
        [
            {"langue": "de", "text": "German"},
            {"langue": "fr", "text": "French"},
            {"langue": "en", "text": "English"},
            {"langue": "fr_CA", "text": "Quebec"},
        ]
    )
    assert select_summary(variants, "fr-CA") == "Quebec"
    assert select_summary(variants, "fr-CH") == "French"
    assert select_summary(variants, "de-DE") == "German"
    assert select_summary(variants, "it") == "English"
    assert select_summary(variants) == "English"
    assert select_summary({"fr": variants["fr"]}, "de") == ""
