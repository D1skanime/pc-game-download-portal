"""Add durable operator suppression state to provider-owned media.

Revision ID: 0132_steam_scan_owned_media_state
Revises: 0131_owned_background_audio
"""

import sqlalchemy as sa
from alembic import op

revision = "0132_steam_scan_owned_media_state"
down_revision = "0131_owned_background_audio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("rom_owned_media") as batch_op:
        batch_op.add_column(
            sa.Column(
                "operator_suppressed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.alter_column("operator_suppressed", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("rom_owned_media") as batch_op:
        batch_op.drop_column("operator_suppressed")
