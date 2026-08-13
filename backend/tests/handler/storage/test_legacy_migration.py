from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import stat
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from main import app

from config import OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS
from handler.auth import oauth_handler


def _subject():
    assert (
        importlib.util.find_spec("handler.storage.legacy_migration") is not None
    ), "Phase 6 RED: exact bounded legacy detection is not implemented"
    return importlib.import_module("handler.storage.legacy_migration")


def _external(root: Path, root_id: int = 7):
    from handler.filesystem.storage_policy import _create_external_descriptor

    return _create_external_descriptor(root_id, root)


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
    assert len(result.source_fingerprint) == 64


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
    assert result.lower_bound is False
    assert result.source_fingerprint is None
    assert result.selectable is False
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
    real_hash = subject.hash_descriptor_file

    def observe(storage, operation, relative_path):
        operations.append(operation.value)
        return real_open(storage, operation, relative_path)

    def observe_hash(*args, **kwargs):
        operations.append("hash")
        return real_hash(*args, **kwargs)

    monkeypatch.setattr(subject, "open_storage_access", observe)
    monkeypatch.setattr(subject, "hash_descriptor_file", observe_hash)
    result = _detect(tmp_path)

    assert result.state == "detected"
    assert operations
    assert set(operations) <= {"list", "stat", "hash"}
    assert "hash" in operations


def test_source_fingerprint_is_content_complete_and_enumeration_deterministic(
    tmp_path: Path,
):
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root, order in ((first, ("b.rom", "a.rom")), (second, ("a.rom", "b.rom"))):
        canonical = root / "roms" / "gb"
        canonical.mkdir(parents=True)
        for name in order:
            (canonical / name).write_bytes(name.encode())

    first_result = _detect(first)
    second_result = _detect(second)

    assert first_result.selectable is True
    assert first_result.source_fingerprint == second_result.source_fingerprint


def test_source_fingerprint_rejects_same_metadata_different_bytes(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    paths = []
    for root, content in ((first, b"first"), (second, b"other")):
        path = root / "roms" / "gb" / "game.rom"
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        path.chmod(0o640)
        os.utime(path, ns=(1_700_000_000_000_000_000,) * 2)
        paths.append(path)

    first_result = _detect(first)
    second_result = _detect(second)

    assert paths[0].stat().st_size == paths[1].stat().st_size
    assert stat.S_IMODE(paths[0].stat().st_mode) == stat.S_IMODE(
        paths[1].stat().st_mode
    )
    assert paths[0].stat().st_mtime_ns == paths[1].stat().st_mtime_ns
    assert first_result.source_fingerprint != second_result.source_fingerprint


@pytest.mark.parametrize(
    ("kwargs", "problem"),
    [
        ({"per_file_byte_budget": 3}, "file_byte_budget"),
        ({"aggregate_byte_budget": 3}, "aggregate_byte_budget"),
    ],
)
def test_incomplete_source_byte_budgets_are_manual_and_path_free(
    tmp_path: Path, kwargs, problem
):
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "private-game.rom").write_bytes(b"1234")

    result = _detect(tmp_path, **kwargs)

    assert result.selectable is False
    assert result.source_fingerprint is None
    assert result.safe_problem_code == problem
    assert "private-game" not in str(asdict(result))


def test_stat_to_hash_replacement_uses_only_aggregate_remaining(
    tmp_path: Path, monkeypatch
):
    subject = _subject()
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "a.rom").write_bytes(b"123")
    replaced = canonical / "z-private.rom"
    replaced.write_bytes(b"1")
    real_hash = subject.hash_descriptor_file
    passed_caps = []
    replacement_manifest = None

    def replace_before_hash(storage, logical_path, **kwargs):
        nonlocal replacement_manifest
        passed_caps.append(kwargs["max_bytes"])
        if logical_path.endswith("z-private.rom"):
            replaced.write_bytes(b"4567")
            replacement_manifest = _source_manifest(tmp_path)
        return real_hash(storage, logical_path, **kwargs)

    monkeypatch.setattr(subject, "hash_descriptor_file", replace_before_hash)
    result = _detect(tmp_path, per_file_byte_budget=10, aggregate_byte_budget=5)

    assert passed_caps == [5, 2]
    assert result.selectable is False
    assert result.source_fingerprint is None
    assert result.safe_problem_code == "aggregate_byte_budget"
    assert "private-game" not in str(asdict(result))
    assert replacement_manifest is not None
    assert _source_manifest(tmp_path) == replacement_manifest


def test_hash_return_over_aggregate_remaining_is_rejected_before_progress(
    tmp_path: Path, monkeypatch
):
    subject = _subject()
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "private-game.rom").write_bytes(b"12")
    before = _source_manifest(tmp_path)
    passed_caps = []

    def dishonest_hash(*_args, **kwargs):
        passed_caps.append(kwargs["max_bytes"])
        return type(
            "DishonestHashResult",
            (),
            {"bytes_read": 5, "sha256": "0" * 64},
        )()

    monkeypatch.setattr(subject, "hash_descriptor_file", dishonest_hash)
    result = _detect(tmp_path, per_file_byte_budget=10, aggregate_byte_budget=4)

    assert passed_caps == [4]
    assert result.observed_files == 0
    assert result.observed_bytes == 0
    assert result.selectable is False
    assert result.source_fingerprint is None
    assert result.safe_problem_code == "aggregate_byte_budget"
    assert "private-game" not in str(asdict(result))
    assert _source_manifest(tmp_path) == before


def test_typed_hash_failure_is_manual_and_does_not_mutate_source(
    tmp_path: Path, monkeypatch
):
    from exceptions.storage_exceptions import DescriptorHashShortReadError

    subject = _subject()
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    (canonical / "private-game.rom").write_bytes(b"1234")
    before = _source_manifest(tmp_path)

    def fail_hash(*_args, **_kwargs):
        raise DescriptorHashShortReadError()

    monkeypatch.setattr(subject, "hash_descriptor_file", fail_hash)
    result = _detect(tmp_path)

    assert result.selectable is False
    assert result.source_fingerprint is None
    assert result.safe_problem_code == "hash_incomplete"
    assert "private-game" not in str(asdict(result))
    assert _source_manifest(tmp_path) == before


def test_detection_results_expire_bind_and_reject_reuse(
    tmp_path: Path, platform, admin_user
):
    from datetime import datetime, timezone

    from handler.database.base_handler import sync_session
    from handler.database.legacy_migration_handler import (
        DBLegacyMigrationHandler,
        LegacyDetectionResultError,
    )
    from handler.storage.legacy_migration import LegacyDetectionOutcome
    from models.storage import PlatformStorageMapping, StorageRoot

    handler = DBLegacyMigrationHandler()
    with sync_session.begin() as database:
        root = StorageRoot(name="legacy", container_path=str(tmp_path))
        database.add(root)
        database.flush()
        root_id = root.id

    context = handler.get_detection_context(platform.id, root_id)
    outcome = LegacyDetectionOutcome(
        platform_id=platform.id,
        storage_root_id=root_id,
        state="detected",
        proposed_relative_path="roms/gb",
        observed_files=1,
        observed_bytes=4,
        lower_bound=False,
        selectable=True,
        safe_problem_code=None,
        source_fingerprint="0" * 64,
    )
    completed_at = datetime(2026, 8, 12, tzinfo=timezone.utc)
    result = handler.save_detection_result(
        context,
        outcome,
        actor_user_id=admin_user.id,
        now=completed_at,
    )

    assert result.expires_at - result.completed_at == timedelta(hours=24)
    handler.require_detection_result(
        result.id,
        platform_id=platform.id,
        expected_version=1,
        consume=True,
        now=completed_at,
    )
    with pytest.raises(LegacyDetectionResultError, match="legacy_detection_stale"):
        handler.require_detection_result(
            result.id,
            platform_id=platform.id,
            expected_version=1,
            now=completed_at,
        )
    with pytest.raises(
        LegacyDetectionResultError, match="legacy_detection_cross_platform"
    ):
        handler.require_detection_result(
            result.id,
            platform_id=platform.id + 1,
            expected_version=2,
            now=completed_at,
        )

    expiring = handler.save_detection_result(
        context,
        outcome,
        actor_user_id=admin_user.id,
        now=completed_at,
    )
    with pytest.raises(LegacyDetectionResultError, match="legacy_detection_expired"):
        handler.require_detection_result(
            expiring.id,
            platform_id=platform.id,
            expected_version=1,
            now=completed_at + timedelta(hours=25),
        )

    stale_context = handler.get_detection_context(platform.id, root_id)
    with sync_session.begin() as database:
        database.add(
            PlatformStorageMapping(
                platform_id=platform.id,
                storage_root_id=root_id,
                relative_path="roms/gb",
            )
        )
    with pytest.raises(LegacyDetectionResultError, match="legacy_detection_stale"):
        handler.save_detection_result(
            stale_context,
            outcome,
            actor_user_id=admin_user.id,
            now=completed_at,
        )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _access_token(user) -> str:
    return oauth_handler.create_access_token(
        data={
            "sub": user.username,
            "iss": "romm:oauth",
            "scopes": " ".join(user.oauth_scopes),
        },
        expires_delta=timedelta(seconds=OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS),
    )


@pytest.fixture
def access_token(admin_user):
    return _access_token(admin_user)


@pytest.fixture
def viewer_access_token(viewer_user):
    return _access_token(viewer_user)


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


def _seed_impact_preview(tmp_path: Path, platform, admin_user):
    from datetime import datetime, timezone

    from handler.database.base_handler import sync_session
    from handler.database.legacy_migration_handler import DBLegacyMigrationHandler
    from handler.storage.legacy_migration import LegacyDetectionOutcome
    from models.rom import Rom
    from models.storage import StorageRoot

    canonical = tmp_path / "roms" / platform.fs_slug
    canonical.mkdir(parents=True)
    (canonical / "one.gb").write_bytes(b"one")
    (canonical / "two.gb").write_bytes(b"two")
    with sync_session.begin() as database:
        root = StorageRoot(name="legacy-impact", container_path=str(tmp_path))
        database.add(root)
        database.flush()
        root_id = root.id
        for name in ("one.gb", "two.gb"):
            database.add(
                Rom(
                    platform_id=platform.id,
                    fs_name=name,
                    fs_name_no_tags=name[:-3],
                    fs_name_no_ext=name[:-3],
                    fs_extension="gb",
                    fs_path=platform.fs_slug,
                    fs_size_bytes=3,
                    name=name,
                    missing_from_fs=True,
                )
            )
    handler = DBLegacyMigrationHandler()
    context = handler.get_detection_context(platform.id, root_id)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    detected = _subject().detect_legacy_storage(
        _external(tmp_path, root_id),
        platform_id=platform.id,
        storage_root_id=root_id,
        fs_slug=platform.fs_slug,
    )
    assert detected.source_fingerprint is not None
    result = handler.save_detection_result(
        context,
        LegacyDetectionOutcome(
            platform_id=platform.id,
            storage_root_id=root_id,
            state="detected",
            proposed_relative_path=f"roms/{platform.fs_slug}",
            observed_files=2,
            observed_bytes=6,
            lower_bound=False,
            selectable=True,
            safe_problem_code=None,
            source_fingerprint=detected.source_fingerprint,
        ),
        actor_user_id=admin_user.id,
        now=now,
    )
    return handler, result, now


def test_impact_preview_binds_confirmation_and_changes_no_state(
    tmp_path: Path, platform, admin_user
):
    from sqlalchemy import func, select

    from handler.database.base_handler import sync_session
    from models.storage import LegacyMigration, PlatformStorageMapping

    handler, result, now = _seed_impact_preview(tmp_path, platform, admin_user)
    before = _source_manifest(tmp_path)
    impact = handler.preview_migration_impact(
        result.id, platform_id=platform.id, expected_result_version=1, now=now
    )
    assert impact.state == "ready"
    assert impact.proposed_mapping.relative_path == f"roms/{platform.fs_slug}"
    assert impact.reconnectable_catalog_count == 2
    assert impact.unmatched_catalog_count == 0
    assert impact.problems == ()
    assert impact.planned_owned_effects.mapping_create_count == 1
    assert impact.planned_owned_effects.catalog_reconnect_count == 2
    assert impact.planned_owned_effects.audit_record_count == 1
    assert impact.planned_owned_effects.rollback_record_count == 1
    assert impact.planned_owned_effects.source_mutation_count == 0
    assert impact.confirmation.detection_result_id == result.id
    assert impact.confirmation.result_version == 1
    assert impact.confirmation.platform_id == platform.id
    assert impact.confirmation.storage_root_id == result.storage_root_id
    assert impact.confirmation.relative_path == f"roms/{platform.fs_slug}"
    assert impact.confirmation.source_fingerprint == result.source_fingerprint
    assert len(impact.confirmation.catalog_fingerprint) == 64
    assert impact.confirmation.catalog_fingerprint.isascii()
    assert impact.confirmation.catalog_fingerprint.islower()
    assert impact.confirmation.expires_at == result.expires_at
    assert impact.source_immutable is True
    assert impact.legacy_fallback_enabled is False
    assert _source_manifest(tmp_path) == before
    with sync_session() as database:
        assert database.scalar(select(func.count(PlatformStorageMapping.id))) == 0
        assert database.scalar(select(func.count(LegacyMigration.id))) == 0
        assert database.get(type(result), result.id).version == 1


def test_impact_confirmation_revalidates_catalog_and_conflicts(
    tmp_path: Path, platform, admin_user
):
    from handler.database.base_handler import sync_session
    from handler.database.legacy_migration_handler import LegacyDetectionResultError
    from models.rom import Rom
    from models.storage import PlatformStorageMapping

    handler, result, now = _seed_impact_preview(tmp_path, platform, admin_user)
    impact = handler.preview_migration_impact(
        result.id, platform_id=platform.id, expected_result_version=1, now=now
    )
    assert (
        type(handler)()
        .validate_impact_confirmation(impact.confirmation, now=now)
        .confirmation
        == impact.confirmation
    )
    with sync_session.begin() as database:
        database.add(
            Rom(
                platform_id=platform.id,
                fs_name="late.gb",
                fs_name_no_tags="late",
                fs_name_no_ext="late",
                fs_extension="gb",
                fs_path=platform.fs_slug,
                fs_size_bytes=4,
                name="Late",
                missing_from_fs=True,
            )
        )
    with pytest.raises(LegacyDetectionResultError) as stale:
        handler.validate_impact_confirmation(impact.confirmation, now=now)
    assert stale.value.code == "legacy_impact_stale"
    with sync_session.begin() as database:
        database.add(
            PlatformStorageMapping(
                platform_id=platform.id,
                storage_root_id=result.storage_root_id,
                relative_path=f"roms/{platform.fs_slug}",
            )
        )
    conflict = handler.preview_migration_impact(
        result.id, platform_id=platform.id, expected_result_version=1, now=now
    )
    assert conflict.state == "manual_mapping_required"
    assert conflict.confirmation is None
    assert [problem.code for problem in conflict.problems] == [
        "active_mapping_conflict"
    ]


def test_admin_migrate_endpoint_returns_only_bounded_atomic_outcome(
    client, access_token, tmp_path: Path, platform, admin_user
):
    handler, result, now = _seed_impact_preview(tmp_path, platform, admin_user)
    impact = handler.preview_migration_impact(
        result.id, platform_id=platform.id, expected_result_version=1, now=now
    )
    confirmation = asdict(impact.confirmation)
    confirmation["expires_at"] = confirmation["expires_at"].isoformat()

    unauthorized = client.post(
        f"/api/storage/legacy-detections/{result.id}/migrate",
        json=confirmation,
    )
    assert unauthorized.status_code == 401

    response = client.post(
        f"/api/storage/legacy-detections/{result.id}/migrate",
        headers={"Authorization": f"Bearer {access_token}"},
        json=confirmation,
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "state",
        "migration_id",
        "migration_version",
        "mapping_id",
        "mapping_version",
        "platform_id",
        "storage_root_id",
        "reconnected_catalog_count",
        "unmatched_catalog_count",
        "source_immutable",
        "legacy_fallback_enabled",
    }
    assert payload["state"] == "completed"
    assert payload["reconnected_catalog_count"] == 2
    assert payload["unmatched_catalog_count"] == 0
    assert payload["source_immutable"] is True
    assert payload["legacy_fallback_enabled"] is False
    from sqlalchemy import select

    from handler.database.base_handler import sync_session
    from models.storage import LegacyMigrationCatalogChange

    with sync_session() as database:
        changes = database.scalars(
            select(LegacyMigrationCatalogChange)
            .where(LegacyMigrationCatalogChange.migration_id == payload["migration_id"])
            .order_by(
                LegacyMigrationCatalogChange.entity_kind,
                LegacyMigrationCatalogChange.entity_id,
            )
        ).all()
    assert [
        (change.entity_kind, change.prior_missing_from_fs) for change in changes
    ] == [
        ("rom", True),
        ("rom", True),
    ]
    serialized = str(payload).lower()
    assert str(tmp_path).lower() not in serialized
    assert "relative_path" not in serialized
    assert "raw" not in serialized


def test_migration_rejects_same_metadata_source_substitution_before_owned_writes(
    tmp_path: Path, platform, admin_user
):
    from sqlalchemy import func, select

    from handler.database.base_handler import sync_session
    from handler.database.legacy_migration_handler import LegacyDetectionResultError
    from models.rom import Rom
    from models.storage import LegacyMigration, PlatformStorageMapping

    handler, result, now = _seed_impact_preview(tmp_path, platform, admin_user)
    impact = handler.preview_migration_impact(
        result.id, platform_id=platform.id, expected_result_version=1, now=now
    )
    source = tmp_path / "roms" / platform.fs_slug / "one.gb"
    metadata = source.stat()
    source.write_bytes(b"ONE")
    os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))

    with pytest.raises(LegacyDetectionResultError) as stale:
        handler.migrate_platform(
            impact.confirmation,
            actor_user_id=admin_user.id,
            actor_display_name=admin_user.username,
            now=now,
        )
    assert stale.value.code == "legacy_impact_stale"
    with sync_session() as database:
        assert database.scalar(select(func.count(PlatformStorageMapping.id))) == 0
        assert database.scalar(select(func.count(LegacyMigration.id))) == 0
        roms = database.scalars(select(Rom).where(Rom.platform_id == platform.id)).all()
        assert roms
        assert all(rom.missing_from_fs for rom in roms)


def test_migration_rejects_equal_count_catalog_replacement_before_owned_writes(
    tmp_path: Path, platform, admin_user
):
    from sqlalchemy import func, select

    from handler.database.base_handler import sync_session
    from handler.database.legacy_migration_handler import LegacyDetectionResultError
    from models.rom import Rom
    from models.storage import LegacyMigration, PlatformStorageMapping

    handler, result, now = _seed_impact_preview(tmp_path, platform, admin_user)
    impact = handler.preview_migration_impact(
        result.id, platform_id=platform.id, expected_result_version=1, now=now
    )
    with sync_session.begin() as database:
        victim = database.scalars(
            select(Rom).where(Rom.platform_id == platform.id).order_by(Rom.id)
        ).first()
        victim.fs_name = "replacement.gb"
        victim.fs_name_no_tags = "replacement"
        victim.fs_name_no_ext = "replacement"
        victim.name = "Replacement"

    with pytest.raises(LegacyDetectionResultError) as stale:
        handler.migrate_platform(
            impact.confirmation,
            actor_user_id=admin_user.id,
            actor_display_name=admin_user.username,
            now=now,
        )
    assert stale.value.code == "legacy_impact_stale"
    with sync_session() as database:
        assert database.scalar(select(func.count(PlatformStorageMapping.id))) == 0
        assert database.scalar(select(func.count(LegacyMigration.id))) == 0


@pytest.mark.parametrize(
    "mutation",
    ["rename", "disappearance", "unreadable", "symlink"],
)
def test_migration_reobserves_canonical_source_drift_before_owned_writes(
    tmp_path: Path, platform, admin_user, monkeypatch, mutation
):
    from sqlalchemy import func, select

    from exceptions.storage_exceptions import DescriptorHashShortReadError
    from handler.database.base_handler import sync_session
    from handler.database.legacy_migration_handler import LegacyDetectionResultError
    from handler.storage import legacy_migration as detector
    from models.storage import LegacyMigration, PlatformStorageMapping

    handler, result, now = _seed_impact_preview(tmp_path, platform, admin_user)
    impact = handler.preview_migration_impact(
        result.id, platform_id=platform.id, expected_result_version=1, now=now
    )
    source = tmp_path / "roms" / platform.fs_slug / "one.gb"
    if mutation == "rename":
        source.rename(source.with_name("renamed.gb"))
    elif mutation == "disappearance":
        source.unlink()
    elif mutation == "symlink":
        secret = tmp_path / "private-source"
        secret.write_bytes(b"one")
        source.unlink()
        source.symlink_to(secret)
    else:

        def unreadable(*_args, **_kwargs):
            raise DescriptorHashShortReadError()

        monkeypatch.setattr(detector, "hash_descriptor_file", unreadable)

    with pytest.raises(LegacyDetectionResultError) as stale:
        handler.migrate_platform(
            impact.confirmation,
            actor_user_id=admin_user.id,
            actor_display_name=admin_user.username,
            now=now,
        )
    assert stale.value.code == "legacy_impact_stale"
    assert str(tmp_path) not in str(stale.value)
    with sync_session() as database:
        assert database.scalar(select(func.count(PlatformStorageMapping.id))) == 0
        assert database.scalar(select(func.count(LegacyMigration.id))) == 0
