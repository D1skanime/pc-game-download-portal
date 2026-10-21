"""ScreenScraper description slot helpers."""

from handler.metadata.ss_handler import _get_text_variants


def accepted_synopsis(value):
    return _get_text_variants({"synopsis": value})


def merge_ss_metadata(current, incoming):
    return {**current, **incoming}


def select_summary(variants, metadata_locale=None):
    return variants.get(metadata_locale or "en", {}).get("summary", "")
