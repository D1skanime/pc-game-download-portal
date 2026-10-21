from copy import deepcopy

import pytest

from handler.metadata.description_completeness import assess_description_completeness
from handler.metadata.steam_descriptions import accepted_text_variants


def slot(language, text="Description", **extra):
    return {"source_language": language, "summary": text, **extra}


def test_legacy_identity_and_scalar_do_not_establish_completeness():
    result = assess_description_completeness(
        {"steam_id": 1245620, "name": "Elden Ring", "summary": "Legacy"},
        ("german", "english"),
        "de-DE",
    )
    assert result.required_locales == ("de", "en")
    assert result.missing_locales == ("de", "en")
    assert not result.complete


@pytest.mark.parametrize(
    "locale,expected", [(None, "en"), ("de-DE", "de"), ("fr_FR", "fr")]
)
def test_requested_locale_and_english_are_required_despite_configured_extras(
    locale, expected
):
    result = assess_description_completeness(
        {}, ("german", "english", "invalid") * 30, locale
    )
    assert result.required_locales == tuple(dict.fromkeys((expected, "en", "de")))


@pytest.mark.parametrize("manual_locale", ["de", "de-DE", "de_DE"])
def test_manual_exact_and_base_satisfy_only_requested_locale(manual_locale):
    current = {
        "manual_metadata": {"descriptions": {manual_locale: "Manuell", "en": "Manual"}}
    }
    before = deepcopy(current)
    assert assess_description_completeness(current, (), "de-DE").complete
    assert current == before


def test_manual_english_never_satisfies_missing_french():
    result = assess_description_completeness(
        {"manual_metadata": {"descriptions": {"en": "Manual"}}}, (), "fr-FR"
    )
    assert result.missing_locales == ("fr",)


def test_matching_historical_provider_slots_are_complete():
    current = {
        "steam_id": 38,
        "steam_metadata": {
            "app_id": 38,
            "source": "storefront",
            "text_variants": {
                "de": slot("german", "Deutsch"),
                "en": slot("english", "English"),
            },
        },
    }
    assert assess_description_completeness(current, (), "de-DE").complete


@pytest.mark.parametrize(
    "metadata",
    [
        {"app_id": 39, "source": "storefront"},
        {"app_id": True, "source": "storefront"},
        {"app_id": 38, "source": "other"},
        {"app_id": 38, "source": "storefront", "type": "movie"},
    ],
)
def test_wrong_provider_identity_or_type_never_satisfies_locale(metadata):
    current = {
        "steam_id": 38,
        "steam_metadata": {
            **metadata,
            "text_variants": {"en": slot("english")},
        },
    }
    assert assess_description_completeness(current).missing_locales == ("en",)


@pytest.mark.parametrize("text", ["", "   ", None, 42, "x" * 65536])
def test_invalid_summary_is_not_accepted(text):
    assert accepted_text_variants({"de": slot("german", text)}, app_id=38) == {}


@pytest.mark.parametrize(
    "extra",
    [
        {"app_id": 39},
        {"app_id": True},
        {"type": "movie"},
        {"source": "other"},
        {"requested_language": "english"},
        {"language_evidence": "detector"},
    ],
)
def test_invalid_slot_provenance_is_rejected(extra):
    assert accepted_text_variants({"de": slot("german", **extra)}, app_id=38) == {}


def test_new_identical_english_is_ambiguous_but_historical_pair_is_preserved():
    value = {"de": slot("german", " Same "), "en": slot("english", "Same")}
    assert "summary" not in accepted_text_variants(value, app_id=38).get("de", {})
    assert accepted_text_variants(value, app_id=38)["en"]["summary"] == "Same"
    assert (
        accepted_text_variants(value, app_id=38, historical=True)["de"]["summary"]
        == "Same"
    )


def test_distinct_slots_retain_request_evidence_and_english():
    value = {
        "de": slot(
            "german",
            "Deutsch",
            requested_language="german",
            language_evidence="provider_slot",
        ),
        "fr": slot("french", "Francais"),
        "en": slot("english", "English"),
    }
    accepted = accepted_text_variants(value, app_id=38)
    assert set(accepted) == {"de", "fr", "en"}
    assert accepted["de"]["requested_language"] == "german"
    assert accepted["de"]["language_evidence"] == "provider_slot"


def test_screenscraper_explicit_language_slots_share_completeness():
    current = {
        "ss_id": 38,
        "ss_metadata": {
            "text_variants": {
                "fr": slot("fr", "Francais"),
                "en": slot("en", "English"),
            }
        },
    }
    assert assess_description_completeness(current, (), "fr", provider="ss").complete


def test_provider_requested_text_is_complete_without_changing_manual_english():
    current = {
        "steam_id": 38,
        "manual_metadata": {"descriptions": {"en": "Manual"}},
        "steam_metadata": {
            "app_id": 38,
            "source": "storefront",
            "text_variants": {"fr": slot("french", "Francais")},
        },
    }
    before = deepcopy(current)
    assert assess_description_completeness(current, (), "fr").complete
    assert current == before
