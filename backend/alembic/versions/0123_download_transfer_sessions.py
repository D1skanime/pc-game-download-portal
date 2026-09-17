"""Persist path-free browser transfer observations.

Revision ID: 0123_download_transfer_sessions
Revises: 0122_download_archive_sets
"""

import sqlalchemy as sa
from alembic import op

revision = "0123_download_transfer_sessions"
down_revision = "0122_download_archive_sets"
branch_labels = None
depends_on = None


def _timestamps():
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


def upgrade() -> None:
    op.create_table(
        "download_transfer_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("selected_items", sa.Integer(), nullable=False),
        sa.Column("selected_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "observed_bytes", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_activity_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["manifest_id"], ["download_manifests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "mode IN ('standard', 'enhanced')", name="ck_download_transfer_session_mode"
        ),
        sa.CheckConstraint(
            "selected_items >= 0 AND selected_bytes >= 0 AND observed_bytes >= 0",
            name="ck_download_transfer_session_counts",
        ),
    )
    op.create_index(
        "idx_download_transfer_sessions_owner_time",
        "download_transfer_sessions",
        ["user_id", "started_at"],
    )
    op.create_index(
        "idx_download_transfer_sessions_manifest",
        "download_transfer_sessions",
        ["manifest_id"],
    )
    op.create_table(
        "download_transfer_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("manifest_member_id", sa.Integer(), nullable=False),
        sa.Column("manifest_member_public_id", sa.String(36), nullable=False),
        sa.Column("expected_bytes", sa.BigInteger(), nullable=False),
        sa.Column("expected_sha256", sa.String(64), nullable=True),
        sa.Column(
            "observed_bytes", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["session_id"], ["download_transfer_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["manifest_member_id"],
            ["download_manifest_members.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "manifest_member_id", name="uq_download_transfer_item_member"
        ),
        sa.CheckConstraint(
            "expected_bytes >= 0 AND observed_bytes >= 0",
            name="ck_download_transfer_item_counts",
        ),
    )
    op.create_index(
        "idx_download_transfer_items_session", "download_transfer_items", ["session_id"]
    )
    op.create_table(
        "download_transfer_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("observed_bytes", sa.BigInteger(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["session_id"], ["download_transfer_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["download_transfer_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "ordinal", name="uq_download_transfer_event_ordinal"
        ),
        sa.CheckConstraint(
            "observed_bytes >= 0", name="ck_download_transfer_event_bytes"
        ),
    )
    op.create_index(
        "idx_download_transfer_events_item",
        "download_transfer_events",
        ["item_id", "ordinal"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_download_transfer_events_item", table_name="download_transfer_events"
    )
    op.drop_table("download_transfer_events")
    op.drop_index(
        "idx_download_transfer_items_session", table_name="download_transfer_items"
    )
    op.drop_table("download_transfer_items")
    op.drop_index(
        "idx_download_transfer_sessions_manifest",
        table_name="download_transfer_sessions",
    )
    op.drop_index(
        "idx_download_transfer_sessions_owner_time",
        table_name="download_transfer_sessions",
    )
    op.drop_table("download_transfer_sessions")
