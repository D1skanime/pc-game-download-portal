"""Add locale-scoped manual metadata to PC components.

Revision ID: 0135_component_manual_metadata
Revises: 0134_rom_updated_at_fractional_seconds
"""

import sqlalchemy as sa
from alembic import op

revision = "0135_component_manual_metadata"
down_revision = "0134_rom_updated_at_fractional_seconds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rom_component_metadata",
        sa.Column("manual_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rom_component_metadata", "manual_metadata")
