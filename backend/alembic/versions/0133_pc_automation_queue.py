"""Add the durable PC automation review queue.

Revision ID: 0133_pc_automation_queue
Revises: 0132_steam_scan_owned_media_state
"""

import sqlalchemy as sa
from alembic import op

revision = "0133_pc_automation_queue"
down_revision = "0132_steam_scan_owned_media_state"
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


def _target_kind() -> sa.Enum:
    return sa.Enum(
        "parent",
        "component",
        name="pcautomationtargetkind",
        native_enum=False,
        create_constraint=True,
        length=20,
    )


def _state() -> sa.Enum:
    return sa.Enum(
        "pending",
        "skipped",
        "retryable_failure",
        "claimed",
        name="pcautomationqueuestate",
        native_enum=False,
        create_constraint=True,
        length=32,
    )


def upgrade() -> None:
    target_kind = _target_kind()
    state = _state()
    target_kind.create(op.get_bind(), checkfirst=True)
    state.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "pc_automation_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target_identity", sa.String(length=80), nullable=False),
        sa.Column("target_kind", target_kind, nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=True),
        sa.Column("target_incarnation", sa.String(length=64), nullable=False),
        sa.Column("target_updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("normalized_query", sa.String(length=350), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("provider_candidate_id", sa.String(length=255), nullable=True),
        sa.Column("candidate_title", sa.String(length=350), nullable=True),
        sa.Column("candidate_cover_url", sa.Text(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("state", state, nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "(target_kind = 'parent' AND component_id IS NULL) OR "
            "(target_kind = 'component' AND component_id IS NOT NULL)",
            name="ck_pc_automation_queue_target_shape",
        ),
        sa.CheckConstraint(
            "retry_count >= 0 AND retry_count <= 8",
            name="ck_pc_automation_queue_retry_count",
        ),
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_identity", name="uq_pc_automation_queue_target"),
    )
    op.create_index(
        "idx_pc_automation_queue_pending",
        "pc_automation_queue",
        ["state", "next_retry_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_pc_automation_queue_pending", table_name="pc_automation_queue")
    op.drop_table("pc_automation_queue")
    _state().drop(op.get_bind(), checkfirst=True)
    _target_kind().drop(op.get_bind(), checkfirst=True)
