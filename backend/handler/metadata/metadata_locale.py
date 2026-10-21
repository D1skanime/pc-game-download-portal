"""Capture one provider locale in the existing durable request envelope."""

from copy import deepcopy
from itertools import islice

from config.config_manager import config_manager as cm
from config.scan_language import normalize_language


def effective_metadata_locale(preference: object = None) -> str:
    explicit = normalize_language(preference)
    if explicit is not None:
        return explicit
    priorities = cm.get_config().SCAN_LANGUAGE_PRIORITY
    return next(
        (
            locale
            for value in islice(priorities, 64)
            if (locale := normalize_language(value))
        ),
        "en",
    )


def capture_metadata_locale(envelope: dict) -> dict:
    captured = deepcopy(envelope)
    policy = dict(captured.get("request", captured.get("policies", {})))
    commands = captured.get("commands", [])
    scheduled = bool(commands) and all(
        command.get("trigger") == "scheduled" for command in commands
    )
    policy["metadata_locale"] = effective_metadata_locale(
        None if scheduled else policy.get("metadata_locale")
    )
    captured["request"] = policy
    return captured


def ensure_metadata_locale(envelope: dict) -> dict:
    policy = envelope.get("request", {})
    locale = policy.get("metadata_locale")
    if locale and normalize_language(locale) == locale:
        return envelope
    return capture_metadata_locale(envelope)
