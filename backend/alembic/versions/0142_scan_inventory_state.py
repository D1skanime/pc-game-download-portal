"""Add compact advisory scan inventory and retry state.

Revision ID: 0142_scan_inventory_state
Revises: 0141_queue_target_precision
"""

import sqlalchemy as sa
from alembic import op

revision = "0142_scan_inventory_state"
down_revision = "0141_queue_target_precision"
branch_labels = None
depends_on = None


def identity_columns():
    return [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("identity_digest", sa.String(64), nullable=False),
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("storage_root_id", sa.Integer(), nullable=False),
        sa.Column("mapping_relative_path", sa.String(700), nullable=False),
        sa.Column("mapping_revision", sa.Integer(), nullable=False),
        sa.Column("binding_digest", sa.String(64), nullable=False),
        sa.Column("game_relative_path", sa.String(700), nullable=False),
        sa.Column("path_digest", sa.String(64), nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("rom_incarnation", sa.String(32), nullable=False),
        sa.Column("inventory_version", sa.Integer(), nullable=False),
        sa.Column("classifier_version", sa.Integer(), nullable=False),
        sa.Column("policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        "scan_inventory_baselines",
        *identity_columns(),
        sa.Column("inventory_digest", sa.String(64), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column("validated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("reusable", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("identity_digest", name="uq_scan_inventory_identity"),
    )
    op.create_table(
        "scan_metadata_retries",
        *identity_columns(),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("normalized_query", sa.String(700), nullable=False),
        sa.Column("locale", sa.String(32), nullable=False),
        sa.Column("config_fingerprint", sa.String(64), nullable=False),
        sa.Column("next_eligible_at", sa.DateTime(), nullable=True),
        sa.Column("last_invoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_request_at", sa.DateTime(), nullable=True),
        sa.Column("no_match_streak", sa.Integer(), nullable=False),
        sa.Column("transient_streak", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("config_blocked", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("identity_digest", name="uq_scan_metadata_retry_identity"),
    )


def downgrade():
    op.drop_table("scan_metadata_retries")
    op.drop_table("scan_inventory_baselines")
