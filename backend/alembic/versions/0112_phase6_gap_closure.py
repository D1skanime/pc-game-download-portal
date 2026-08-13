"""Bind legacy migration state to exact source and catalog fingerprints.

Revision ID: 0112_phase6_gap_closure
Revises: 0111_safe_lifecycle
Create Date: 2026-08-13 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0112_phase6_gap_closure"
down_revision = "0111_safe_lifecycle"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    ]


def _ensure_gap_closure_downgrade() -> None:
    connection = op.get_bind()
    fingerprints = int(
        connection.scalar(
            sa.text(
                "SELECT COUNT(*) FROM legacy_detection_results "
                "WHERE source_fingerprint IS NOT NULL"
            )
        )
        or 0
    )
    changes = int(
        connection.scalar(
            sa.text("SELECT COUNT(*) FROM legacy_migration_catalog_changes")
        )
        or 0
    )
    if fingerprints or changes:
        raise RuntimeError(
            "Cannot downgrade legacy fingerprint state while durable evidence exists"
        )


def _invalidate_fingerprintless_selectable_results() -> None:
    op.execute(
        sa.text(
            "UPDATE legacy_detection_results "
            "SET selectable = FALSE, lower_bound = TRUE, "
            "state = 'manual_mapping_required', "
            "safe_problem_code = 'fingerprint_refresh_required', "
            "version = version + 1 "
            "WHERE selectable = TRUE"
        )
    )


def _restore_fingerprint_refresh_markers() -> None:
    op.execute(
        sa.text(
            "UPDATE legacy_detection_results "
            "SET selectable = TRUE, lower_bound = FALSE, state = 'detected', "
            "safe_problem_code = NULL, version = version - 1 "
            "WHERE selectable = FALSE AND lower_bound = TRUE "
            "AND state = 'manual_mapping_required' "
            "AND safe_problem_code = 'fingerprint_refresh_required' "
            "AND source_fingerprint IS NULL AND version > 1"
        )
    )


def upgrade() -> None:
    with op.batch_alter_table("legacy_detection_results") as batch_op:
        batch_op.add_column(sa.Column("source_fingerprint", sa.String(64)))

    _invalidate_fingerprintless_selectable_results()

    with op.batch_alter_table("legacy_detection_results") as batch_op:
        batch_op.create_check_constraint(
            "ck_legacy_detection_results_source_fingerprint_format",
            "source_fingerprint IS NULL OR "
            "(CHAR_LENGTH(source_fingerprint) = 64 AND "
            "source_fingerprint = LOWER(source_fingerprint))",
        )
        batch_op.create_check_constraint(
            "ck_legacy_detection_results_source_fingerprint_selectable",
            "(selectable = false AND source_fingerprint IS NULL) OR "
            "(selectable = true AND source_fingerprint IS NOT NULL "
            "AND lower_bound = false)",
        )

    op.create_table(
        "legacy_migration_catalog_changes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("migration_id", sa.Integer(), nullable=False),
        sa.Column("entity_kind", sa.String(16), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("prior_missing_from_fs", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "entity_kind IN ('rom', 'rom_file')",
            name="ck_legacy_migration_catalog_changes_entity_kind",
        ),
        sa.CheckConstraint(
            "entity_id > 0",
            name="ck_legacy_migration_catalog_changes_entity_id",
        ),
        sa.ForeignKeyConstraint(
            ["migration_id"],
            ["legacy_migrations.id"],
            name="fk_legacy_migration_catalog_changes_migration_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_legacy_migration_catalog_changes"),
        sa.UniqueConstraint(
            "migration_id",
            "entity_kind",
            "entity_id",
            name="uq_legacy_migration_catalog_changes_identity",
        ),
    )
    op.create_index(
        "ix_legacy_migration_catalog_changes_order",
        "legacy_migration_catalog_changes",
        ["migration_id", "entity_kind", "entity_id"],
    )


def downgrade() -> None:
    _ensure_gap_closure_downgrade()
    op.drop_table("legacy_migration_catalog_changes")
    with op.batch_alter_table("legacy_detection_results") as batch_op:
        batch_op.drop_constraint(
            "ck_legacy_detection_results_source_fingerprint_selectable",
            type_="check",
        )

    _restore_fingerprint_refresh_markers()

    with op.batch_alter_table("legacy_detection_results") as batch_op:
        batch_op.drop_constraint(
            "ck_legacy_detection_results_source_fingerprint_format",
            type_="check",
        )
        batch_op.drop_column("source_fingerprint")
