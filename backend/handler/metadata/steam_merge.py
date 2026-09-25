"""Guarded Steam metadata normalization shared by PC application paths."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

DISPLAY_FIELDS = frozenset(
    {"name", "summary", "main_developer", "publishers", "pc_release_date"}
)
MANUAL_FIELDS = frozenset({"name", "summary", "pc_release_date"})


def normalize_steam(
    steam: Mapping[str, Any], current: Mapping[str, Any]
) -> dict[str, Any]:
    """Return safe, non-empty Steam updates without changing selected media."""
    steam_id = _positive_int(steam.get("steam_id"))
    if steam_id is None:
        return {}

    existing_metadata = _mapping(current.get("steam_metadata"))
    manual_metadata = _mapping(current.get("manual_metadata"))
    steam_fields = _string_set(existing_metadata.get("fields"))
    metadata = _provenance(steam.get("steam_metadata"), steam_id, steam_fields)
    updates: dict[str, Any] = {"steam_id": steam_id, "steam_metadata": metadata}

    metadata_current = _mapping(current.get("metadata"))
    fallback_fields = _string_set(
        _mapping(steam.get("steam_metadata")).get("fallback_fields")
    )
    values = {
        "name": _non_empty_string(steam.get("name")),
        "summary": _non_empty_string(steam.get("summary")),
        "main_developer": _first_string(
            steam.get("main_developer"),
            _mapping(steam.get("steam_metadata")).get("developers"),
        ),
        "publishers": _string_list(
            steam.get("publishers"),
            _mapping(steam.get("steam_metadata")).get("publishers"),
        ),
        "pc_release_date": _release_timestamp(
            steam.get("pc_release_date"),
            _mapping(steam.get("steam_metadata")).get("release_date"),
        ),
    }
    applied_fields: list[str] = []
    structured_updates: dict[str, Any] = {}
    for field, value in values.items():
        if value is None or _is_manual(manual_metadata, field):
            continue
        current_value = (
            current.get(field)
            if field in {"name", "summary"}
            else metadata_current.get(field, current.get(field))
        )
        if _can_replace(
            current_value,
            field in steam_fields
            or (field in {"name", "summary"} and field not in fallback_fields),
        ):
            if field in {"name", "summary"}:
                updates[field] = value
            else:
                structured_updates[field] = value
            applied_fields.append(field)

    if applied_fields:
        metadata["fields"] = sorted(steam_fields | set(applied_fields))
    elif steam_fields:
        metadata["fields"] = sorted(steam_fields)

    if structured_updates:
        updates["metadata"] = structured_updates

    media = _media(steam)
    if media:
        updates["media"] = media
    return updates


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _non_empty_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _first_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, list):
            value = next((item for item in value if _non_empty_string(item)), None)
        if result := _non_empty_string(value):
            return result
    return None


def _string_list(*values: object) -> list[str] | None:
    for value in values:
        if not isinstance(value, list):
            continue
        result = [item.strip() for item in value if _non_empty_string(item)]
        if result:
            return result
    return None


def _release_timestamp(*values: object) -> int | None:
    for value in values:
        timestamp = _positive_int(value)
        if timestamp is not None:
            return timestamp
        date = _mapping(value).get("date") if isinstance(value, Mapping) else value
        if not isinstance(date, str) or not date.strip():
            continue
        for date_format in ("%d %b, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                return int(
                    datetime.strptime(date.strip(), date_format)
                    .replace(tzinfo=UTC)
                    .timestamp()
                )
            except ValueError:
                continue
    return None


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str) and item in DISPLAY_FIELDS}


def _provenance(value: object, steam_id: int, fields: set[str]) -> dict[str, Any]:
    metadata = _mapping(value)
    metadata.update({"app_id": steam_id, "source": "storefront"})
    if fields:
        metadata["fields"] = sorted(fields)
    else:
        metadata.pop("fields", None)
    return metadata


def _is_manual(metadata: Mapping[str, Any], field: str) -> bool:
    return field in MANUAL_FIELDS and bool(metadata.get(field))


def _can_replace(current: object, steam_owned: bool) -> bool:
    if isinstance(current, str):
        return not current.strip() or steam_owned
    if isinstance(current, list):
        return not current or steam_owned
    return current is None or steam_owned


def _media(steam: Mapping[str, Any]) -> dict[str, list[str]]:
    media: dict[str, list[str]] = {}
    if cover := _non_empty_string(steam.get("url_cover")):
        media["cover"] = [cover]
    screenshots = _string_list(steam.get("url_screenshots"))
    if screenshots:
        media["screenshots"] = screenshots
    return media
