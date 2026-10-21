"""Pure assessment of missing locale-specific provider descriptions."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from config import STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG
from handler.metadata.manual_description import normalize_locale


def description_locale(value: object) -> str | None:
    if not isinstance(value, str):
        return None
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


def assess_description_completeness(
    current: Mapping[str, object],
    configured_languages: Iterable[str] = (),
    metadata_locale: str | None = None,
    *,
    provider: str = "steam",
) -> DescriptionCompleteness:
    requested = description_locale(metadata_locale) or "en"
    required = tuple(
        dict.fromkeys(
            locale
            for value in (requested, "en", *configured_languages)
            if (locale := description_locale(value)) is not None
        )
    )
    return DescriptionCompleteness(required, required)
