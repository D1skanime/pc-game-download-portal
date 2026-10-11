"""Preserve fractional seconds for ROM optimistic versioning.

Revision ID: 0134_rom_updated_at_fractional_seconds
Revises: 0133_pc_automation_queue
"""

from alembic import op

revision = "0134_rom_updated_at_fractional_seconds"
down_revision = "0133_pc_automation_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE roms MODIFY COLUMN updated_at "
        "TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) "
        "ON UPDATE CURRENT_TIMESTAMP(6)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE roms MODIFY COLUMN updated_at "
        "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP "
        "ON UPDATE CURRENT_TIMESTAMP"
    )
