"""Link browser download retry attempts.

Revision ID: 0126_download_transfer_attempt_lineage
Revises: 0125_pc_component_manifest_members_missing_from_fs
"""

import sqlalchemy as sa
from alembic import op

revision = "0126_download_transfer_attempt_lineage"
down_revision = "0125_pc_component_manifest_members_missing_from_fs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "download_transfer_sessions",
        sa.Column("parent_session_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "download_transfer_sessions",
        sa.Column(
            "attempt_no", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
    )
    op.create_index(
        "ix_download_transfer_sessions_parent_session_id",
        "download_transfer_sessions",
        ["parent_session_id"],
    )
    op.create_foreign_key(
        "fk_download_transfer_sessions_parent_session_id",
        "download_transfer_sessions",
        "download_transfer_sessions",
        ["parent_session_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_download_transfer_sessions_parent_session_id",
        "download_transfer_sessions",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_download_transfer_sessions_parent_session_id",
        table_name="download_transfer_sessions",
    )
    op.drop_column("download_transfer_sessions", "attempt_no")
    op.drop_column("download_transfer_sessions", "parent_session_id")
