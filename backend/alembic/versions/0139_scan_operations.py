"""Durable scan intent, results and the seeded global execution slot.

Revision ID: 0139_scan_operations
Revises: 0138_rom_metadata_facet_roles_view
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.dialects.mysql import TIMESTAMP as MYSQL_TIMESTAMP

revision = "0139_scan_operations"
down_revision = "0138_rom_metadata_facet_roles_view"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_key", sa.String(96), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("command", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.String(36)),
        sa.Column("lease_owner", sa.String(64)),
        sa.Column(
            "lease_expires_at",
            sa.DateTime().with_variant(MYSQL_DATETIME(fsp=6), "mysql", "mariadb"),
        ),
        sa.Column(
            "dispatch_due",
            sa.DateTime().with_variant(MYSQL_DATETIME(fsp=6), "mysql", "mariadb"),
        ),
        sa.Column(
            "dispatch_claim_until",
            sa.DateTime().with_variant(MYSQL_DATETIME(fsp=6), "mysql", "mariadb"),
        ),
        sa.Column("dispatch_owner", sa.String(64)),
        sa.Column("rq_job_id", sa.String(100), nullable=False),
        sa.Column("intentional_cancel", sa.Boolean(), nullable=False),
        sa.Column("cause_code", sa.String(64)),
        sa.Column("next_action", sa.String(64)),
        sa.Column("scan_stats", sa.JSON(), nullable=False),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
        sa.Column("mutation_keys", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True).with_variant(
                MYSQL_TIMESTAMP(fsp=6), "mysql", "mariadb"
            ),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True).with_variant(
                MYSQL_TIMESTAMP(fsp=6), "mysql", "mariadb"
            ),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "actor_id", "request_key", name="uq_scan_operation_actor_key"
        ),
        sa.UniqueConstraint("rq_job_id", name="uq_scan_operation_job"),
        sa.CheckConstraint("version >= 1", name="ck_scan_operation_version"),
        sa.CheckConstraint(
            "state IN ('accepted', 'queued', 'running', 'stopping', 'cancelled', "
            "'interrupted', 'recovering', 'blocked', 'failed', 'completed', 'completed-with-warnings')",
            name="ck_scan_operation_state",
        ),
    )
    op.create_index(
        "ix_scan_operation_dispatch",
        "scan_operations",
        ["dispatch_due", "dispatch_claim_until"],
    )
    op.create_table(
        "scan_operation_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "operation_id",
            sa.String(36),
            sa.ForeignKey("scan_operations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_key", sa.String(96), nullable=False),
        sa.Column(
            "mapping_id",
            sa.Integer(),
            sa.ForeignKey("platform_storage_mappings.id"),
            nullable=False,
        ),
        sa.Column("expected_revision", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.String(700), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("cause_code", sa.String(64)),
        sa.Column("attempt_id", sa.String(36), nullable=False),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
        sa.Column("source_evidence", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True).with_variant(
                MYSQL_TIMESTAMP(fsp=6), "mysql", "mariadb"
            ),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True).with_variant(
                MYSQL_TIMESTAMP(fsp=6), "mysql", "mariadb"
            ),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "operation_id", "target_key", "provider", name="uq_scan_operation_item"
        ),
    )
    slot = op.create_table(
        "scan_execution_slot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column(
            "active_operation_id",
            sa.String(36),
            sa.ForeignKey("scan_operations.id", ondelete="SET NULL"),
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True).with_variant(
                MYSQL_TIMESTAMP(fsp=6), "mysql", "mariadb"
            ),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True).with_variant(
                MYSQL_TIMESTAMP(fsp=6), "mysql", "mariadb"
            ),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="ck_scan_execution_singleton"),
    )
    op.bulk_insert(slot, [{"id": 1, "active_operation_id": None, "version": 0}])


def downgrade() -> None:
    op.drop_table("scan_execution_slot")
    op.drop_table("scan_operation_items")
    op.drop_index("ix_scan_operation_dispatch", table_name="scan_operations")
    op.drop_table("scan_operations")
