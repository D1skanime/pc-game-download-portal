"""Add durable role and safe display label to parent-owned media.

Revision ID: 0128_owned_media_role_and_display_label
Revises: 0127_parent_rom_owned_media
"""

import sqlalchemy as sa
from alembic import op

revision = "0128_owned_media_role_and_display_label"
down_revision = "0127_parent_rom_owned_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role = sa.Enum(
        "screenshot",
        "artwork",
        "soundtrack",
        name="romownedmediarole",
        native_enum=False,
        create_constraint=True,
    )
    op.add_column(
        "rom_owned_media",
        sa.Column(
            "role",
            role,
            nullable=False,
            server_default="screenshot",
        ),
    )
    op.add_column(
        "rom_owned_media",
        sa.Column(
            "display_label",
            sa.String(length=255),
            nullable=False,
            server_default="Provider media",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE rom_owned_media "
            "SET role = 'artwork', display_label = 'Uploaded media' "
            "WHERE origin = 'upload'"
        )
    )
    with op.batch_alter_table("rom_owned_media") as batch_op:
        batch_op.create_check_constraint(
            "ck_rom_owned_media_display_label_nonempty", "display_label <> ''"
        )
        batch_op.alter_column("role", server_default=None)
        batch_op.alter_column("display_label", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("rom_owned_media") as batch_op:
        batch_op.drop_constraint(
            "ck_rom_owned_media_display_label_nonempty", type_="check"
        )
        batch_op.drop_column("display_label")
        batch_op.drop_column("role")
