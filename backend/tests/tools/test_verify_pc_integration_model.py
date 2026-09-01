from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "backend" / "tools" / "verify_pc_integration_model.py"


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """This focused tool suite is database free."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override shared database cleanup for this suite."""


def _load_module():
    if not MODULE_PATH.is_file():
        pytest.fail(
            "Phase 10 RED: missing harness module at "
            f"{MODULE_PATH.relative_to(REPO_ROOT)}"
        )

    spec = importlib.util.spec_from_file_location(
        "verify_pc_integration_model", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fixture_copy_uses_win_structure_without_changing_source(tmp_path: Path):
    module = _load_module()
    source = tmp_path / "source-library"
    game = source / "Cyberpunk2077"
    game.mkdir(parents=True)
    (game / "setup.exe").write_bytes(b"base game")
    (game / "dlc").mkdir()
    (game / "dlc" / "setup-dlc.exe").write_bytes(b"dlc")
    (source / "obsolete-empty-game").mkdir()

    source_digest = module.fixture_tree_digest(source)
    fixture_root = module.prepare_fixture_copy(source, tmp_path / "run")

    assert fixture_root == tmp_path / "run" / "library"
    assert (
        fixture_root / "roms" / "win" / "Cyberpunk2077" / "setup.exe"
    ).read_bytes() == b"base game"
    assert fixture_root / "roms" / "win" / "Cyberpunk2077" / "dlc" / "setup-dlc.exe"
    assert not (fixture_root / "roms" / "win" / "obsolete-empty-game").exists()
    assert module.fixture_tree_digest(source) == source_digest


def test_compose_environment_is_unique_to_phase_10(tmp_path: Path):
    module = _load_module()

    environment = module.phase10_environment(
        fixture_root=tmp_path / "library",
        artifacts_root=tmp_path / "artifacts",
        compose_project="phase10-test-run",
    )

    assert environment["COMPOSE_PROJECT_NAME"] == "phase10-test-run"
    assert environment["PHASE10_FIXTURE_SOURCE"] == str(tmp_path / "library")
    assert environment["PHASE10_ARTIFACTS"] == str(tmp_path / "artifacts")
    assert "PHASE9_FIXTURE_SOURCE" not in environment
