"""Keep dismissed browser transfer history for audit retention.

Revision ID: 0127_download_transfer_history_dismissal
Revises: 0126_download_transfer_attempt_lineage
"""

import sqlalchemy as sa
from alembic import op

revision = "0127_download_transfer_history_dismissal"
down_revision = "0126_download_transfer_attempt_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "download_transfer_sessions",
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "download_transfer_items",
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("download_transfer_items", "dismissed_at")
    op.drop_column("download_transfer_sessions", "dismissed_at")
