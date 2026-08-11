"""Add versioned mapping lifecycle and immutable audit snapshots.

Revision ID: 0109_mapping_admin_contracts
Revises: 0108_storage_foundation
Create Date: 2026-08-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0109_mapping_admin_contracts"
down_revision = "0108_storage_foundation"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        )
    ]


def upgrade() -> None:
    connection = op.get_bind()
    existing_columns = {
        column["name"]
        for column in sa.inspect(connection).get_columns("platform_storage_mappings")
    }
    with op.batch_alter_table("platform_storage_mappings") as batch_op:
        if "active" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "active", sa.Boolean(), server_default=sa.true(), nullable=True
                )
            )
        if "version" not in existing_columns:
            batch_op.add_column(
                sa.Column("version", sa.Integer(), server_default="1", nullable=True)
            )
    connection.execute(
        sa.text(
            "UPDATE platform_storage_mappings SET active = :active, version = 1 WHERE active IS NULL OR version IS NULL"
        ),
        {"active": True},
    )
    with op.batch_alter_table("platform_storage_mappings") as batch_op:
        batch_op.alter_column(
            "active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        )
        batch_op.alter_column(
            "version", existing_type=sa.Integer(), nullable=False, server_default="1"
        )
        batch_op.create_index(
            "ix_platform_storage_mappings_platform_id", ["platform_id"], unique=False
        )
        batch_op.drop_constraint(
            "uq_platform_storage_mappings_platform_id", type_="unique"
        )
        batch_op.drop_constraint(
            "uq_platform_storage_mappings_root_relative_path", type_="unique"
        )
        batch_op.create_index(
            "ix_platform_storage_mappings_active_platform",
            ["active", "platform_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_platform_storage_mappings_active_root_path",
            ["active", "storage_root_id", "relative_path"],
            unique=False,
        )

    op.create_table(
        "storage_mapping_audits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("actor_display_name", sa.String(length=255), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("old_storage_root_id", sa.Integer(), nullable=True),
        sa.Column("old_relative_path", sa.String(length=700), nullable=True),
        sa.Column("old_version", sa.Integer(), nullable=True),
        sa.Column("old_active", sa.Boolean(), nullable=True),
        sa.Column("new_storage_root_id", sa.Integer(), nullable=True),
        sa.Column("new_relative_path", sa.String(length=700), nullable=True),
        sa.Column("new_version", sa.Integer(), nullable=True),
        sa.Column("new_active", sa.Boolean(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "action IN ('create', 'update', 'remove', 'activate', 'deactivate')",
            name="ck_storage_mapping_audits_action",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_storage_mapping_audits"),
    )
    op.create_index(
        "ix_storage_mapping_audits_platform_created",
        "storage_mapping_audits",
        ["platform_id", "created_at"],
    )
    op.create_index(
        "ix_storage_mapping_audits_mapping_created",
        "storage_mapping_audits",
        ["mapping_id", "created_at"],
    )
    op.create_index(
        "ix_storage_mapping_audits_action_created",
        "storage_mapping_audits",
        ["action", "created_at"],
    )


def _ensure_pristine_lifecycle_for_downgrade() -> None:
    connection = op.get_bind()
    audit_count = connection.scalar(
        sa.text("SELECT COUNT(*) FROM storage_mapping_audits")
    )
    changed_count = connection.scalar(
        sa.text(
            "SELECT COUNT(*) FROM platform_storage_mappings WHERE active = :active OR version != 1"
        ),
        {"active": False},
    )
    platform_duplicates = connection.execute(
        sa.text(
            "SELECT platform_id FROM platform_storage_mappings GROUP BY platform_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    path_duplicates = connection.execute(
        sa.text(
            "SELECT storage_root_id, relative_path FROM platform_storage_mappings GROUP BY storage_root_id, relative_path HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if audit_count or changed_count or platform_duplicates or path_duplicates:
        raise RuntimeError(
            "Cannot downgrade mapping lifecycle while lifecycle history exists"
        )


def downgrade() -> None:
    _ensure_pristine_lifecycle_for_downgrade()
    op.drop_table("storage_mapping_audits")
    with op.batch_alter_table("platform_storage_mappings") as batch_op:
        batch_op.drop_index("ix_platform_storage_mappings_active_root_path")
        batch_op.drop_index("ix_platform_storage_mappings_active_platform")
        batch_op.create_unique_constraint(
            "uq_platform_storage_mappings_platform_id", ["platform_id"]
        )
        batch_op.drop_index("ix_platform_storage_mappings_platform_id")
        batch_op.create_unique_constraint(
            "uq_platform_storage_mappings_root_relative_path",
            ["storage_root_id", "relative_path"],
        )
        batch_op.drop_column("version")
        batch_op.drop_column("active")
