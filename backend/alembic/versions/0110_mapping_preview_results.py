"""Add durable mapping preview results."""

import sqlalchemy as sa
from alembic import op

revision = "0110_mapping_preview_results"
down_revision = "0109_mapping_admin_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mapping_previews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("observed_files", sa.Integer(), nullable=False),
        sa.Column("observed_directories", sa.Integer(), nullable=False),
        sa.Column("observed_bytes", sa.Integer(), nullable=False),
        sa.Column("lower_bound", sa.Boolean(), nullable=False),
        sa.Column("budget_reason", sa.String(length=32), nullable=True),
        sa.Column("problems", sa.JSON(), nullable=False),
        sa.Column("observed_revision", sa.Integer(), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["mapping_id"], ["platform_storage_mappings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mapping_previews"),
    )
    op.create_index(
        "ix_mapping_previews_mapping_id",
        "mapping_previews",
        ["mapping_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("mapping_previews")
