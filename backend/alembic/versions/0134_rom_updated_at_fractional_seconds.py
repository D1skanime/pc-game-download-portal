"""Preserve fractional seconds for ROM optimistic versioning.

Revision ID: 0134_rom_updated_at_fractional_seconds
Revises: 0133_pc_automation_queue
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP

from utils.database import is_postgresql

revision = "0134_rom_updated_at_fractional_seconds"
down_revision = "0133_pc_automation_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if is_postgresql(op.get_bind()):
        op.alter_column(
            "roms",
            "updated_at",
            type_=TIMESTAMP(timezone=True, precision=6),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        op.execute("""CREATE FUNCTION roms_touch_updated_at() RETURNS trigger AS $$
        BEGIN
            IF NEW IS DISTINCT FROM OLD AND NEW.updated_at = OLD.updated_at THEN
                NEW.updated_at = statement_timestamp();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER roms_touch_updated_at BEFORE UPDATE ON roms
        FOR EACH ROW EXECUTE FUNCTION roms_touch_updated_at()""")
        return
    op.execute(
        "ALTER TABLE roms MODIFY COLUMN updated_at "
        "TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) "
        "ON UPDATE CURRENT_TIMESTAMP(6)"
    )


def downgrade() -> None:
    if is_postgresql(op.get_bind()):
        op.execute("DROP TRIGGER roms_touch_updated_at ON roms")
        op.execute("DROP FUNCTION roms_touch_updated_at()")
        op.alter_column(
            "roms",
            "updated_at",
            type_=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )
        return
    op.execute(
        "ALTER TABLE roms MODIFY COLUMN updated_at "
        "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP "
        "ON UPDATE CURRENT_TIMESTAMP"
    )
