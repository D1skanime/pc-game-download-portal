"""Bounded ScreenScraper description extraction and non-destructive merge."""

import html
from collections.abc import Mapping
from copy import deepcopy
from typing import TypedDict

from config.scan_language import normalize_language
from handler.metadata.manual_description import normalize_locale

MAX_SLOTS = 18
MAX_SUMMARY = 32_000
MAX_TOTAL = 64_000


class SSDescriptionVariant(TypedDict):
    source_language: str
    summary: str


def _locale(value: object) -> str | None:
    if normalize_language(value) is None:
        return None
    try:
        return normalize_locale(value)  # type: ignore[arg-type]
    except ValueError:
        return None


def accepted_synopsis(value: object) -> dict[str, SSDescriptionVariant]:
    if not isinstance(value, list):
        return {}
    variants: dict[str, SSDescriptionVariant] = {}
    total = 0
    for entry in value:
        if not isinstance(entry, Mapping):
            continue
        locale = _locale(entry.get("langue"))
        raw = entry.get("text")
        if locale is None or not isinstance(raw, str) or len(raw) > MAX_SUMMARY:
            continue
        text = html.unescape(raw).strip()
        if not text or len(text) > MAX_SUMMARY:
            continue
        previous = len(variants[locale]["summary"]) if locale in variants else 0
        if (
            locale not in variants and len(variants) >= MAX_SLOTS
        ) or total - previous + len(text) > MAX_TOTAL:
            continue
        total += len(text) - previous
        variants[locale] = {"source_language": locale, "summary": text}
    return variants


def accepted_text_variants(value: object) -> dict[str, SSDescriptionVariant]:
    if not isinstance(value, Mapping):
        return {}
    entries = []
    for locale, entry in value.items():
        if not isinstance(entry, Mapping):
            continue
        normalized = _locale(locale)
        if normalized is None or _locale(entry.get("source_language")) != normalized:
            continue
        entries.append({"langue": normalized, "text": entry.get("summary")})
    return accepted_synopsis(entries)


def merge_ss_metadata(current: object, incoming: object) -> dict:
    """Merge description slots without accepting other incoming metadata."""
    old = current if isinstance(current, Mapping) else {}
    new = incoming if isinstance(incoming, Mapping) else {}
    merged = deepcopy(dict(old))
    variants = accepted_text_variants(old.get("text_variants"))
    accepted = accepted_text_variants(new.get("text_variants"))
    for locale, entry in accepted.items():
        candidate = {**variants, locale: entry}
        if (
            len(candidate) <= MAX_SLOTS
            and sum(len(slot["summary"]) for slot in candidate.values()) <= MAX_TOTAL
        ):
            variants[locale] = entry.copy()
    if variants or "text_variants" in old:
        merged["text_variants"] = variants
    return merged


def select_summary(variants: object, metadata_locale: object = None) -> str:
    accepted = accepted_text_variants(variants)
    requested = _locale(metadata_locale) or normalize_language(metadata_locale) or "en"
    base = requested.split("-", 1)[0]
    for locale in dict.fromkeys((requested, base, "en", "en-US", "en-GB")):
        if entry := accepted.get(locale):
            return entry["summary"]
    return ""
