"""Retain manifest-referenced missing PC component members.

Revision ID: 0125_pc_component_manifest_members_missing_from_fs
Revises: 0124_download_transfer_results
"""

import sqlalchemy as sa
from alembic import op

revision = "0125_pc_component_manifest_members_missing_from_fs"
down_revision = "0124_download_transfer_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("rom_component_manifest_members") as batch_op:
        batch_op.add_column(
            sa.Column(
                "missing_from_fs",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("rom_component_manifest_members") as batch_op:
        batch_op.drop_column("missing_from_fs")
