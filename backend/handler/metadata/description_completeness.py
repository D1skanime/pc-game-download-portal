"""Pure assessment of missing locale-specific provider descriptions."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import islice

from config import STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG
from handler.metadata.manual_description import DESCRIPTION_MAX_LENGTH, normalize_locale
from handler.metadata.steam_descriptions import (
    TEXT_VARIANT_SUMMARY_MAX_LENGTH,
    accepted_text_variants,
    bounded_text,
    valid_app_id,
    valid_steam_provenance,
)


def description_locale(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if value in STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG:
        return STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG[value]
    try:
        base = normalize_locale(value).split("-", 1)[0]
    except ValueError:
        return None
    return base if base in STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG.values() else None


@dataclass(frozen=True, slots=True)
class DescriptionCompleteness:
    required_locales: tuple[str, ...]
    missing_locales: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_locales


def _mapping(value: object) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _manual_locales(current: Mapping) -> set[str]:
    descriptions = _mapping(
        _mapping(current.get("manual_metadata")).get("descriptions")
    )
    result = set()
    for locale, text in descriptions.items():
        if bounded_text(text, DESCRIPTION_MAX_LENGTH) is None:
            continue
        try:
            result.add(normalize_locale(locale))
        except ValueError:
            continue
    return result


def _provider_locales(current: Mapping, provider: str) -> set[str]:
    if provider == "steam":
        app_id = current.get("steam_id")
        metadata = _mapping(current.get("steam_metadata"))
        if not (
            valid_app_id(app_id)
            and metadata.get("app_id") == app_id
            and metadata.get("source") == "storefront"
            and valid_steam_provenance(metadata, app_id)
        ):
            return set()
        variants = accepted_text_variants(
            metadata.get("text_variants"), app_id=app_id, historical=True
        )
        return {locale for locale, entry in variants.items() if "summary" in entry}
    if provider in ("ss", "screenscraper") and valid_app_id(current.get("ss_id")):
        ss_variants = _mapping(
            _mapping(current.get("ss_metadata")).get("text_variants")
        )
        return {
            locale
            for locale, entry in ss_variants.items()
            if isinstance(locale, str)
            and description_locale(locale) == locale
            and isinstance(entry, Mapping)
            and entry.get("source_language") == locale
            and bounded_text(entry.get("summary"), TEXT_VARIANT_SUMMARY_MAX_LENGTH)
            is not None
        }
    return set()


def assess_description_completeness(
    current: Mapping[str, object],
    configured_languages: Iterable[str] = (),
    metadata_locale: str | None = None,
    *,
    provider: str = "steam",
) -> DescriptionCompleteness:
    requested = description_locale(metadata_locale) or "en"
    extras = (
        configured_languages.split(",")
        if isinstance(configured_languages, str)
        else configured_languages
    )
    required = tuple(
        dict.fromkeys(
            locale
            for value in (requested, "en", *islice(extras, 64))
            if (locale := description_locale(value)) is not None
        )
    )
    manual = _manual_locales(current)
    available = _provider_locales(current, provider)
    try:
        exact = normalize_locale(metadata_locale) if metadata_locale else "en"
    except ValueError:
        exact = requested
    missing = tuple(
        locale
        for locale in required
        if locale not in available
        and locale not in manual
        and not (locale == requested and exact in manual)
        and not (locale == "en" and manual & {"en-US", "en-GB"})
    )
    return DescriptionCompleteness(required, missing)
