from importlib import import_module

from sqlalchemy import inspect

from endpoints.responses.rom import RomFileSchema, RomSchema
from models import assets as asset_models
from models import play_session as play_session_models
from models import rom as rom_models
from models import storage as storage_models


def _catalog_lifecycle():
    return import_module("models.catalog_lifecycle")


def _foreign_key(column):
    foreign_keys = list(column.foreign_keys)
    assert len(foreign_keys) == 1
    return foreign_keys[0]


def test_retained_catalog_identity_is_bounded_and_reconnectable():
    model = _catalog_lifecycle().RetainedCatalogIdentity
    columns = model.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "platform_id",
        "detached_rom_id",
        "active_rom_id",
        "logical_path",
        "file_name",
        "crc_hash",
        "md5_hash",
        "sha1_hash",
        "version",
        "detached_by_user_id",
        "detached_at",
        "reconnected_at",
        "created_at",
        "updated_at",
    }
    assert columns.logical_path.type.length == 700
    assert columns.file_name.type.length == 450
    assert columns.active_rom_id.nullable is True
    assert _foreign_key(columns.platform_id).ondelete == "RESTRICT"
    assert _foreign_key(columns.active_rom_id).ondelete == "SET NULL"
    assert {
        "ix_retained_catalog_platform_logical_path",
        "ix_retained_catalog_active_rom_id",
    } <= {index.name for index in model.__table__.indexes}
    assert not any(
        token in column.name
        for column in columns
        for token in ("host", "container", "absolute", "snapshot", "row")
    )


def test_owned_cleanup_intent_is_typed_bounded_and_idempotent():
    lifecycle = _catalog_lifecycle()
    model = lifecycle.OwnedCleanupIntent
    columns = model.__table__.columns

    assert {
        "retained_catalog_id",
        "kind",
        "resource_id",
        "relative_path",
        "file_name",
        "deduplication_key",
        "state",
        "version",
        "attempt_count",
        "safe_error",
        "actor_user_id",
        "next_attempt_at",
        "completed_at",
    } <= set(columns.keys())
    assert columns.relative_path.type.length == 700
    assert columns.file_name.type.length == 450
    assert columns.safe_error.type.length == 1000
    assert _foreign_key(columns.retained_catalog_id).ondelete == "RESTRICT"
    assert {
        "cover",
        "manual",
        "screenshot",
        "resource",
    } <= {kind.value for kind in lifecycle.OwnedCleanupKind}
    assert {"pending", "processing", "completed", "failed"} == {
        state.value for state in lifecycle.OwnedCleanupState
    }
    constraint_names = {constraint.name for constraint in model.__table__.constraints}
    assert "uq_owned_cleanup_intents_deduplication_key" in constraint_names
    assert "ck_owned_cleanup_intents_state" in constraint_names
    assert "ck_owned_cleanup_intents_kind" in constraint_names


def test_save_and_state_detachment_preserves_retained_ownership():
    retained_table = "retained_catalog_identities.id"

    for model in (asset_models.Save, asset_models.State):
        columns = model.__table__.columns
        assert columns.rom_id.nullable is True
        assert _foreign_key(columns.rom_id).ondelete == "SET NULL"
        assert columns.retained_catalog_id.nullable is True
        assert (
            _foreign_key(columns.retained_catalog_id).target_fullname == retained_table
        )
        assert _foreign_key(columns.retained_catalog_id).ondelete == "RESTRICT"
        assert inspect(model).relationships.retained_catalog.back_populates in {
            "saves",
            "states",
        }

    assert asset_models.Screenshot.__table__.columns.rom_id.nullable is False
    assert (
        _foreign_key(asset_models.Screenshot.__table__.columns.rom_id).ondelete
        == "CASCADE"
    )


def test_play_session_stays_attributable_after_rom_detachment():
    model = play_session_models.PlaySession
    columns = model.__table__.columns

    assert columns.rom_id.nullable is True
    assert _foreign_key(columns.rom_id).ondelete == "SET NULL"
    assert columns.retained_catalog_id.nullable is True
    assert (
        _foreign_key(columns.retained_catalog_id).target_fullname
        == "retained_catalog_identities.id"
    )
    assert _foreign_key(columns.retained_catalog_id).ondelete == "RESTRICT"
    assert (
        inspect(model).relationships.retained_catalog.back_populates == "play_sessions"
    )
    assert "ix_play_sessions_retained_catalog" in {
        index.name for index in model.__table__.indexes
    }


def test_detection_result_is_bounded_expiring_and_path_safe():
    model = storage_models.LegacyDetectionResult
    columns = model.__table__.columns

    assert {
        "platform_id",
        "storage_root_id",
        "state",
        "proposed_relative_path",
        "observed_files",
        "observed_bytes",
        "lower_bound",
        "selectable",
        "safe_problem_code",
        "observed_mapping_id",
        "observed_mapping_version",
        "version",
        "actor_user_id",
        "expires_at",
        "completed_at",
    } <= set(columns.keys())
    assert columns.proposed_relative_path.type.length == 700
    assert columns.safe_problem_code.type.length == 64
    assert columns.expires_at.nullable is False
    assert {
        "detected",
        "manual_mapping_required",
        "empty",
        "unreadable",
        "unreachable",
        "unsafe",
        "conflict",
    } == {state.value for state in storage_models.LegacyDetectionState}
    assert not any(
        token in column.name
        for column in columns
        for token in ("host", "container", "absolute", "raw", "snapshot")
    )


def test_detection_result_fingerprint_requires_a_complete_safe_observation():
    model = storage_models.LegacyDetectionResult
    columns = model.__table__.columns

    assert columns.source_fingerprint.type.length == 64
    assert columns.source_fingerprint.nullable is True
    constraint_names = {constraint.name for constraint in model.__table__.constraints}
    assert "ck_legacy_detection_results_source_fingerprint_format" in constraint_names
    assert (
        "ck_legacy_detection_results_source_fingerprint_selectable" in constraint_names
    )
    assert not any(
        token in column.name
        for column in columns
        for token in ("host", "container", "absolute", "raw", "snapshot", "content")
    )


def test_migration_state_is_versioned_rollbackable_and_first_use_nullable():
    model = storage_models.LegacyMigration
    columns = model.__table__.columns

    assert {
        "detection_result_id",
        "platform_id",
        "storage_root_id",
        "mapping_id",
        "relative_path",
        "state",
        "version",
        "actor_user_id",
        "prior_mapping_id",
        "prior_mapping_version",
        "prior_mapping_active",
        "reconnected_catalog_count",
        "unmatched_catalog_count",
        "expires_at",
        "completed_at",
        "first_used_at",
        "first_use_operation",
        "rolled_back_at",
    } <= set(columns.keys())
    assert columns.relative_path.type.length == 700
    assert columns.first_used_at.nullable is True
    assert columns.first_use_operation.nullable is True
    assert columns.rolled_back_at.nullable is True
    assert {
        "pending",
        "completed",
        "rolled_back",
        "failed",
    } == {state.value for state in storage_models.LegacyMigrationState}
    constraint_names = {constraint.name for constraint in model.__table__.constraints}
    assert "ck_legacy_migrations_first_use_pair" in constraint_names
    assert "ck_legacy_migrations_state" in constraint_names
    assert "ck_legacy_migrations_version" in constraint_names


def test_migration_owns_ordered_relationship_free_exact_catalog_changes():
    model = storage_models.LegacyMigrationCatalogChange
    columns = model.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "migration_id",
        "entity_kind",
        "entity_id",
        "prior_missing_from_fs",
        "entity_incarnation_token",
        "parent_rom_id",
        "parent_incarnation_token",
        "lineage_valid",
        "created_at",
        "updated_at",
    }
    assert columns.entity_kind.type.length == 16
    assert columns.entity_id.nullable is False
    assert columns.prior_missing_from_fs.nullable is False
    assert _foreign_key(columns.migration_id).target_fullname == "legacy_migrations.id"
    assert _foreign_key(columns.migration_id).ondelete == "CASCADE"
    assert len(columns.entity_id.foreign_keys) == 0
    constraint_names = {constraint.name for constraint in model.__table__.constraints}
    assert "ck_legacy_migration_catalog_changes_entity_kind" in constraint_names
    assert "ck_legacy_migration_catalog_changes_entity_id" in constraint_names
    assert "ck_lmcc_lineage_shape" in constraint_names
    assert "uq_legacy_migration_catalog_changes_identity" in constraint_names
    assert "ix_legacy_migration_catalog_changes_order" in {
        index.name for index in model.__table__.indexes
    }
    relationship = inspect(storage_models.LegacyMigration).relationships.catalog_changes
    assert relationship.back_populates == "migration"
    assert "delete-orphan" in relationship.cascade
    assert not any(
        token in column.name
        for column in columns
        for token in ("path", "file", "host", "raw", "snapshot", "content", "row")
    )


def test_catalog_incarnation_tokens_are_private_bounded_and_unique():
    for model, index_name in (
        (rom_models.Rom, "uq_roms_incarnation_token"),
        (rom_models.RomFile, "uq_rom_files_incarnation_token"),
    ):
        column = model.__table__.columns.incarnation_token
        assert column.type.length == 32
        assert column.nullable is False
        index = next(
            item for item in model.__table__.indexes if item.name == index_name
        )
        assert index.unique is True

    assert "incarnation_token" not in RomSchema.model_fields
    assert "incarnation_token" not in RomFileSchema.model_fields


def test_catalog_change_lineage_shape_is_bounded_and_relationship_free():
    columns = storage_models.LegacyMigrationCatalogChange.__table__.columns

    assert columns.entity_incarnation_token.type.length == 32
    assert columns.parent_incarnation_token.type.length == 32
    assert columns.lineage_valid.nullable is False
    assert len(columns.parent_rom_id.foreign_keys) == 0
    assert len(columns.entity_incarnation_token.foreign_keys) == 0
    assert len(columns.parent_incarnation_token.foreign_keys) == 0


def test_lifecycle_models_hold_no_filesystem_mutation_authority(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"immutable-source")
    before = (source.stat().st_mode, source.stat().st_size, source.read_bytes())

    lifecycle = _catalog_lifecycle()
    lifecycle.RetainedCatalogIdentity(
        platform_id=1,
        detached_rom_id=2,
        logical_path="roms/snes/game.zip",
        file_name="game.zip",
        version=1,
        detached_by_user_id=3,
    )
    storage_models.LegacyDetectionResult(
        platform_id=1,
        storage_root_id=2,
        state=storage_models.LegacyDetectionState.DETECTED,
        proposed_relative_path="roms/snes",
        observed_files=1,
        observed_bytes=len(source.read_bytes()),
        lower_bound=False,
        selectable=True,
        version=1,
        actor_user_id=3,
    )

    after = (source.stat().st_mode, source.stat().st_size, source.read_bytes())
    assert after == before
