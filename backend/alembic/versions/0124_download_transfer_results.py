"""Persist explicit browser transfer session results.

Revision ID: 0124_download_transfer_results
Revises: 0123_download_transfer_sessions
"""

import sqlalchemy as sa
from alembic import op

revision = "0124_download_transfer_results"
down_revision = "0123_download_transfer_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "download_transfer_sessions",
        sa.Column("result", sa.String(16), nullable=True),
    )
    op.create_check_constraint(
        "ck_download_transfer_session_result",
        "download_transfer_sessions",
        "result IS NULL OR result IN ('success', 'partial', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_download_transfer_session_result",
        "download_transfer_sessions",
        type_="check",
    )
    op.drop_column("download_transfer_sessions", "result")
