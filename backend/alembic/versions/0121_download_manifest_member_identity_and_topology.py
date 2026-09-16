"""Enforce download-manifest member identity and ownership topology.

Revision ID: 0121_download_manifest_member_identity_and_topology
Revises: 0120_download_manifest_rom
Create Date: 2026-09-15 00:00:00.000000
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0121_download_manifest_member_identity_and_topology"
down_revision = "0120_download_manifest_rom"
branch_labels = None
depends_on = None


def _has_unique_constraint(table_name: str, name: str) -> bool:
    return name in {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table_name)
    }


def _has_column(table_name: str, name: str) -> bool:
    return name in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _has_foreign_key(table_name: str, name: str) -> bool:
    return name in {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    }


def upgrade() -> None:
    with op.batch_alter_table("alembic_version") as batch_op:
        batch_op.alter_column(
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_nullable=False,
        )

    if not _has_unique_constraint(
        "rom_component_manifest_members",
        "uq_rom_component_manifest_members_id_component",
    ):
        with op.batch_alter_table("rom_component_manifest_members") as batch_op:
            batch_op.create_unique_constraint(
                "uq_rom_component_manifest_members_id_component",
                ["id", "component_id"],
            )

    if not _has_unique_constraint(
        "download_manifest_components", "uq_download_manifest_components_id_component"
    ):
        with op.batch_alter_table("download_manifest_components") as batch_op:
            batch_op.create_unique_constraint(
                "uq_download_manifest_components_id_component",
                ["id", "component_id"],
            )

    if not _has_column("download_manifest_members", "public_id"):
        with op.batch_alter_table("download_manifest_members") as batch_op:
            batch_op.add_column(
                sa.Column("public_id", sa.String(length=36), nullable=True)
            )
    if not _has_column("download_manifest_members", "component_id"):
        with op.batch_alter_table("download_manifest_members") as batch_op:
            batch_op.add_column(sa.Column("component_id", sa.Integer(), nullable=True))

    bind = op.get_bind()
    members = sa.table(
        "download_manifest_members",
        sa.column("id", sa.Integer()),
        sa.column("public_id", sa.String(length=36)),
    )
    for row in bind.execute(sa.select(members.c.id)):
        bind.execute(
            members.update()
            .where(members.c.id == row.id)
            .values(public_id=str(uuid.uuid4()))
        )
    op.execute(
        "UPDATE download_manifest_members SET component_id = ("
        "SELECT component_id FROM download_manifest_components "
        "WHERE download_manifest_components.id = "
        "download_manifest_members.download_manifest_component_id)"
    )

    with op.batch_alter_table("download_manifest_members") as batch_op:
        batch_op.alter_column(
            "public_id", existing_type=sa.String(length=36), nullable=False
        )
        batch_op.alter_column(
            "component_id", existing_type=sa.Integer(), nullable=False
        )
        if not _has_unique_constraint(
            "download_manifest_members", "uq_download_manifest_members_public_id"
        ):
            batch_op.create_unique_constraint(
                "uq_download_manifest_members_public_id", ["public_id"]
            )
        if not _has_foreign_key(
            "download_manifest_members",
            "fk_download_manifest_members_selected_component",
        ):
            batch_op.create_foreign_key(
                "fk_download_manifest_members_selected_component",
                "download_manifest_components",
                ["download_manifest_component_id", "component_id"],
                ["id", "component_id"],
                ondelete="CASCADE",
            )
        if not _has_foreign_key(
            "download_manifest_members",
            "fk_download_manifest_members_source_component",
        ):
            batch_op.create_foreign_key(
                "fk_download_manifest_members_source_component",
                "rom_component_manifest_members",
                ["manifest_member_id", "component_id"],
                ["id", "component_id"],
                ondelete="RESTRICT",
            )


def downgrade() -> None:
    with op.batch_alter_table("download_manifest_members") as batch_op:
        batch_op.drop_constraint(
            "fk_download_manifest_members_source_component", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_download_manifest_members_selected_component", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "uq_download_manifest_members_public_id", type_="unique"
        )
        batch_op.drop_column("component_id")
        batch_op.drop_column("public_id")

    with op.batch_alter_table("download_manifest_components") as batch_op:
        batch_op.drop_constraint(
            "uq_download_manifest_components_id_component", type_="unique"
        )

    with op.batch_alter_table("rom_component_manifest_members") as batch_op:
        batch_op.drop_constraint(
            "uq_rom_component_manifest_members_id_component", type_="unique"
        )
