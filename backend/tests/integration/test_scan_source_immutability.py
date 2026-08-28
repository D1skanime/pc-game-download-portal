import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

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
