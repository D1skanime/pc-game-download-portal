"""Bind download manifests to their canonical ROM.

Revision ID: 0120_download_manifest_rom
Revises: 0119_download_manifests
Create Date: 2026-09-15 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0120_download_manifest_rom"
down_revision = "0119_download_manifests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("download_manifests") as batch_op:
        batch_op.add_column(sa.Column("rom_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_download_manifests_rom_id_roms",
            "roms",
            ["rom_id"],
            ["id"],
            ondelete="CASCADE",
        )
    op.execute(
        "UPDATE download_manifests SET rom_id = ("
        "SELECT rom_components.rom_id "
        "FROM download_manifest_components AS components "
        "JOIN rom_components ON rom_components.id = components.component_id "
        "WHERE components.manifest_id = download_manifests.id)"
    )
    with op.batch_alter_table("download_manifests") as batch_op:
        batch_op.alter_column("rom_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("download_manifests") as batch_op:
        batch_op.drop_constraint(
            "fk_download_manifests_rom_id_roms", type_="foreignkey"
        )
        batch_op.drop_column("rom_id")
