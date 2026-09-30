"""Add selected local soundtrack background audio.

Revision ID: 0130_local_background_audio
Revises: 0129_backfill_legacy_rom_owned_media
"""

import sqlalchemy as sa
from alembic import op

revision = "0130_local_background_audio"
down_revision = "0129_backfill_legacy_rom_owned_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rom_local_background_audio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("rom_file_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rom_file_id"], ["rom_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rom_id", "rom_file_id", name="uq_rom_local_background_audio_file"
        ),
    )
    op.create_index(
        "idx_rom_local_background_audio_rom",
        "rom_local_background_audio",
        ["rom_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_rom_local_background_audio_rom",
        table_name="rom_local_background_audio",
    )
    op.drop_table("rom_local_background_audio")
