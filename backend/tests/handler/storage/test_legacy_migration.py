from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import stat
from dataclasses import asdict
from pathlib import Path

import pytest


def _subject():
    assert (
        importlib.util.find_spec("handler.storage.legacy_migration") is not None
    ), "Phase 6 RED: exact bounded legacy detection is not implemented"
    return importlib.import_module("handler.storage.legacy_migration")


def _external(root: Path):
    from handler.filesystem.storage_policy import _create_external_descriptor

    return _create_external_descriptor(7, root)


def _source_manifest(root: Path) -> tuple[tuple[object, ...], ...]:
    rows = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        digest = None
        target = None
        if stat.S_ISREG(metadata.st_mode):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        elif stat.S_ISLNK(metadata.st_mode):
            target = os.readlink(path)
        rows.append(
            (
                relative,
                stat.S_IFMT(metadata.st_mode),
                stat.S_IMODE(metadata.st_mode),
                metadata.st_size,
                digest,
                target,
            )
        )
    return tuple(rows)


def _detect(root: Path, fs_slug: str = "gb", **kwargs):
    subject = _subject()
    return subject.detect_legacy_storage(
        _external(root),
        platform_id=5,
        storage_root_id=7,
        fs_slug=fs_slug,
        **kwargs,
    )


def test_exact_candidate_grammars_are_literal_and_bounded():
    subject = _subject()

    assert subject.build_legacy_candidate_paths("M?nchen GB") == (
        "roms/M?nchen GB",
        "M?nchen GB/roms",
    )
    for unsafe in ("", "../gb", "games/gb", "/gb", "C:\\gb", "gb\\roms"):
        with pytest.raises(ValueError):
            subject.build_legacy_candidate_paths(unsafe)


def test_detects_only_the_exact_persisted_fs_slug(tmp_path: Path):
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "game.gb").write_bytes(b"game")
    alias = tmp_path / "roms" / "GB"
    alias.mkdir()
    (alias / "wrong.gb").write_bytes(b"wrong")
    (tmp_path / "gb_old").mkdir()
    before = _source_manifest(tmp_path)

    result = _detect(tmp_path)

    assert result.state == "detected"
    assert result.proposed_relative_path == "roms/gb"
    assert result.observed_files == 1
    assert result.observed_bytes == 4
    assert result.selectable is True
    assert result.safe_problem_code is None
    assert _source_manifest(tmp_path) == before


def test_custom_alias_and_configured_names_never_become_candidates(tmp_path: Path):
    for relative in ("roms/gb_old", "playstation3_backup", "games/gb"):
        target = tmp_path / relative
        target.mkdir(parents=True)
        (target / "game.rom").write_bytes(b"content")

    result = _detect(tmp_path)

    assert result.state == "manual_mapping_required"
    assert result.proposed_relative_path is None
    assert result.selectable is False
    assert result.safe_problem_code == "canonical_layout_missing"


def test_both_canonical_grammars_require_manual_mapping(tmp_path: Path):
    for relative in ("roms/gb", "gb/roms"):
        target = tmp_path / relative
        target.mkdir(parents=True)
        (target / "game.gb").write_bytes(b"game")

    result = _detect(tmp_path)

    assert result.state == "manual_mapping_required"
    assert result.proposed_relative_path is None
    assert result.selectable is False
    assert result.safe_problem_code == "multiple_canonical_layouts"


def test_empty_canonical_layout_is_visible_but_unselectable(tmp_path: Path):
    (tmp_path / "gb" / "roms").mkdir(parents=True)

    result = _detect(tmp_path)

    assert result.state == "empty"
    assert result.proposed_relative_path == "gb/roms"
    assert result.observed_files == 0
    assert result.selectable is False
    assert result.safe_problem_code == "canonical_layout_empty"


def test_entry_budget_reports_observed_lower_bound(tmp_path: Path):
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "one.gb").write_bytes(b"1")
    (canonical / "two.gb").write_bytes(b"22")

    result = _detect(tmp_path, entry_budget=1)

    assert result.state == "detected"
    assert result.observed_files == 1
    assert result.lower_bound is True
    assert result.selectable is True
    assert result.safe_problem_code == "entry_budget"


def test_unsafe_candidate_is_path_free_and_unselectable(tmp_path: Path):
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "game.gb").write_bytes(b"game")
    (canonical / "escape").symlink_to(tmp_path / "outside")

    result = _detect(tmp_path)
    serialized = str(asdict(result))

    assert result.state == "unsafe"
    assert result.selectable is False
    assert result.safe_problem_code == "unsafe_entry"
    assert str(tmp_path) not in serialized
    assert "game.gb" not in serialized


def test_detection_uses_only_list_and_stat_capabilities(tmp_path: Path, monkeypatch):
    subject = _subject()
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "game.gb").write_bytes(b"game")
    operations = []
    real_open = subject.open_storage_access

    def observe(storage, operation, relative_path):
        operations.append(operation.value)
        return real_open(storage, operation, relative_path)

    monkeypatch.setattr(subject, "open_storage_access", observe)
    result = _detect(tmp_path)

    assert result.state == "detected"
    assert operations
    assert set(operations) <= {"list", "stat"}


@pytest.mark.parametrize(
    "kind, expected_status",
    [("anonymous", 401), ("viewer", 403)],
)
def test_legacy_detection_authorizes_before_observation(
    client,
    viewer_access_token,
    monkeypatch,
    kind,
    expected_status,
):
    _subject()
    from endpoints import storage as endpoint

    monkeypatch.setattr(
        endpoint.db_legacy_migration_handler,
        "validate_detection_request",
        lambda *_args, **_kwargs: pytest.fail("unauthorized legacy observation"),
    )
    headers = (
        {"Authorization": f"Bearer {viewer_access_token}"} if kind == "viewer" else {}
    )
    response = client.post(
        "/api/storage/legacy-detections",
        headers=headers,
        json={"platform_id": 5, "storage_root_id": 7},
    )

    assert response.status_code == expected_status


def test_admin_explicitly_enqueues_ids_only(client, access_token, monkeypatch):
    _subject()
    from endpoints import storage as endpoint

    monkeypatch.setattr(
        endpoint.db_legacy_migration_handler,
        "validate_detection_request",
        lambda platform_id, storage_root_id: None,
    )
    captured = {}

    def enqueue(function, **kwargs):
        captured["function"] = function
        captured.update(kwargs)
        return type("Job", (), {"id": "safe-job-id"})()

    monkeypatch.setattr(endpoint.low_prio_queue, "enqueue", enqueue)
    response = client.post(
        "/api/storage/legacy-detections",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"platform_id": 5, "storage_root_id": 7},
    )

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "safe-job-id",
        "platform_id": 5,
        "storage_root_id": 7,
        "state": "pending",
    }
    assert set(captured["kwargs"]) == {
        "platform_id",
        "storage_root_id",
        "actor_user_id",
    }
    assert all(isinstance(value, int) for value in captured["kwargs"].values())


def test_legacy_detection_openapi_is_bounded_and_has_no_fallback(client):
    _subject()
    schema = client.get("/openapi.json").json()

    assert "post" in schema["paths"]["/api/storage/legacy-detections"]
    assert "get" in schema["paths"]["/api/storage/legacy-detections/{result_id}"]
    legacy_schemas = {
        name: value
        for name, value in schema["components"]["schemas"].items()
        if name.startswith("LegacyDetection")
    }
    serialized = str(legacy_schemas).lower()
    assert "container_path" not in serialized
    assert "absolute" not in serialized
    assert "raw" not in serialized
    assert "fallback" not in serialized
    assert "file_list" not in serialized
