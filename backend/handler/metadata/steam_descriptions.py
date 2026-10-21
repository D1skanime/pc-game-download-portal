"""Pure validation for bounded Steam language slots."""

from collections.abc import Mapping
from typing import Any

from config import STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG

TEXT_VARIANT_NAME_MAX_LENGTH = 255
TEXT_VARIANT_SUMMARY_MAX_LENGTH = 65_535
TEXT_VARIANT_LANGUAGE_BY_TAG = {
    tag: language for language, tag in STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG.items()
}


def bounded_text(value: object, maximum_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text and len(text) <= maximum_length else None


def accepted_text_variants(
    value: object, *, app_id: int, historical: bool = False
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    variants = {}
    for tag, entry in value.items():
        if not isinstance(tag, str) or not isinstance(entry, Mapping):
            continue
        language = TEXT_VARIANT_LANGUAGE_BY_TAG.get(tag)
        if language is None or entry.get("source_language") != language:
            continue
        variant = {"source_language": language}
        for field, limit in (
            ("name", TEXT_VARIANT_NAME_MAX_LENGTH),
            ("summary", TEXT_VARIANT_SUMMARY_MAX_LENGTH),
        ):
            text = bounded_text(entry.get(field), limit)
            if text is not None:
                variant[field] = text
        if len(variant) > 1:
            variants[tag] = variant
    return variants
