import pytest

from handler.metadata.manual_description import (
    clear_manual_description,
    normalize_locale,
    resolve_description,
    set_manual_description,
)


def test_manual_description_is_scoped_to_the_requested_locale():
    metadata = set_manual_description({}, "de-DE", "Deutsche Beschreibung")

    assert (
        resolve_description(
            metadata,
            locale="de-DE",
            provider_variants={"de": "Provider Deutsch", "en": "Provider English"},
            fallback="Legacy summary",
        )
        == "Deutsche Beschreibung"
    )
    assert (
        resolve_description(
            metadata,
            locale="en-US",
            provider_variants={"de": "Provider Deutsch", "en": "Provider English"},
            fallback="Legacy summary",
        )
        == "Provider English"
    )


def test_clear_manual_description_restores_provider_fallback():
    metadata = set_manual_description({}, "de-DE", "Deutsche Beschreibung")
    cleared = clear_manual_description(metadata, "de-DE")

    assert cleared == {}
    assert (
        resolve_description(
            cleared,
            locale="de-DE",
            provider_variants={"de": "Provider Deutsch", "en": "Provider English"},
            fallback="Legacy summary",
        )
        == "Provider Deutsch"
    )


def test_manual_english_description_precedes_provider_fallback():
    metadata = set_manual_description({}, "en", "Manual English description")

    assert (
        resolve_description(
            metadata,
            locale="fr-FR",
            provider_variants={"en": "Provider English"},
            fallback="Legacy summary",
        )
        == "Manual English description"
    )


def test_locale_and_description_validation_is_actionable():
    with pytest.raises(ValueError, match="locale"):
        normalize_locale("not a locale")

    with pytest.raises(ValueError, match="description"):
        set_manual_description({}, "en-US", "x" * 20_001)

    assert (
        clear_manual_description(
            set_manual_description({}, "en-US", "English description"), "en-US"
        )
        == {}
    )
