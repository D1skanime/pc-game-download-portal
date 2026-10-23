"""Serialized scan configuration mutations with durable publication."""

import copy
import fcntl
import os
import re
import stat
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from config import STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG
from exceptions.config_exceptions import ConfigNotWritableException

if TYPE_CHECKING:
    from config.config_manager import ConfigManager

_MUTATION_LOCK = threading.RLock()
_LOCALE = re.compile(r"^[a-z]{2,3}(?:[-_][a-z0-9]{2,8})*$")


class ScanLanguageConflict(ValueError):
    pass


def normalize_language(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if value in STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG:
        return STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG[value]
    if len(value) > 35 or not _LOCALE.fullmatch(value):
        return None
    base = re.split("[-_]", value, maxsplit=1)[0]
    return base if base in STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG.values() else None


def _persist(path: Path, raw: dict) -> None:
    # Serialization must finish before opening any replacement file.
    content = yaml.dump(raw)
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, delete=False
        ) as file:
            temporary = Path(file.name)
            os.fchmod(file.fileno(), mode)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _mutate(manager: "ConfigManager", change: Callable[[dict], None]) -> list[str]:
    path = Path(manager.config_file)
    with _MUTATION_LOCK:
        try:
            if not manager._config_file_writable or not path.stat().st_mode & 0o222:
                raise ConfigNotWritableException
            with path.with_name(path.name + ".lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                with path.open() as file:
                    raw = yaml.safe_load(file) or {}
                if not isinstance(raw, dict):
                    raise ValueError("invalid_config_mapping")
                candidate = object.__new__(type(manager))
                candidate.__dict__.update(copy.deepcopy(manager.__dict__))
                change(raw)
                candidate._raw_config = raw
                candidate._parse_config()
                candidate._validate_config()
                _persist(path, raw)
                manager.__dict__.update(candidate.__dict__)
                return list(candidate.config.SCAN_LANGUAGE_PRIORITY)
        except (OSError, yaml.YAMLError) as error:
            raise ConfigNotWritableException from error


def update_language(
    manager: "ConfigManager", selected: list[str], expected: list[str]
) -> list[str]:
    def change(raw: dict) -> None:
        priority = raw.setdefault("scan", {}).setdefault("priority", {})
        current = priority.get("language", ["en"])
        if current != expected:
            raise ScanLanguageConflict("stale_language_priority")
        first = next(
            (code for value in selected if (code := normalize_language(value))), "en"
        )
        priority["language"] = list(
            dict.fromkeys(
                [
                    first,
                    "en",
                    *(code for value in current if (code := normalize_language(value))),
                ]
            )
        )

    return _mutate(manager, change)


def update_scan_settings(manager: "ConfigManager", **settings: Any) -> None:
    def change(raw: dict) -> None:
        scan = raw.setdefault("scan", {})
        priority = scan.setdefault("priority", {})
        for key in ("metadata", "artwork", "region", "language"):
            priority[key] = list(settings[key + "_priority"])
        for key in ("cover", "screenshot", "manual"):
            value = settings["artwork_overrides"].get(key)
            if value is None:
                priority.pop(key, None)
            else:
                priority[key] = list(value)
        scan["media"] = list(settings["media"])
        gamelist = scan.setdefault("gamelist", {})
        gamelist["export"] = settings["gamelist_export"]
        gamelist.setdefault("media", {}).update(
            thumbnail=settings["gamelist_thumbnail"], image=settings["gamelist_image"]
        )
        scan.setdefault("pegasus", {})["export"] = settings["pegasus_export"]

    _mutate(manager, change)
