"""Canonical locale-scoped manual description storage and resolution."""

from __future__ import annotations

import re
from collections.abc import Mapping

DESCRIPTION_MAX_LENGTH = 20_000
_LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*$")


def normalize_locale(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("locale must be a string")
    value = value.strip()
    if not value or len(value) > 35 or not _LOCALE_RE.fullmatch(value):
        raise ValueError("locale must be a valid BCP-47 language tag")
    parts = value.replace("_", "-").split("-")
    language = parts[0].lower()
    normalized = [language]
    for part in parts[1:]:
        normalized.append(part.upper() if len(part) in {2, 3} else part)
    return "-".join(normalized)


def normalize_description(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("description must be a string or null")
    value = value.strip()
    if not value:
        return None
    if len(value) > DESCRIPTION_MAX_LENGTH:
        raise ValueError(
            f"description must be at most {DESCRIPTION_MAX_LENGTH} characters"
        )
    return value


def _stored_descriptions(metadata: Mapping[str, object] | None) -> dict[str, str]:
    if not isinstance(metadata, Mapping):
        return {}
    raw = metadata.get("descriptions")
    if not isinstance(raw, Mapping):
        return {}
    result: dict[str, str] = {}
    for locale, value in raw.items():
        if not isinstance(locale, str) or not isinstance(value, str):
            continue
        try:
            normalized_locale = normalize_locale(locale)
        except ValueError:
            continue
        normalized_value = normalize_description(value)
        if normalized_value is not None:
            result[normalized_locale] = normalized_value
    return result


def get_manual_description(
    metadata: Mapping[str, object] | None, locale: str
) -> str | None:
    return _stored_descriptions(metadata).get(normalize_locale(locale))


def set_manual_description(
    metadata: Mapping[str, object] | None, locale: str, description: str | None
) -> dict[str, object]:
    normalized_locale = normalize_locale(locale)
    normalized_description = normalize_description(description)
    result = dict(metadata or {})
    descriptions = _stored_descriptions(metadata)
    if normalized_description is None:
        descriptions.pop(normalized_locale, None)
    else:
        descriptions[normalized_locale] = normalized_description
    if descriptions:
        result["descriptions"] = descriptions
    else:
        result.pop("descriptions", None)
    return result


def clear_manual_description(
    metadata: Mapping[str, object] | None, locale: str
) -> dict[str, object]:
    return set_manual_description(metadata, locale, None)


def resolve_description(
    metadata: Mapping[str, object] | None,
    *,
    locale: str,
    provider_variants: Mapping[str, str | None] | None,
    fallback: str | None,
) -> str | None:
    normalized_locale = normalize_locale(locale)
    manual = _stored_descriptions(metadata).get(normalized_locale)
    if manual is not None:
        return manual

    descriptions = _stored_descriptions(metadata)
    for english_locale in ("en", "en-US", "en-GB"):
        manual_english = descriptions.get(english_locale)
        if manual_english is not None:
            return manual_english

    variants = provider_variants or {}
    normalized_variants: dict[str, str] = {}
    for key, value in variants.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        try:
            normalized_key = normalize_locale(key)
        except ValueError:
            continue
        normalized_value = normalize_description(value)
        if normalized_value is not None:
            normalized_variants[normalized_key] = normalized_value

    candidates = [
        normalized_variants.get(normalized_locale),
        normalized_variants.get(normalized_locale.split("-", 1)[0]),
        normalized_variants.get("en"),
    ]
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return normalize_description(fallback)
