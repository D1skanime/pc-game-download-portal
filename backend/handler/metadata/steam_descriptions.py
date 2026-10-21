"""Pure validation for bounded Steam language slots."""

from collections.abc import Mapping
from typing import Any, TypeGuard

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


def valid_app_id(value: object) -> TypeGuard[int]:
    return type(value) is int and value > 0


def valid_steam_provenance(value: Mapping, app_id: int) -> bool:
    return (
        valid_app_id(app_id)
        and (
            "app_id" not in value
            or (valid_app_id(value["app_id"]) and value["app_id"] == app_id)
        )
        and ("type" not in value or value["type"] in ("game", "dlc"))
        and ("source" not in value or value["source"] == "storefront")
    )


def accepted_text_variants(
    value: object, *, app_id: int, historical: bool = False
) -> dict[str, dict[str, Any]]:
    """Accept slot evidence without claiming linguistic certainty."""
    if not isinstance(value, Mapping) or not valid_app_id(app_id):
        return {}
    variants: dict[str, dict[str, Any]] = {}
    for tag, entry in value.items():
        if not isinstance(tag, str) or not isinstance(entry, Mapping):
            continue
        language = TEXT_VARIANT_LANGUAGE_BY_TAG.get(tag)
        if (
            language is None
            or bounded_text(entry.get("source_language"), 32) != language
            or not valid_steam_provenance(entry, app_id)
            or (
                "requested_language" in entry
                and entry["requested_language"] != language
            )
            or (
                "language_evidence" in entry
                and entry["language_evidence"] != "provider_slot"
            )
        ):
            continue
        variant = {"source_language": language}
        for field, limit in (
            ("name", TEXT_VARIANT_NAME_MAX_LENGTH),
            ("summary", TEXT_VARIANT_SUMMARY_MAX_LENGTH),
        ):
            text = bounded_text(entry.get(field), limit)
            if text is not None:
                variant[field] = text
        if not (variant.keys() & {"name", "summary"}):
            continue
        for field in ("requested_language", "language_evidence"):
            if field in entry:
                variant[field] = entry[field]
        variants[tag] = variant

    english = variants.get("en", {}).get("summary")
    if english and not historical:
        for tag, variant in list(variants.items()):
            if tag != "en" and variant.get("summary") == english:
                variant.pop("summary")
                if not (variant.keys() & {"name", "summary"}):
                    variants.pop(tag)
    return variants
