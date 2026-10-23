"""Actual scan owners offer durable identities and retain captured provider locale."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from tests.handler.test_scan_inventory_state import bound_game as bound_game
from tests.handler.test_scan_inventory_state import clear_inventory as clear_inventory
from tests.handler.test_scan_inventory_state import (
    inventory_attempt as inventory_attempt,
)
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem.roms_handler import FSRom
from handler.scan_operation_checkpoint import bind_checkpoint_command
from handler.scan_operation_recovery import decode_command
from handler.scan_retry_execution import RetryCoordinator, bind_retry_coordinator
from models.rom import Rom

pytest_plugins = ["tests.handler.test_scan_operations"]


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["steam", "ss"])
async def test_post_merge_observation_offers_durable_identity(
    monkeypatch, bound_game, inventory_attempt, provider
):
    from handler import scan_description_retry as descriptions
    from handler import scan_retry_execution as execution
    from handler.scan_pc_automation_observation import observe_pc_automation
    from handler.windows_quick_execution import bind_windows_quick

    binding, command_data = bound_game
    with sync_session.begin() as session:
        row = session.get(Rom, binding.rom_id)
        row.platform.slug = "win" if provider == "steam" else "snes"
        row.manual_metadata = {"descriptions": {"en": "Protected English"}}
    durable = db_rom_handler.get_rom(binding.rom_id)
    scanned = SimpleNamespace(steam_id=None, ss_id=None)
    monkeypatch.setattr(execution, "configured_sources", lambda policy: [provider])
    monkeypatch.setattr(
        descriptions, "get_description_component_page", lambda *a, **kw: ([], None)
    )
    coordinator = RetryCoordinator(
        {
            "apis": [provider],
            "metadata_locale": "fr-FR",
            "description_languages": ["en"],
        }
    )
    command = decode_command(command_data["commands"][0])

    async def automation(platform, scanned, old, newly_added):
        # Model the normal durable IGDB/automation merge, not an ephemeral result.
        db_rom_handler.update_rom(old.id, {provider + "_id": 10})

    with bind_scan_write_context(context(inventory_attempt)), bind_checkpoint_command(
        command
    ), bind_retry_coordinator(coordinator), bind_windows_quick(None):
        await observe_pc_automation(
            automation, durable.platform, scanned, durable, True
        )
        assert len(coordinator.candidates) == 1
        candidate = coordinator.candidates[0]
        assert candidate.identity.purpose == "description"
        assert candidate.identity.provider == provider
        assert candidate.identity.locale == "fr"
        assert candidate.identity.query == "descriptions:v1:10:parent"
        work = coordinator.work[candidate.identity.game_key]
        assert work.quick.binding.game_relative_path == "Collection/Game"
        assert work.quick.binding.rom_incarnation == binding.rom_incarnation
        assert await coordinator.revalidate(work, purpose="description")
        from dataclasses import replace

        stale = replace(
            work,
            quick=SimpleNamespace(
                binding=replace(work.quick.binding, game_relative_path="Other"),
                before=None,
            ),
        )
        assert not await coordinator.revalidate(stale, purpose="description")

    current = db_rom_handler.get_rom(durable.id)
    assert getattr(current, provider + "_id") == 10
    assert current.manual_metadata == {"descriptions": {"en": "Protected English"}}
    target = coordinator.description_targets[candidate.identity.key]
    assert target.updated_at == current.updated_at


@pytest.mark.asyncio
@pytest.mark.parametrize("current", [True, False])
async def test_non_inventory_description_revalidates_binding_without_files(
    monkeypatch, current
):
    from tests.handler.test_windows_quick_execution import binding

    from handler import scan_description_retry as descriptions
    from handler import scan_retry_execution as execution
    from handler.filesystem.roms_handler import FSRomsHandler
    from handler.storage.read_context import MappingReadContext

    bound = binding()
    rom = SimpleNamespace(incarnation_token=bound.rom_incarnation, platform_slug="win")
    monkeypatch.setattr(execution, "check_worker_boundary", lambda: None)
    monkeypatch.setattr(execution.db_rom_handler, "get_rom", lambda _: rom)
    monkeypatch.setattr(MappingReadContext, "validate", lambda _: object())
    authority = Mock(return_value=current)
    monkeypatch.setattr(descriptions, "description_binding_current", authority)
    filesystem = Mock(side_effect=AssertionError("text repair must not inspect files"))
    monkeypatch.setattr(FSRomsHandler, "for_mapping", filesystem)
    work = SimpleNamespace(rom_id=3, quick=SimpleNamespace(binding=bound, before=None))
    coordinator = RetryCoordinator({"apis": ["steam"], "metadata_locale": "de"})
    assert await coordinator.revalidate(work, purpose="description") is current
    authority.assert_called_once_with(bound)
    filesystem.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scan_type", ["new_platforms", "quick", "update", "unmatched", "complete", "hashes"]
)
@pytest.mark.parametrize("lookup", ["id", "hash", "name"])
async def test_normal_scan_screenscraper_uses_captured_locale(
    monkeypatch, scan_type, lookup
):
    from tests.handler.test_scan_handler import _igdb_scan_fixture

    from handler import scan_handler as scanner
    from handler.scan_handler import ScanType

    platform, rom = _igdb_scan_fixture(platform_slug="snes")
    platform.ss_id = 4
    rom.ss_id = 10 if lookup == "id" else None
    seen = []

    def result(kwargs):
        seen.append(kwargs.get("metadata_locale"))
        return {
            "ss_id": 10,
            "summary": "French" if kwargs.get("metadata_locale") == "fr" else "English",
            "ss_metadata": {
                "text_variants": {"fr": {"summary": "French", "source_language": "fr"}}
            },
        }

    async def by_id(*args, **kwargs):
        return result(kwargs)

    async def by_hash(*args, **kwargs):
        return (result(kwargs), False) if lookup == "hash" else ({"ss_id": None}, False)

    async def by_name(*args, **kwargs):
        return result(kwargs)

    monkeypatch.setattr(scanner, "require_scan_write_context", lambda: None)
    monkeypatch.setattr(scanner.db_rom_handler, "add_rom", lambda row: row)
    monkeypatch.setattr(scanner, "preserve_current_scan_media", lambda row: None)
    monkeypatch.setattr(scanner.db_rom_handler, "rom_files_for_rom_id", lambda _: [])
    monkeypatch.setattr(scanner.meta_playmatch_handler, "is_enabled", lambda: False)
    monkeypatch.setattr(scanner.meta_ss_handler, "is_enabled", lambda: True)
    monkeypatch.setattr(scanner.meta_ss_handler, "get_rom_by_id", by_id)
    monkeypatch.setattr(scanner.meta_ss_handler, "lookup_rom", by_hash)
    monkeypatch.setattr(scanner.meta_ss_handler, "get_rom", by_name)
    monkeypatch.setattr(scanner.fs_rom_handler, "get_pico8_cover_url", lambda _: None)
    fs_rom: FSRom = {
        "fs_name": "Game",
        "flat": True,
        "nested": False,
        "files": [],
        "crc_hash": "",
        "md5_hash": "",
        "sha1_hash": "",
        "ra_hash": "",
    }
    # UPDATE exercises stored ID; other modes exercise ordinary hash/name discovery.
    mode = ScanType.UPDATE if lookup == "id" else ScanType(scan_type)
    result_rom = await scanner.scan_rom(
        mode,
        platform,
        rom,
        fs_rom,
        ["ss"],
        newly_added=lookup != "id",
        metadata_locale="fr",
        metadata_only=True,
        playmatch_enabled=False,
    )
    assert seen == ["fr"]
    assert result_rom.summary == "French"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["steam", "ss"])
@pytest.mark.parametrize(
    "trigger,mode",
    [
        ("manual", "new_platforms"),
        ("manual", "quick"),
        ("manual", "update"),
        ("manual", "unmatched"),
        ("manual", "complete"),
        ("manual", "hashes"),
        ("scheduled", "quick"),
    ],
)
async def test_accepted_worker_drains_new_durable_id_once(
    admin_user, bound_game, monkeypatch, provider, trigger, mode
):
    from copy import deepcopy

    from tests.handler.test_metadata_locale import queued

    from config.config_manager import config_manager as cm
    from endpoints.sockets import scan
    from handler import metadata
    from handler import scan_operation_worker as worker
    from handler import scan_retry_execution as execution
    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from handler.metadata import pc_steam_enrichment
    from handler.scan_pc_automation_observation import observe_pc_automation
    from tasks import scan_operation_dispatch as dispatch
    from tasks.scheduled import scan_library
    from utils.scan_provider_observation import _dispatch

    bound, command_data = bound_game
    with sync_session.begin() as session:
        row = session.get(Rom, bound.rom_id)
        row.platform.slug = "win" if provider == "steam" else "snes"
        row.manual_metadata = {"descriptions": {"en": "Protected English"}}
        row.summary = "Legacy summary"
    config = deepcopy(cm.get_config())
    config.SCAN_LANGUAGE_PRIORITY = ["fr", "en"]
    monkeypatch.setattr(cm, "get_config", lambda: config)
    monkeypatch.setattr(
        metadata.meta_steam_handler, "is_enabled", lambda: provider == "steam"
    )
    monkeypatch.setattr(
        metadata.meta_ss_handler, "is_enabled", lambda: provider == "ss"
    )
    monkeypatch.setattr(
        execution,
        "configured_sources",
        lambda policy: [item for item in [provider] if item in policy.get("apis", [])],
    )
    command_data = deepcopy(command_data)
    command_data["commands"][0].update(trigger=trigger, scan_type=mode)
    repo = DBScanOperationsHandler()
    if trigger == "scheduled":
        monkeypatch.setattr(scan_library, "ENABLE_SCHEDULED_RESCAN", True)
        monkeypatch.setattr(
            scan_library,
            "mapping_scan_commands",
            lambda *a, **kw: [decode_command(command_data["commands"][0])],
        )
        monkeypatch.setattr(dispatch, "dispatch_operation", lambda *a, **kw: False)
        result = await scan_library.scan_library_task.run()
        accepted = repo.get_by_id(result["operation_id"], admin_user.id)
    else:
        accepted = repo.accept(
            admin_user.id,
            "description-worker",
            {
                "commands": command_data["commands"],
                "request": {
                    "apis": [provider],
                    "metadata_locale": "fr",
                    "metadata_only": True,
                },
            },
        )
    ready = queued(repo, accepted)
    config.SCAN_LANGUAGE_PRIORITY = ["de", "en"]
    observed = []
    mapping_calls = []
    finalizations = []

    async def automation(platform, scanned, durable, newly_added):
        db_rom_handler.update_rom(durable.id, {provider + "_id": 10})

    def completed(durable):
        finalizations.append(durable.id)
        db_rom_handler.update_rom(durable.id, {"missing_from_fs": False})

    async def scan_mapping(command, **kwargs):
        mapping_calls.append(
            (command.trigger.value, command.scan_type, kwargs["metadata_locale"])
        )
        durable = db_rom_handler.get_rom(bound.rom_id)
        await observe_pc_automation(
            automation,
            durable.platform,
            SimpleNamespace(),
            durable,
            True,
            selected=provider == "steam",
            completed=completed,
        )
        return scan.ScanStats()

    async def text_fetch(*args, **kwargs):
        _dispatch()
        if provider == "steam":
            request = args[0]
            assert request.explicit_steam_id == 10
            assert request.descriptions_only and request.metadata_locale == "fr"
        else:
            assert args[1] == 10
            assert kwargs["descriptions_only"] and kwargs["metadata_locale"] == "fr"
        observed.append(provider)
        return {
            provider
            + "_metadata": {
                "app_id": 10,
                "source": "storefront",
                "text_variants": {
                    "de": {
                        "summary": "Deutsch",
                        "source_language": "german" if provider == "steam" else "de",
                    },
                    "fr": {
                        "summary": "Francais",
                        "source_language": "french" if provider == "steam" else "fr",
                    },
                    "en": {
                        "summary": "English",
                        "source_language": "english" if provider == "steam" else "en",
                    },
                },
            }
        }

    monkeypatch.setattr(scan, "execute_mapping_scan", scan_mapping)
    monkeypatch.setattr(
        scan, "_get_socket_manager", lambda: SimpleNamespace(emit=AsyncMock())
    )
    monkeypatch.setattr(worker, "get_current_job", lambda: None)
    monkeypatch.setattr(worker, "_heartbeat", lambda *args: None)
    monkeypatch.setattr(pc_steam_enrichment, "resolve_steam_pc_enrichment", text_fetch)
    monkeypatch.setattr(metadata.meta_ss_handler, "get_rom_by_id", text_fetch)
    await worker.run_scan_operation(ready.id)
    final = repo.execution(ready.id)
    assert final["state"] == "completed"
    assert final["scan_stats"]["provider_requests"] == 1
    assert final["scan_stats"]["inventory_checked"] == 0
    assert mapping_calls == [(trigger, mode, "fr")]
    assert finalizations == [bound.rom_id]
    assert observed == [provider]
    durable = db_rom_handler.get_rom(bound.rom_id)
    assert durable.manual_metadata == {"descriptions": {"en": "Protected English"}}
    assert durable.summary == "Legacy summary"
    slots = getattr(durable, provider + "_metadata")["text_variants"]
    assert slots["fr"]["summary"] == "Francais"
    assert slots["en"]["summary"] == "English"
    # The binding fingerprint comes from the actual registration seam.
    from sqlalchemy import select

    from models.scan_inventory import ScanMetadataRetry

    with sync_session.begin() as session:
        rows = session.scalars(
            select(ScanMetadataRetry).where(
                ScanMetadataRetry.rom_id == bound.rom_id,
                ScanMetadataRetry.normalized_query == "descriptions:v1:10:parent",
            )
        ).all()
        assert len(rows) == 1 and rows[0].last_request_at is not None
        assert rows[0].outcome == "matched"


@pytest.mark.asyncio
async def test_actual_quick_igdb_merge_supplies_steam_description_identity(
    monkeypatch, bound_game, inventory_attempt
):
    from handler import scan_handler as scanner
    from handler import scan_retry_execution as execution
    from handler.metadata.pc_automation import pc_automation_handler
    from handler.scan_handler import ScanType
    from handler.scan_pc_automation_observation import observe_pc_automation

    bound, command_data = bound_game
    with sync_session.begin() as session:
        row = session.get(Rom, bound.rom_id)
        row.platform.slug = "win"
        row.platform.igdb_id = 6
    original = db_rom_handler.get_rom(bound.rom_id)
    lookup = AsyncMock(return_value={"igdb_id": 3070, "steam_id": 10, "name": "Game"})
    search = AsyncMock(side_effect=AssertionError("known ID must not search Steam"))
    monkeypatch.setattr(scanner.meta_igdb_handler, "get_rom", lookup)
    monkeypatch.setattr(scanner.meta_playmatch_handler, "is_enabled", lambda: False)
    monkeypatch.setattr(
        pc_automation_handler.match_handler, "fetch_unique_steam_match", search
    )
    monkeypatch.setattr(execution, "configured_sources", lambda policy: ["steam"])
    coordinator = RetryCoordinator({"apis": ["steam", "igdb"], "metadata_locale": "fr"})
    command = decode_command(command_data["commands"][0])
    fs_rom: FSRom = {
        "fs_name": original.fs_name,
        "flat": True,
        "nested": False,
        "files": [],
        "crc_hash": "",
        "md5_hash": "",
        "sha1_hash": "",
        "ra_hash": "",
    }
    with bind_scan_write_context(context(inventory_attempt)), bind_checkpoint_command(
        command
    ), bind_retry_coordinator(coordinator):
        scanned = await scanner.scan_rom(
            ScanType.QUICK,
            original.platform,
            original,
            fs_rom,
            ["igdb", "steam"],
            newly_added=True,
            metadata_only=True,
            metadata_locale="fr",
        )
        durable = scanner.merge_scan_rom(scanned)
        assert db_rom_handler.get_rom(durable.id).steam_id == 10
        await observe_pc_automation(
            scanner.process_pc_automation_after_scan,
            original.platform,
            scanned,
            durable,
            True,
        )
    lookup.assert_awaited_once()
    search.assert_not_awaited()
    assert len(coordinator.candidates) == 1
    assert coordinator.candidates[0].identity.query == "descriptions:v1:10:parent"
