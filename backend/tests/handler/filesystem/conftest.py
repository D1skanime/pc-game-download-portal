"""Explicit read-only legacy library context for filesystem adapter tests."""

from copy import deepcopy
from importlib import import_module
from pathlib import Path

import pytest

from handler import filesystem
from handler.filesystem import platforms_handler
from handler.filesystem.storage_policy import _create_external_descriptor


@pytest.fixture
def legacy_library(monkeypatch: pytest.MonkeyPatch, request):
    root = Path(__file__).resolve().parents[3] / "romm_test/library"
    assert (root / "n64/roms/Paper Mario (USA).z64").is_file()
    monkeypatch.setattr(
        filesystem, "legacy_external_storage", _create_external_descriptor(1, root)
    )
    config_module = import_module("config.config_manager")
    monkeypatch.setattr(
        config_module.config_manager,
        "config",
        deepcopy(config_module.config_manager.config),
    )
    for module in (
        config_module,
        platforms_handler,
        request.module,
    ):
        monkeypatch.setattr(module, "LIBRARY_BASE_PATH", str(root))
    return root
