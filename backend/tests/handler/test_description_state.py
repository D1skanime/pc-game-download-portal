"""Current text-only writes share catalog authority and retry transactions."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime

import pytest
from tests.handler.test_scan_inventory_state import bound_game as bound_game
from tests.handler.test_scan_inventory_state import clear_inventory as clear_inventory
from tests.handler.test_scan_inventory_state import (
    inventory_attempt as inventory_attempt,
)
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.scan_inventory_state import _digest, load_retry_states
from handler.database.scan_write_fence import bind_scan_write_context
from handler.scan_metadata_retry_policy import RetryIdentity, observe_outcome
from models.rom import Rom

pytest_plugins = ["tests.handler.test_scan_operations"]


def snapshot(binding, provider="steam"):
    with sync_session.begin() as session:
        rom = session.get(Rom, binding.rom_id)
        return rom.updated_at, {
            provider + "_id": getattr(rom, provider + "_id"),
            provider + "_metadata": deepcopy(getattr(rom, provider + "_metadata")),
            "manual_metadata": deepcopy(rom.manual_metadata),
        }


def seed(binding, provider="steam"):
    with sync_session.begin() as session:
        rom = session.get(Rom, binding.rom_id)
        setattr(rom, provider + "_id", 10)
        setattr(rom, provider + "_metadata", {"kept": "provider field"})
        rom.manual_metadata = {
            "descriptions": {"en": "  Protected English  "},
            "name": True,
        }
    return snapshot(binding, provider)


def patch(provider="steam", **extra):
    language = "german" if provider == "steam" else "de"
    return {
        provider
        + "_metadata": {
            "app_id": 10,
            "source": "storefront",
            "kept": "must not replace",
            "text_variants": {
                "de": {"source_language": language, "summary": "Deutsch"},
                "en": {
                    "source_language": "english" if provider == "steam" else "en",
                    "summary": "English",
                },
            },
        },
        **extra,
    }


def state(binding, provider="steam"):
    identity = RetryIdentity(
        binding,
        provider,
        "descriptions:v1:10:parent",
        "de",
        "f" * 64,
        purpose="description",
    )
    now = datetime.now().replace(microsecond=123456)
    return observe_outcome(
        identity,
        None,
        outcome="no_match",
        clock=lambda: now,
        invoked_at=now,
        request_at=now,
    )


def apply(binding, expected, current, data, *, provider="steam", retry=None, **extra):
    writer = db_rom_handler.apply_description_patch
    return writer(
        binding=binding,
        component_id=None,
        provider=provider,
        provider_id=10,
        expected_updated_at=expected,
        expected_text_digest=_digest(current),
        data=data,
        retry_state=retry,
        **extra,
    )


@pytest.mark.parametrize("provider", ["steam", "ss"])
def test_only_text_changes_and_replay_is_noop(bound_game, inventory_attempt, provider):
    binding, _ = bound_game
    expected, current = seed(binding, provider)
    with sync_session.begin() as session:
        before = session.get(Rom, binding.rom_id)
        original_name, original_summary = before.name, before.summary
    with bind_scan_write_context(context(inventory_attempt)):
        assert apply(
            binding,
            expected,
            current,
            patch(
                provider,
                name="forbidden title",
                summary="forbidden scalar",
                steam_id=99,
                manual_metadata={},
            ),
            provider=provider,
            retry=state(binding, provider),
        )
    with sync_session.begin() as session:
        row = session.get(Rom, binding.rom_id)
        assert row.name == original_name and row.summary == original_summary
        assert getattr(row, provider + "_id") == 10
        assert row.manual_metadata == current["manual_metadata"]
        metadata = getattr(row, provider + "_metadata")
        assert metadata["kept"] == "provider field"
        assert metadata["text_variants"]["de"]["summary"] == "Deutsch"
        assert metadata["text_variants"]["en"]["summary"] == "English"
        stamp = row.updated_at
    assert len(load_retry_states(binding)) == 1
    with bind_scan_write_context(context(inventory_attempt)):
        assert not apply(binding, expected, current, patch(provider), provider=provider)
    assert snapshot(binding, provider)[0] == stamp


@pytest.mark.parametrize("provider", ["steam", "ss"])
@pytest.mark.parametrize("same_tick", [False, True])
def test_manual_save_between_fetch_and_commit_is_preserved(
    bound_game,
    inventory_attempt,
    provider,
    same_tick,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    binding, _ = bound_game
    expected, current = seed(binding, provider)
    fetched, release = Event(), Event()

    def worker():
        fetched.set()
        assert release.wait(10)
        with bind_scan_write_context(context(inventory_attempt)):
            return apply(
                binding,
                expected,
                current,
                patch(provider),
                provider=provider,
                retry=state(binding, provider),
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(worker)
        assert fetched.wait(10)
        saved = db_rom_handler.update_manual_description(
            rom_id=binding.rom_id,
            expected_updated_at=expected,
            locale="de",
            description="Concurrent manual edit",
        )
        assert saved is not None
        saved_manual = deepcopy(saved.manual_metadata)
        if same_tick:
            with sync_session.begin() as session:
                session.get(Rom, binding.rom_id).updated_at = expected
        release.set()
        assert not result.result(timeout=15)
    stamp, after = snapshot(binding, provider)
    assert after["manual_metadata"] == saved_manual
    assert after["manual_metadata"]["descriptions"]["de"] == "Concurrent manual edit"
    assert "text_variants" not in after[provider + "_metadata"]
    assert not load_retry_states(binding)


@pytest.mark.parametrize("provider", ["steam", "ss"])
def test_same_tick_provider_identity_change_rejects_text_and_retry(
    bound_game, inventory_attempt, provider
):
    binding, _ = bound_game
    expected, current = seed(binding, provider)
    with sync_session.begin() as session:
        row = session.get(Rom, binding.rom_id)
        setattr(row, provider + "_id", 11)
        row.updated_at = expected
    with bind_scan_write_context(context(inventory_attempt)):
        assert not apply(
            binding,
            expected,
            current,
            patch(provider),
            provider=provider,
            retry=state(binding, provider),
        )
    assert not load_retry_states(binding)
    assert snapshot(binding, provider)[1][provider + "_id"] == 11


@pytest.mark.parametrize("provider", ["steam", "ss"])
@pytest.mark.parametrize(
    "revoked",
    [
        "mapping_revision",
        "mapping_path",
        "root_inactive",
        "root_binding",
        "incarnation",
        "lease",
        "attempt",
        "cancel",
        "owner",
        "operation_version",
    ],
)
def test_revoked_authority_blocks_text_and_retry(
    bound_game,
    inventory_attempt,
    provider,
    revoked,
):
    from datetime import timedelta

    from handler.database.scan_write_fence import ScanWriteRejected
    from models.scan_operation import ScanOperation
    from models.storage import PlatformStorageMapping, StorageRoot

    binding, _ = bound_game
    expected, current = seed(binding, provider)
    bound = context(inventory_attempt)
    extra = {}
    if revoked == "attempt":
        bound = replace(bound, attempt_id="foreign")
    elif revoked == "owner":
        bound = replace(bound, lease_owner="foreign")
    elif revoked == "operation_version":
        extra["expected_operation_version"] = 0
    elif revoked == "incarnation":
        binding = replace(binding, rom_incarnation="e" * 32)
    else:
        with sync_session.begin() as session:
            mapping = session.get(PlatformStorageMapping, binding.mapping_id)
            if revoked == "mapping_revision":
                mapping.version += 1
            elif revoked == "mapping_path":
                mapping.relative_path = "Other"
            elif revoked == "root_inactive":
                session.get(StorageRoot, binding.storage_root_id).active = False
            elif revoked == "root_binding":
                replacement = StorageRoot(
                    name="Other root", container_path="/phase34/owned/other"
                )
                session.add(replacement)
                session.flush()
                mapping.storage_root_id = replacement.id
            elif revoked == "lease":
                session.get(ScanOperation, inventory_attempt.id).lease_expires_at = (
                    datetime.now() - timedelta(seconds=2)
                )
            elif revoked == "cancel":
                session.get(ScanOperation, inventory_attempt.id).intentional_cancel = (
                    True
                )
    with bind_scan_write_context(bound), pytest.raises(ScanWriteRejected):
        apply(
            binding,
            expected,
            current,
            patch(provider),
            provider=provider,
            retry=state(binding, provider),
            **extra,
        )
    with sync_session.begin() as session:
        assert (
            getattr(session.get(Rom, binding.rom_id), provider + "_metadata")
            == current[provider + "_metadata"]
        )
        from models.scan_inventory import ScanMetadataRetry

        assert session.query(ScanMetadataRetry).count() == 0


def test_explicit_session_rolls_back_text_and_retry_together(
    bound_game, inventory_attempt
):
    binding, _ = bound_game
    expected, current = seed(binding)
    with pytest.raises(RuntimeError, match="rollback"):
        with bind_scan_write_context(context(inventory_attempt)):
            with sync_session.begin() as session:
                assert apply(
                    binding,
                    expected,
                    current,
                    patch(),
                    retry=state(binding),
                    session=session,
                )
                raise RuntimeError("rollback")
    assert snapshot(binding)[1] == current
    assert not load_retry_states(binding)


def test_component_text_preserves_parent_and_metadata_source(
    bound_game, inventory_attempt
):
    from models.rom import RomComponent, RomComponentKind, RomComponentMetadata

    binding, _ = bound_game
    seed(binding)
    with sync_session.begin() as session:
        component = RomComponent(
            rom_id=binding.rom_id, relative_path="dlc", kind=RomComponentKind.DLC
        )
        session.add(component)
        session.flush()
        metadata = RomComponentMetadata(
            component_id=component.id,
            steam_id=10,
            name="Saved DLC",
            summary="Legacy DLC",
            metadata_source="igdb",
            steam_metadata={"kept": "DLC field"},
            manual_metadata={"descriptions": {"en": "Manual DLC"}},
            provider_metadata={"igdb_metadata": {"name": "IGDB"}},
        )
        session.add(metadata)
        session.flush()
        identity, expected = component.id, component.updated_at
        current = {
            "steam_id": 10,
            "steam_metadata": deepcopy(metadata.steam_metadata),
            "manual_metadata": deepcopy(metadata.manual_metadata),
        }
    with sync_session.begin() as session:
        expected = session.get(RomComponent, identity).updated_at
    parent_before = snapshot(binding)
    retry = state(binding)
    retry = replace(
        retry,
        identity=replace(
            retry.identity, query=f"descriptions:v1:10:component:{identity}"
        ),
    )
    with bind_scan_write_context(context(inventory_attempt)):
        assert db_rom_handler.apply_description_patch(
            binding=binding,
            component_id=identity,
            provider="steam",
            provider_id=10,
            expected_updated_at=expected,
            expected_text_digest=_digest(current),
            data=patch(name="Forbidden"),
            retry_state=retry,
        )
    with sync_session.begin() as session:
        saved = session.get(RomComponentMetadata, identity)
        assert saved.name == "Saved DLC" and saved.summary == "Legacy DLC"
        assert saved.metadata_source == "igdb" and saved.provider_metadata == {
            "igdb_metadata": {"name": "IGDB"}
        }
        assert saved.manual_metadata == current["manual_metadata"]
        assert saved.steam_metadata["kept"] == "DLC field"
        assert saved.steam_metadata["text_variants"]["de"]["summary"] == "Deutsch"
    assert snapshot(binding) == parent_before


@pytest.mark.parametrize("provider", ["steam", "ss"])
def test_invalid_empty_patch_never_updates_target_clock(
    bound_game, inventory_attempt, provider
):
    binding, _ = bound_game
    expected, current = seed(binding, provider)
    bad = {
        provider
        + "_metadata": {
            "app_id": 999,
            "text_variants": {
                "de": {"source_language": "english", "summary": "Wrong slot"}
            },
        }
    }
    with bind_scan_write_context(context(inventory_attempt)):
        assert not apply(binding, expected, current, bad, provider=provider)
    assert snapshot(binding, provider) == (expected, current)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["steam", "ss"])
@pytest.mark.parametrize("partial", [False, True])
async def test_dispatch_persists_slots_observed_facts_and_restart_cooldown(
    bound_game,
    inventory_attempt,
    provider,
    partial,
    monkeypatch,
):
    from types import SimpleNamespace

    from handler import (
        metadata,
    )
    from handler import scan_description_retry as descriptions
    from handler import scan_retry_execution as execution
    from handler.metadata import pc_steam_enrichment
    from handler.scan_operation_recovery import decode_command
    from models.platform import Platform
    from utils.scan_provider_observation import _dispatch

    binding, command = bound_game
    seed(binding, provider)
    with sync_session.begin() as session:
        row = session.get(Rom, binding.rom_id)
        session.get(Platform, row.platform_id).slug = (
            "win" if provider == "steam" else "snes"
        )
    monkeypatch.setattr(execution, "configured_sources", lambda policy: [provider])
    monkeypatch.setattr(
        "handler.scan_operation_worker.check_worker_boundary", lambda: None
    )
    observed = []
    data = patch(provider)
    if not partial:
        data[provider + "_metadata"]["text_variants"]["fr"] = {
            "source_language": "french" if provider == "steam" else "fr",
            "summary": "Francais",
        }

    async def fetch(*args, **kwargs):
        _dispatch()
        observed.append((args, kwargs))
        return data

    if provider == "steam":
        monkeypatch.setattr(pc_steam_enrichment, "resolve_steam_pc_enrichment", fetch)
    else:
        monkeypatch.setattr(metadata.meta_ss_handler, "get_rom_by_id", fetch)
    policy = {
        "apis": [provider],
        "metadata_locale": "fr",
        "description_languages": ("de", "en"),
    }
    retry = execution.RetryCoordinator(policy)
    rom = db_rom_handler.get_rom(binding.rom_id)
    quick = SimpleNamespace(binding=binding, automation_observation=None)
    retry.consider_descriptions(
        quick,
        rom,
        decode_command(command["commands"][0]),
        targets=[descriptions.target_from_rom(rom)],
    )
    candidate = retry.candidates[0]
    policy["metadata_locale"] = "de"
    with bind_scan_write_context(context(inventory_attempt)):
        await descriptions.dispatch_description(
            retry, retry.work[candidate.identity.game_key], candidate.identity
        )
    assert len(observed) == 1
    if provider == "steam":
        assert observed[0][0][0].metadata_locale == "fr"
        assert observed[0][0][0].descriptions_only
    else:
        assert (
            observed[0][1]["metadata_locale"] == "fr"
            and observed[0][1]["descriptions_only"]
        )
    after = snapshot(binding, provider)[1]
    assert after["manual_metadata"]["descriptions"]["en"] == "  Protected English  "
    slots = after[provider + "_metadata"]["text_variants"]
    assert slots["de"]["summary"] == "Deutsch" and slots["en"]["summary"] == "English"
    assert ("fr" in slots) is not partial
    row = load_retry_states(binding)[0]
    assert row.outcome == ("no_match" if partial else "matched")
    assert row.no_match_streak == int(partial)
    assert row.last_request_at is not None and row.last_invoked_at is not None
    assert quick.automation_observation["requests"] == 1
    assert not quick.automation_observation["cached"]
    restarted = execution.RetryCoordinator(retry.policy)
    restarted.consider_descriptions(
        quick,
        db_rom_handler.get_rom(binding.rom_id),
        decode_command(command["commands"][0]),
        targets=[descriptions.target_from_rom(db_rom_handler.get_rom(binding.rom_id))],
    )
    assert not restarted.candidates


def test_component_query_is_bounded_and_continues_past_complete_page(
    bound_game,
    inventory_attempt,
    monkeypatch,
):
    from types import SimpleNamespace

    from handler import scan_description_retry as descriptions
    from handler import scan_retry_execution as execution
    from handler.scan_operation_recovery import decode_command
    from models.platform import Platform
    from models.rom import RomComponent, RomComponentKind, RomComponentMetadata

    binding, command = bound_game
    seed(binding)
    with sync_session.begin() as session:
        row = session.get(Rom, binding.rom_id)
        session.get(Platform, row.platform_id).slug = "win"
        # A complete first page must not hide later missing descriptions.
        for index in range(70):
            component = RomComponent(
                rom_id=binding.rom_id,
                relative_path=f"dlc{index}",
                kind=RomComponentKind.DLC,
            )
            session.add(component)
            session.flush()
            session.add(
                RomComponentMetadata(
                    component_id=component.id,
                    steam_id=10,
                    manual_metadata=(
                        {"descriptions": {"de": "Manuell", "en": "Manual"}}
                        if index < 64
                        else {}
                    ),
                )
            )
    rom = db_rom_handler.get_rom(binding.rom_id)
    page, cursor = descriptions.get_description_component_page(rom)
    assert len(page) == 64 and cursor is not None
    rest, _ = descriptions.get_description_component_page(rom, after=cursor)
    assert len(rest) == 6
    monkeypatch.setattr(execution, "configured_sources", lambda policy: ["steam"])
    retry = execution.RetryCoordinator(
        {"apis": ["steam"], "metadata_locale": "de", "description_languages": ("en",)}
    )
    retry.consider_descriptions(
        SimpleNamespace(binding=binding), rom, decode_command(command["commands"][0])
    )
    assert len(retry.candidates) == 7
    assert (
        len(
            {
                item.component_id
                for item in retry.description_targets.values()
                if item.component_id
            }
        )
        == 6
    )


@pytest.mark.parametrize("revoked", ["cancel", "root", "mapping"])
def test_commit_boundary_revocation_rolls_back_catalog_and_retry(
    bound_game,
    inventory_attempt,
    revoked,
):
    from sqlalchemy import update

    from handler.database.scan_write_fence import ScanWriteRejected
    from models.scan_operation import ScanOperation
    from models.storage import PlatformStorageMapping, StorageRoot

    binding, _ = bound_game
    expected, current = seed(binding)
    with pytest.raises(ScanWriteRejected):
        with bind_scan_write_context(context(inventory_attempt)):
            with sync_session.begin() as session:
                assert apply(
                    binding,
                    expected,
                    current,
                    patch(),
                    retry=state(binding),
                    session=session,
                )
                if revoked == "cancel":
                    session.execute(
                        update(ScanOperation)
                        .where(ScanOperation.id == inventory_attempt.id)
                        .values(intentional_cancel=True)
                    )
                elif revoked == "root":
                    session.execute(
                        update(StorageRoot)
                        .where(StorageRoot.id == binding.storage_root_id)
                        .values(active=False)
                    )
                else:
                    session.execute(
                        update(PlatformStorageMapping)
                        .where(PlatformStorageMapping.id == binding.mapping_id)
                        .values(version=2)
                    )
    assert snapshot(binding)[1] == current
    assert not load_retry_states(binding)


def test_detached_component_lookup_loads_description_metadata(bound_game):
    from sqlalchemy import inspect

    from models.rom import RomComponent, RomComponentKind, RomComponentMetadata

    binding, _ = bound_game
    with sync_session.begin() as session:
        component = RomComponent(
            rom_id=binding.rom_id, relative_path="dlc", kind=RomComponentKind.DLC
        )
        session.add(component)
        session.flush()
        identity = component.id
        session.add(
            RomComponentMetadata(
                component_id=identity,
                steam_id=10,
                steam_metadata={"text_variants": {}},
                manual_metadata={"descriptions": {"en": "Protected component English"}},
            )
        )
    loaded = db_rom_handler.get_pc_component_by_id(binding.rom_id, identity)
    assert loaded is not None
    assert "component_metadata" not in inspect(loaded).unloaded
    assert loaded.component_metadata.steam_id == 10
    assert loaded.component_metadata.manual_metadata == {
        "descriptions": {"en": "Protected component English"}
    }
    assert db_rom_handler.get_pc_component_by_id(binding.rom_id + 1, identity) is None
