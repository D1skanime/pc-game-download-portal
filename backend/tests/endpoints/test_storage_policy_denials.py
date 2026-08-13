from __future__ import annotations

import ast
import hashlib
import stat
from inspect import unwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import HTTPException

from endpoints import firmware as firmware_endpoints
from endpoints import heartbeat as heartbeat_endpoints
from endpoints import roms as rom_endpoints
from endpoints.storage_policy import authorize_api_storage_operation
from handler.filesystem import legacy_external_storage, storage_composition
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation

TASK_1_ROUTE_MATRIX = (
    ("roms/upload.py", "start_chunked_upload", "UPLOAD", "legacy_external_storage"),
    ("roms/upload.py", "complete_chunked_upload", "UPLOAD", "legacy_external_storage"),
    ("roms/files.py", "delete_rom_file", "DELETE", "legacy_external_storage"),
    ("roms/__init__.py", "convert_rom_to_folder", "EXTRACT", "legacy_external_storage"),
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


def _authorization_is_guarded_by_non_empty_delete_list() -> bool:
    source = Path("endpoints", "firmware.py").read_text()
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "delete_firmware"
    )
    expected = (
        "authorize_api_storage_operation(StorageOperation.DELETE, "
        "legacy_external_storage)"
    )
    return any(
        ast.unparse(node.test) == "delete_from_fs"
        and expected
        in {ast.unparse(call) for call in ast.walk(node) if isinstance(call, ast.Call)}
        for node in ast.walk(function)
        if isinstance(node, ast.If)
    )


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


@pytest.mark.parametrize(
    "operation",
    [
        StorageOperation.CREATE,
        StorageOperation.UPLOAD,
        StorageOperation.WRITE,
        StorageOperation.OVERWRITE,
        StorageOperation.RENAME,
        StorageOperation.MOVE,
        StorageOperation.COPY,
        StorageOperation.DELETE,
        StorageOperation.EXTRACT,
        StorageOperation.PATCH,
        StorageOperation.MKDIR,
        StorageOperation.SIDECAR_WRITE,
        StorageOperation.COVER_WRITE,
    ],
)
def test_phase6_external_mutations_are_denied_before_io(
    monkeypatch, operation: StorageOperation
) -> None:
    io_tripwire = Mock(side_effect=AssertionError("filesystem I/O reached"))
    monkeypatch.setattr(Path, "stat", io_tripwire)
    monkeypatch.setattr(Path, "open", io_tripwire)

    with pytest.raises(HTTPException) as error:
        authorize_api_storage_operation(operation, legacy_external_storage)

    assert error.value.status_code == 403
    assert error.value.detail["operation"] == operation.value
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


OWNED_DELETE_ROUTE_MATRIX = (
    (
        "screenshots.py",
        "delete_screenshot",
        "storage_composition.owned[OwnedStorageKind.ASSETS]",
    ),
    (
        "roms/manual.py",
        "delete_rom_manuals",
        "storage_composition.owned[OwnedStorageKind.RESOURCES]",
    ),
)


@pytest.mark.parametrize(
    ("relative_file", "function_name", "provider"), OWNED_DELETE_ROUTE_MATRIX
)
def test_owned_deletions_authorize_the_exact_typed_descriptor_before_io(
    relative_file: str, function_name: str, provider: str
) -> None:
    calls = _function_calls(relative_file, function_name)
    assert (
        f"authorize_api_storage_operation(StorageOperation.DELETE, {provider})" in calls
    )


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


@pytest.mark.asyncio
async def test_firmware_catalog_removal_never_requests_external_delete(
    monkeypatch,
) -> None:
    firmware = SimpleNamespace(
        id=7,
        platform_id=3,
        file_name="bios.bin",
        file_path="firmware",
        platform=SimpleNamespace(slug="pc"),
    )
    permissions = Mock()
    permissions.can_see_platform.return_value = True
    db_delete = Mock()
    fs_delete = Mock(side_effect=AssertionError("external deletion reached"))
    monkeypatch.setattr(
        firmware_endpoints, "get_permissions", lambda _request: permissions
    )
    monkeypatch.setattr(firmware_endpoints, "assert_can", Mock())
    monkeypatch.setattr(
        firmware_endpoints.db_firmware_handler,
        "get_firmware",
        Mock(return_value=firmware),
    )
    monkeypatch.setattr(
        firmware_endpoints.db_firmware_handler, "delete_firmware", db_delete
    )
    monkeypatch.setattr(
        firmware_endpoints.fs_firmware_handler, "remove_file", fs_delete
    )

    result = await unwrap(firmware_endpoints.delete_firmware)(
        request=Mock(), firmware=[firmware.id], delete_from_fs=[]
    )

    assert result == {"successful_items": 1, "failed_ids": [], "errors": []}
    db_delete.assert_called_once_with(firmware.id)
    fs_delete.assert_not_called()
    assert _authorization_is_guarded_by_non_empty_delete_list()


def _source_manifest(root: Path) -> tuple[tuple[object, ...], ...]:
    records = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        info = path.lstat()
        kind = "symlink" if path.is_symlink() else "file" if path.is_file() else "dir"
        digest = ""
        target = ""
        if kind == "file":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        elif kind == "symlink":
            target = path.readlink().as_posix()
        records.append(
            (
                path.relative_to(root).as_posix(),
                kind,
                stat.S_IMODE(info.st_mode),
                info.st_size,
                digest,
                target,
            )
        )
    return tuple(records)


@pytest.mark.asyncio
async def test_crafted_firmware_delete_is_replay_safe_and_source_immutable(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "external"
    source.mkdir()
    firmware_file = source / "bios.bin"
    firmware_file.write_bytes(b"immutable firmware")
    (source / "alias.bin").symlink_to(firmware_file.name)
    before = _source_manifest(source)

    db_read = Mock(side_effect=AssertionError("database lookup reached"))
    db_delete = Mock(side_effect=AssertionError("database mutation reached"))
    fs_delete = Mock(side_effect=AssertionError("filesystem mutation reached"))
    monkeypatch.setattr(firmware_endpoints.db_firmware_handler, "get_firmware", db_read)
    monkeypatch.setattr(
        firmware_endpoints.db_firmware_handler, "delete_firmware", db_delete
    )
    monkeypatch.setattr(
        firmware_endpoints.fs_firmware_handler, "remove_file", fs_delete
    )

    for firmware_ids in ([1], [1], [1, 2], [999_999]):
        with pytest.raises(HTTPException) as error:
            await unwrap(firmware_endpoints.delete_firmware)(
                request=Mock(),
                firmware=firmware_ids,
                delete_from_fs=[firmware_ids[0]],
            )
        assert error.value.status_code == 403
        assert error.value.detail == {
            "code": "external_storage_operation_denied",
            "operation": "delete",
            "storage_class": "external_read_only",
            "storage_id": "root:0",
        }
        assert str(source) not in str(error.value.detail)

    assert _source_manifest(source) == before
    db_read.assert_not_called()
    db_delete.assert_not_called()
    fs_delete.assert_not_called()


def _setup_request() -> SimpleNamespace:
    return SimpleNamespace(auth=SimpleNamespace(scopes=[]))


@pytest.mark.asyncio
async def test_empty_setup_platform_request_is_neutral_and_path_free(
    monkeypatch,
) -> None:
    detect = Mock(side_effect=AssertionError("structure detection reached"))
    create_structure = Mock(side_effect=AssertionError("structure creation reached"))
    add_platform = Mock(side_effect=AssertionError("platform creation reached"))
    authorize = Mock(side_effect=AssertionError("authorization reached"))
    monkeypatch.setattr(
        heartbeat_endpoints.db_user_handler,
        "get_admin_users",
        Mock(return_value=[]),
    )
    monkeypatch.setattr(
        heartbeat_endpoints.fs_platform_handler,
        "detect_library_structure",
        detect,
    )
    monkeypatch.setattr(
        heartbeat_endpoints.fs_platform_handler,
        "create_library_structure",
        create_structure,
    )
    monkeypatch.setattr(
        heartbeat_endpoints.fs_platform_handler,
        "add_platform",
        add_platform,
    )
    monkeypatch.setattr(
        heartbeat_endpoints,
        "authorize_api_storage_operation",
        authorize,
        raising=False,
    )

    result = await unwrap(heartbeat_endpoints.create_setup_platforms)(
        request=_setup_request(),
        platform_slugs=[],
    )

    assert result == {
        "success": True,
        "created_count": 0,
        "message": "No platforms selected",
    }
    authorize.assert_not_called()
    detect.assert_not_called()
    create_structure.assert_not_called()
    add_platform.assert_not_called()


@pytest.mark.asyncio
async def test_setup_platform_authorizes_create_and_mkdir_before_detection(
    monkeypatch,
) -> None:
    denial = HTTPException(
        status_code=403,
        detail={"code": "external_storage_operation_denied"},
    )
    authorize = Mock(side_effect=[None, denial])
    detect = Mock(side_effect=AssertionError("structure detection reached"))
    monkeypatch.setattr(
        heartbeat_endpoints.db_user_handler,
        "get_admin_users",
        Mock(return_value=[]),
    )
    monkeypatch.setattr(
        heartbeat_endpoints,
        "authorize_api_storage_operation",
        authorize,
        raising=False,
    )
    monkeypatch.setattr(
        heartbeat_endpoints.fs_platform_handler,
        "detect_library_structure",
        detect,
    )

    with pytest.raises(HTTPException) as error:
        await unwrap(heartbeat_endpoints.create_setup_platforms)(
            request=_setup_request(),
            platform_slugs=["pc"],
        )

    assert error.value is denial
    assert authorize.call_args_list == [
        call(StorageOperation.CREATE, legacy_external_storage),
        call(StorageOperation.MKDIR, legacy_external_storage),
    ]
    detect.assert_not_called()


@pytest.mark.asyncio
async def test_crafted_setup_platform_requests_are_replay_safe_and_immutable(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "external"
    source.mkdir()
    (source / "pc").mkdir()
    marker = source / "pc" / "game.bin"
    marker.write_bytes(b"immutable game")
    (source / "alias").symlink_to("pc", target_is_directory=True)
    before = _source_manifest(source)
    detect = Mock(side_effect=AssertionError("structure detection reached"))
    create_structure = Mock(side_effect=AssertionError("structure creation reached"))
    add_platform = Mock(side_effect=AssertionError("platform creation reached"))
    monkeypatch.setattr(
        heartbeat_endpoints.db_user_handler,
        "get_admin_users",
        Mock(return_value=[]),
    )
    monkeypatch.setattr(
        heartbeat_endpoints.fs_platform_handler,
        "detect_library_structure",
        detect,
    )
    monkeypatch.setattr(
        heartbeat_endpoints.fs_platform_handler,
        "create_library_structure",
        create_structure,
    )
    monkeypatch.setattr(
        heartbeat_endpoints.fs_platform_handler,
        "add_platform",
        add_platform,
    )

    for slugs in (["pc"], ["pc"], ["../escape"], [str(source / "alias")]):
        with pytest.raises(HTTPException) as error:
            await unwrap(heartbeat_endpoints.create_setup_platforms)(
                request=_setup_request(),
                platform_slugs=slugs,
            )
        assert error.value.status_code == 403
        assert error.value.detail == {
            "code": "external_storage_operation_denied",
            "operation": "create",
            "storage_class": "external_read_only",
            "storage_id": "root:0",
        }
        assert str(source) not in str(error.value.detail)

    assert _source_manifest(source) == before
    detect.assert_not_called()
    create_structure.assert_not_called()
    add_platform.assert_not_called()


def _rom_update_fixture() -> SimpleNamespace:
    return SimpleNamespace(
        id=41,
        platform_id=2,
        fs_name="game.bin",
        fs_path="pc",
        files=[],
        igdb_id=None,
        sgdb_id=None,
        moby_id=None,
        ss_id=None,
        ra_id=None,
        launchbox_id=None,
        hasheous_id=None,
        tgdb_id=None,
        flashpoint_id=None,
        hltb_id=None,
        libretro_id=None,
        igdb_metadata={},
        moby_metadata={},
        ss_metadata={},
        ra_metadata={},
        launchbox_metadata={},
        hasheous_metadata={},
        flashpoint_metadata={},
        hltb_metadata={},
        url_screenshots=[],
        name="Game",
        summary="Original",
        name_sort_key="Game",
        url_cover="",
        url_manual="",
    )


def _install_update_rom_tripwires(
    monkeypatch: pytest.MonkeyPatch,
    rom: SimpleNamespace,
    effects: list[str],
) -> None:
    monkeypatch.setattr(
        rom_endpoints.db_rom_handler,
        "get_rom",
        Mock(return_value=rom),
    )
    monkeypatch.setattr(rom_endpoints, "assert_rom_visible", Mock())
    monkeypatch.setattr(
        rom_endpoints.db_rom_handler,
        "update_rom",
        Mock(side_effect=lambda *_args, **_kwargs: effects.append("database")),
    )
    for name in (
        "remove_cover",
        "store_artwork",
        "get_cover",
        "get_manual",
        "get_rom_screenshots",
        "store_ra_badge",
        "remove_media_resources_path",
        "store_media_file",
    ):
        monkeypatch.setattr(
            rom_endpoints.fs_resource_handler,
            name,
            AsyncMock(side_effect=AssertionError("owned resource mutation reached")),
        )
    monkeypatch.setattr(
        rom_endpoints.fs_rom_handler,
        "rename_fs_rom",
        AsyncMock(side_effect=AssertionError("external rename reached")),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "crafted_name",
    [
        "renamed.bin",
        "../escape.bin",
        "alias.bin",
        "occupied.bin",
    ],
)
async def test_update_rom_changed_fs_name_denies_before_partial_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    crafted_name: str,
) -> None:
    source = tmp_path / "external"
    owned = tmp_path / "resources"
    source.mkdir()
    owned.mkdir()
    (source / "game.bin").write_bytes(b"immutable source")
    (source / "occupied.bin").write_bytes(b"collision")
    (source / "alias.bin").symlink_to("game.bin")
    (owned / "cover.png").write_bytes(b"immutable owned")
    source_before = _source_manifest(source)
    owned_before = _source_manifest(owned)

    rom = _rom_update_fixture()
    effects: list[str] = []
    _install_update_rom_tripwires(monkeypatch, rom, effects)
    real_authorize = rom_endpoints.authorize_api_storage_operation

    def record_authorization(operation, storage):
        effects.append("authorize:" + operation.value)
        return real_authorize(operation, storage)

    monkeypatch.setattr(
        rom_endpoints,
        "authorize_api_storage_operation",
        record_authorization,
    )

    form = rom_endpoints.RomUpdateForm(
        fs_name=crafted_name,
        name="Updated",
        url_cover="https://example.invalid/cover.png",
        url_manual="https://example.invalid/manual.pdf",
        raw_manual_metadata='{"languages":["en"]}',
    )
    for _ in range(2):
        with pytest.raises(HTTPException) as error:
            await unwrap(rom_endpoints.update_rom)(
                request=Mock(),
                id=rom.id,
                form_data=form,
                artwork=None,
                remove_cover=True,
                unmatch_metadata=False,
            )
        assert error.value.status_code == 403
        assert error.value.detail == {
            "code": "external_storage_operation_denied",
            "operation": "rename",
            "storage_class": "external_read_only",
            "storage_id": "root:0",
        }
        assert str(source) not in str(error.value.detail)

    assert effects == ["authorize:rename", "authorize:rename"]
    assert _source_manifest(source) == source_before
    assert _source_manifest(owned) == owned_before
    rom_endpoints.db_rom_handler.update_rom.assert_not_called()
    rom_endpoints.fs_rom_handler.rename_fs_rom.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_rom_same_fs_name_keeps_metadata_and_owned_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rom = _rom_update_fixture()
    db_update = Mock()
    authorize = Mock(side_effect=AssertionError("rename authorization reached"))
    monkeypatch.setattr(
        rom_endpoints.db_rom_handler,
        "get_rom",
        Mock(return_value=rom),
    )
    monkeypatch.setattr(rom_endpoints.db_rom_handler, "update_rom", db_update)
    monkeypatch.setattr(
        rom_endpoints.db_rom_handler,
        "invalidate_filter_values_cache",
        Mock(),
    )
    monkeypatch.setattr(rom_endpoints, "refresh_affected_smart_collections", Mock())
    monkeypatch.setattr(rom_endpoints, "assert_rom_visible", Mock())
    monkeypatch.setattr(
        rom_endpoints,
        "authorize_api_storage_operation",
        authorize,
    )
    monkeypatch.setattr(
        rom_endpoints.fs_resource_handler,
        "get_cover",
        AsyncMock(return_value=("cover-small.png", "cover-big.png")),
    )
    monkeypatch.setattr(
        rom_endpoints.fs_resource_handler,
        "get_manual",
        AsyncMock(return_value="manual.pdf"),
    )
    monkeypatch.setattr(
        rom_endpoints.meta_playmatch_handler,
        "is_manual_match",
        Mock(return_value=False),
    )
    monkeypatch.setattr(
        rom_endpoints.DetailedRomSchema,
        "from_orm_with_request",
        Mock(return_value="updated"),
    )

    result = await unwrap(rom_endpoints.update_rom)(
        request=Mock(),
        id=rom.id,
        form_data=rom_endpoints.RomUpdateForm(
            fs_name=rom.fs_name,
            name="Updated",
        ),
        artwork=None,
        remove_cover=False,
        unmatch_metadata=False,
    )

    assert result == "updated"
    authorize.assert_not_called()
    db_update.assert_called_once()
    assert db_update.call_args.args[1]["name"] == "Updated"
    assert db_update.call_args.args[1]["fs_name"] == rom.fs_name
    rom_endpoints.fs_resource_handler.get_cover.assert_awaited_once()
    rom_endpoints.fs_resource_handler.get_manual.assert_awaited_once()
