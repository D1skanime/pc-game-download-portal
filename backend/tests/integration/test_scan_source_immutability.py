import hashlib
from pathlib import Path


def source_manifest(root: Path):
    result = []
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().encode()):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            result.append((rel, "symlink", 0, ""))
        elif path.is_dir():
            result.append((rel, "directory", 0, ""))
        else:
            data = path.read_bytes()
            result.append((rel, "file", len(data), hashlib.sha256(data).hexdigest()))
    return tuple(result)


def test_manifest_compares_names_types_sizes_and_hashes(tmp_path: Path):
    root = tmp_path / "external"
    (root / "Unicode").mkdir(parents=True)
    (root / "Unicode" / "zero.bin").write_bytes(b"")
    (root / "game.iso").write_bytes(b"immutable bytes")
    before = source_manifest(root)
    assert source_manifest(root) == before
    assert before[-1] == (
        "game.iso",
        "file",
        15,
        hashlib.sha256(b"immutable bytes").hexdigest(),
    )


def test_scan_source_uses_policy_capability_not_legacy_derivation():
    source = Path("handler/scan_handler.py").read_text()
    assert (
        "def execute_mapped_scan" in source
    ), "Phase 5 RED: immutable mapped scan execution is not implemented"
