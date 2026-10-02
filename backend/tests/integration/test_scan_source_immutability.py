import hashlib
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

from handler.database.pc_automation_handler import DBPcAutomationHandler
from handler.filesystem.roms_handler import FSRomsHandler
from handler.filesystem.storage_policy import _create_external_descriptor
from handler.metadata.pc_automation import AutomationDecision, PcAutomationHandler
from handler.metadata.pc_match_handler import PcMetadataMatchHandler
from models.platform import Platform
from models.rom import Rom, RomComponentKind
from tasks.scheduled import scan_library

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "backend" / "tools" / "verify_operational_immutability.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_operational_immutability", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """This integration slice verifies manifest logic without a live database."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override shared cleanup hooks for this db-free suite."""


def source_manifest(root: Path):
    return _load_module().manifest_identities(
        _load_module().build_fixture_manifest(root)
    )


def _source_evidence(root: Path) -> tuple[tuple[str, str, int, int, str], ...]:
    """Capture the source properties the scan and review paths must preserve."""
    evidence = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        stat = path.lstat()
        entry_type = "directory" if path.is_dir() else "file"
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        evidence.append(
            (
                path.relative_to(root).as_posix(),
                entry_type,
                stat.st_size,
                stat.st_mtime_ns,
                digest,
            )
        )
    return tuple(evidence)


def test_manifest_compares_names_types_sizes_and_hashes(tmp_path: Path):
    root = tmp_path / "external"
    (root / "Unicode").mkdir(parents=True)
    (root / "Unicode" / "empty").mkdir()
    (root / "Unicode" / "zero.bin").write_bytes(b"")
    (root / "game.iso").write_bytes(b"immutable bytes")
    before = source_manifest(root)
    assert source_manifest(root) == before
    assert (
        "game.iso",
        "file",
        15,
        hashlib.sha256(b"immutable bytes").hexdigest(),
    ) in before


def test_scan_source_uses_policy_capability_not_legacy_derivation():
    source = Path("handler/scan_handler.py").read_text()
    assert (
        "def execute_mapped_scan" in source
    ), "Phase 5 RED: immutable mapped scan execution is not implemented"
    assert "resolve_steam_pc_enrichment" in source
    assert "reconcile_steam_patch_media" in source
    assert "_steam_artwork_handler" not in source
    assert "StorageOperation.SCAN" in source
    assert "StorageOperation.WRITE" not in source


@pytest.mark.asyncio
async def test_cyberpunk_parent_dlc_fixture_builds_one_immutable_dlc_component(
    tmp_path: Path,
):
    """The disposable UAT layout must exercise the scanner's real DLC shape."""
    source_root = tmp_path / "library"
    parent = source_root / "roms" / "win" / "Cyberpunk 2077"
    dlc = parent / "dlc" / "Phantom Liberty"
    dlc.mkdir(parents=True)
    (parent / "Cyberpunk 2077.iso").write_text("base fixture", encoding="utf-8")
    payload = dlc / "Phantom Liberty.zip"
    payload.write_text("dlc fixture", encoding="utf-8")
    before = _source_evidence(source_root)

    handler = FSRomsHandler(_create_external_descriptor(1, source_root, mapping_id=1))
    rom = Rom(
        id=1,
        fs_name="Cyberpunk 2077",
        fs_path="roms/win",
        platform=Platform(name="Windows", slug="win", fs_slug="win"),
    )

    components = await handler.get_pc_components(rom)

    assert [(component.relative_path, component.kind) for component in components] == [
        ("dlc/Phantom Liberty", RomComponentKind.DLC)
    ]
    assert [member.relative_path for member in components[0].manifest_members] == [
        "dlc/Phantom Liberty/Phantom Liberty.zip"
    ]
    assert _source_evidence(source_root) == before


@pytest.mark.asyncio
async def test_uat_interval_automation_keeps_mapped_source_evidence_immutable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Safe and pending automation paths must only update catalog-owned state."""
    source_root = tmp_path / "isolated-pc-library"
    game_root = source_root / "Safe Main Title"
    dlc_root = game_root / "DLC"
    dlc_root.mkdir(parents=True)
    (game_root / "Safe Main Title.iso").write_text("main fixture", encoding="utf-8")
    (dlc_root / "Safe Main Title DLC.zip").write_text("dlc fixture", encoding="utf-8")
    (source_root / "Ambiguous Title.iso").write_text(
        "pending fixture", encoding="utf-8"
    )
    before = _source_evidence(source_root)

    queued: list[dict[str, object]] = []
    owned_applies: list[tuple[str, object]] = []
    timestamp = datetime(2026, 10, 2, tzinfo=timezone.utc)
    safe_parent = SimpleNamespace(
        id=1,
        fs_name="Safe Main Title",
        fs_name_no_ext="Safe Main Title",
        updated_at=timestamp,
        manual_metadata={},
        steam_id=42,
    )
    safe_dlc = SimpleNamespace(
        id=2,
        relative_path="DLC/Safe Main Title DLC.zip",
        updated_at=timestamp,
        kind=RomComponentKind.DLC,
        component_metadata=None,
    )
    ambiguous_parent = SimpleNamespace(
        id=3,
        fs_name="Ambiguous Title",
        fs_name_no_ext="Ambiguous Title",
        updated_at=timestamp,
        manual_metadata={},
        steam_id=None,
    )

    class QueueRecorder:
        def upsert_pending(self, **kwargs: object) -> None:
            queued.append(kwargs)

    class DeterministicMatcher:
        async def fetch_unique_steam_match(self, rom: object, _query: str):
            return {"steam_id": 42} if rom is safe_parent else None

        async def fetch_parent_listed_steam_dlc(self, _rom: object, _component: object):
            return {
                "steam_id": 84,
                "steam_metadata": {"type": "dlc", "fullgame": {"appid": 42}},
            }

    async def apply_parent(rom: object, candidate: dict[str, object]) -> bool:
        owned_applies.append(("parent", candidate["steam_id"]))
        assert rom is safe_parent
        return True

    async def apply_component(
        _rom: object, component: object, candidate: dict[str, object]
    ) -> bool:
        owned_applies.append(("component", candidate["steam_id"]))
        assert component is safe_dlc
        return True

    automation = PcAutomationHandler(
        match_handler=cast(PcMetadataMatchHandler, DeterministicMatcher()),
        queue_handler=cast(DBPcAutomationHandler, QueueRecorder()),
        apply_parent=apply_parent,
        apply_component=apply_component,
    )
    mapped_run = AsyncMock(return_value={"scanned": "isolated"})
    monkeypatch.setattr(scan_library.scan_library_task, "run", mapped_run)
    monkeypatch.setattr(scan_library, "PC_AUTOMATION_UAT_INTERVAL_SECONDS", 10)

    assert await scan_library.pc_automation_uat_interval_task.run() == {
        "scanned": "isolated"
    }
    assert (
        await automation.process_parent(safe_parent)
    ).decision is AutomationDecision.APPLIED
    assert (
        await automation.process_component(safe_parent, safe_dlc)
    ).decision is AutomationDecision.APPLIED
    assert (
        await automation.process_parent(ambiguous_parent)
    ).decision is AutomationDecision.PENDING

    mapped_run.assert_awaited_once()
    assert owned_applies == [("parent", 42), ("component", 84)]
    assert queued[0]["reason"] == "no_unique_steam_match"
    assert _source_evidence(source_root) == before
