"""Add parent-ROM owned media catalog and cleanup intents.

Revision ID: 0127_parent_rom_owned_media
Revises: 0128_add_steam_metadata
"""

import sqlalchemy as sa
from alembic import op

revision = "0127_parent_rom_owned_media"
down_revision = "0128_add_steam_metadata"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    origin = sa.Enum(
        "upload",
        "provider",
        name="romownedmediaorigin",
        native_enum=False,
        create_constraint=True,
    )
    state = sa.Enum(
        "active",
        "tombstoned",
        name="romownedmediastate",
        native_enum=False,
        create_constraint=True,
    )
    surface = sa.Enum(
        "overview",
        "background",
        "soundtrack",
        name="romownedmediasurface",
        native_enum=False,
        create_constraint=True,
    )
    cleanup_state = sa.Enum(
        "pending",
        "processing",
        "completed",
        "failed",
        name="ownedmediacleanupstate",
        native_enum=False,
        create_constraint=True,
    )
    op.create_table(
        "rom_owned_media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("origin", origin, nullable=False),
        sa.Column("state", state, nullable=False, server_default="active"),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("owned_path", sa.String(length=700), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("provider_media_id", sa.String(length=450), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "owned_path IS NULL OR (owned_path <> '' AND owned_path NOT LIKE '/%' AND owned_path NOT LIKE '%..%')",
            name="ck_rom_owned_media_owned_path_relative",
        ),
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rom_id",
            "provider",
            "provider_media_id",
            name="uq_rom_owned_media_provider_identity",
        ),
    )
    op.create_index(
        "idx_rom_owned_media_rom_state", "rom_owned_media", ["rom_id", "state"]
    )
    op.create_index("idx_rom_owned_media_origin", "rom_owned_media", ["origin"])
    op.create_table(
        "rom_owned_media_placements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column("surface", surface, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "position >= 0", name="ck_rom_owned_media_placements_position"
        ),
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["media_id"], ["rom_owned_media.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "media_id", "surface", name="uq_rom_owned_media_placements_media_surface"
        ),
        sa.UniqueConstraint(
            "rom_id",
            "surface",
            "position",
            name="uq_rom_owned_media_placements_rom_surface_position",
        ),
    )
    op.create_index(
        "idx_rom_owned_media_placements_rom_surface_position",
        "rom_owned_media_placements",
        ["rom_id", "surface", "position"],
    )
    op.create_table(
        "owned_media_cleanup_intents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column("owned_path", sa.String(length=700), nullable=False),
        sa.Column("state", cleanup_state, nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("next_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 8",
            name="ck_owned_media_cleanup_intents_attempt_count",
        ),
        sa.CheckConstraint(
            "owned_path <> '' AND owned_path NOT LIKE '/%' AND owned_path NOT LIKE '%..%'",
            name="ck_owned_media_cleanup_intents_owned_path_relative",
        ),
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owned_path", name="uq_owned_media_cleanup_intents_owned_path"
        ),
    )
    op.create_index(
        "idx_owned_media_cleanup_intents_state_next_attempt",
        "owned_media_cleanup_intents",
        ["state", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_owned_media_cleanup_intents_state_next_attempt",
        table_name="owned_media_cleanup_intents",
    )
    op.drop_table("owned_media_cleanup_intents")
    op.drop_index(
        "idx_rom_owned_media_placements_rom_surface_position",
        table_name="rom_owned_media_placements",
    )
    op.drop_table("rom_owned_media_placements")
    op.drop_index("idx_rom_owned_media_origin", table_name="rom_owned_media")
    op.drop_index("idx_rom_owned_media_rom_state", table_name="rom_owned_media")
    op.drop_table("rom_owned_media")
