from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from endpoints.storage_policy import authorize_api_storage_operation
from handler.filesystem import legacy_external_storage, storage_composition
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """This policy contract suite is database free."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override shared database cleanup for policy-only evidence."""


TASK_1_ROUTE_MATRIX = (
    ("roms/upload.py", "start_chunked_upload", "UPLOAD", "legacy_external_storage"),
    ("roms/upload.py", "complete_chunked_upload", "UPLOAD", "legacy_external_storage"),
    ("roms/files.py", "delete_rom_file", "DELETE", "legacy_external_storage"),
    ("roms/__init__.py", "convert_rom_to_folder", "EXTRACT", "legacy_external_storage"),
    ("roms/__init__.py", "delete_roms", "DELETE", "legacy_external_storage"),
    (
        "roms/manual.py",
        "add_rom_manual_file",
        "SIDECAR_WRITE",
        "legacy_external_storage",
    ),
    ("roms/manual.py", "delete_rom_manual_file", "DELETE", "legacy_external_storage"),
    (
        "roms/screenshot.py",
        "add_rom_screenshots",
        "COVER_WRITE",
        "legacy_external_storage",
    ),
    (
        "roms/screenshot.py",
        "delete_rom_screenshot",
        "DELETE",
        "legacy_external_storage",
    ),
    (
        "roms/soundtrack.py",
        "add_rom_soundtracks",
        "SIDECAR_WRITE",
        "legacy_external_storage",
    ),
    (
        "roms/soundtrack.py",
        "delete_rom_soundtrack",
        "DELETE",
        "legacy_external_storage",
    ),
)


def _function_calls(relative_file: str, function_name: str) -> set[str]:
    source = Path("endpoints", relative_file).read_text()
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    return {
        ast.unparse(node) for node in ast.walk(function) if isinstance(node, ast.Call)
    }


@pytest.mark.parametrize(
    ("relative_file", "function_name", "operation", "provider"),
    TASK_1_ROUTE_MATRIX,
)
def test_real_rom_mutation_routes_use_trusted_policy_provider(
    relative_file: str, function_name: str, operation: str, provider: str
) -> None:
    calls = _function_calls(relative_file, function_name)
    expected = (
        f"authorize_api_storage_operation(StorageOperation.{operation}, {provider})"
    )
    assert expected in calls


def test_external_api_denial_is_bounded_and_precedes_io(monkeypatch) -> None:
    io_tripwire = Mock(side_effect=AssertionError("filesystem I/O reached"))
    monkeypatch.setattr(Path, "stat", io_tripwire)
    monkeypatch.setattr(Path, "open", io_tripwire)

    with pytest.raises(HTTPException) as error:
        authorize_api_storage_operation(
            StorageOperation.UPLOAD, legacy_external_storage
        )

    assert error.value.status_code == 403
    assert error.value.detail == {
        "code": "external_storage_operation_denied",
        "operation": "upload",
        "storage_class": "external_read_only",
        "storage_id": "root:0",
    }
    assert "/romm" not in str(error.value.detail)
    io_tripwire.assert_not_called()


def test_caller_text_cannot_replace_provider_identity() -> None:
    caller_values = ("romm_owned", "/romm/resources", "root:999", "../assets")
    for caller_value in caller_values:
        with pytest.raises(HTTPException) as error:
            authorize_api_storage_operation(
                StorageOperation.DELETE,
                legacy_external_storage,
                caller_text=caller_value,
            )
        assert error.value.detail["storage_id"] == legacy_external_storage.storage_id
        assert caller_value not in str(error.value.detail)


def test_patch_uses_external_read_and_owned_temp_output() -> None:
    calls = _function_calls("roms/patch.py", "patch_rom")
    assert (
        "authorize_api_storage_operation(StorageOperation.READ, legacy_external_storage)"
        in calls
    )
    assert (
        "authorize_api_storage_operation(StorageOperation.PATCH, "
        "storage_composition.owned[OwnedStorageKind.TEMP])" in calls
    )


def test_owned_output_authorization_proceeds() -> None:
    descriptor = storage_composition.owned[OwnedStorageKind.TEMP]
    grant = authorize_api_storage_operation(StorageOperation.PATCH, descriptor)
    assert grant.storage is descriptor
    assert grant.operation is StorageOperation.PATCH


TASK_2_ROUTE_MATRIX = (
    (
        "saves.py",
        "add_save",
        "WRITE",
        "storage_composition.owned[OwnedStorageKind.ASSETS]",
    ),
    (
        "saves.py",
        "update_save",
        "OVERWRITE",
        "storage_composition.owned[OwnedStorageKind.ASSETS]",
    ),
    (
        "saves.py",
        "delete_saves",
        "DELETE",
        "storage_composition.owned[OwnedStorageKind.ASSETS]",
    ),
    (
        "states.py",
        "add_state",
        "WRITE",
        "storage_composition.owned[OwnedStorageKind.ASSETS]",
    ),
    (
        "states.py",
        "update_state",
        "OVERWRITE",
        "storage_composition.owned[OwnedStorageKind.ASSETS]",
    ),
    (
        "states.py",
        "delete_states",
        "DELETE",
        "storage_composition.owned[OwnedStorageKind.ASSETS]",
    ),
    (
        "collections.py",
        "add_collection",
        "COVER_WRITE",
        "storage_composition.owned[OwnedStorageKind.RESOURCES]",
    ),
    (
        "collections.py",
        "update_collection",
        "COVER_WRITE",
        "storage_composition.owned[OwnedStorageKind.RESOURCES]",
    ),
    (
        "collections.py",
        "delete_collection",
        "DELETE",
        "storage_composition.owned[OwnedStorageKind.RESOURCES]",
    ),
    ("firmware.py", "add_firmware", "UPLOAD", "legacy_external_storage"),
    ("firmware.py", "delete_firmware", "DELETE", "legacy_external_storage"),
    ("platform.py", "add_platform", "MKDIR", "legacy_external_storage"),
)


@pytest.mark.parametrize(
    ("relative_file", "function_name", "operation", "provider"),
    TASK_2_ROUTE_MATRIX,
)
def test_remaining_real_mutation_routes_use_trusted_policy_provider(
    relative_file: str, function_name: str, operation: str, provider: str
) -> None:
    calls = _function_calls(relative_file, function_name)
    expected = (
        f"authorize_api_storage_operation(StorageOperation.{operation}, {provider})"
    )
    assert expected in calls


def test_identity_form_cannot_supply_storage_classification() -> None:
    from endpoints.forms.identity import UserForm

    form = UserForm(
        username="caller",
        storage_class="romm_owned",
        storage_id="root:999",
        root_path="/romm/resources",
    )
    assert set(form.model_dump()) == {
        "username",
        "password",
        "email",
        "role",
        "enabled",
        "ra_username",
        "avatar",
        "ui_settings",
    }
