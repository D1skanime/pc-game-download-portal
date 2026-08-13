"""Bind legacy rollback to immutable catalog row lineage.

Revision ID: 0113_legacy_change_lineage
Revises: 0112_phase6_gap_closure
Create Date: 2026-08-13 00:00:00.000000
"""

import secrets

import sqlalchemy as sa
from alembic import op

revision = "0113_legacy_change_lineage"
down_revision = "0112_phase6_gap_closure"
branch_labels = None
depends_on = None

TOKEN_LENGTH = 32
BACKFILL_BATCH_SIZE = 500


def _backfill_incarnation_tokens(table_name: str) -> None:
    connection = op.get_bind()
    table = sa.table(
        table_name,
        sa.column("id", sa.Integer()),
        sa.column("incarnation_token", sa.String(TOKEN_LENGTH)),
    )
    used_tokens = set(
        connection.execute(
            sa.select(table.c.incarnation_token).where(
                table.c.incarnation_token.is_not(None)
            )
        ).scalars()
    )
    while True:
        row_ids = list(
            connection.execute(
                sa.select(table.c.id)
                .where(table.c.incarnation_token.is_(None))
                .order_by(table.c.id)
                .limit(BACKFILL_BATCH_SIZE)
            ).scalars()
        )
        if not row_ids:
            break
        for row_id in row_ids:
            token = secrets.token_hex(16)
            while token in used_tokens:
                token = secrets.token_hex(16)
            used_tokens.add(token)
            result = connection.execute(
                sa.update(table)
                .where(table.c.id == row_id, table.c.incarnation_token.is_(None))
                .values(incarnation_token=token)
            )
            if result.rowcount != 1:
                raise RuntimeError(
                    f"Catalog incarnation backfill lost row {table_name}:{row_id}"
                )


def _invalidate_underbound_catalog_changes() -> None:
    op.execute(
        sa.text(
            "UPDATE legacy_migrations SET state = 'failed', version = version + 1 "
            "WHERE state = 'completed'"
        )
    )


def _ensure_lineage_downgrade_safe() -> None:
    connection = op.get_bind()
    valid_lineage = int(
        connection.scalar(
            sa.text(
                "SELECT COUNT(*) FROM legacy_migration_catalog_changes "
                "WHERE lineage_valid = TRUE"
            )
        )
        or 0
    )
    if valid_lineage:
        raise RuntimeError(
            "Cannot downgrade immutable legacy rollback lineage while durable "
            "evidence exists"
        )


def upgrade() -> None:
    with op.batch_alter_table("roms") as batch_op:
        batch_op.add_column(sa.Column("incarnation_token", sa.String(TOKEN_LENGTH)))
    with op.batch_alter_table("rom_files") as batch_op:
        batch_op.add_column(sa.Column("incarnation_token", sa.String(TOKEN_LENGTH)))

    _backfill_incarnation_tokens("roms")
    _backfill_incarnation_tokens("rom_files")

    op.create_index(
        "uq_roms_incarnation_token", "roms", ["incarnation_token"], unique=True
    )
    op.create_index(
        "uq_rom_files_incarnation_token",
        "rom_files",
        ["incarnation_token"],
        unique=True,
    )
    with op.batch_alter_table("roms") as batch_op:
        batch_op.alter_column(
            "incarnation_token",
            existing_type=sa.String(TOKEN_LENGTH),
            nullable=False,
        )
    with op.batch_alter_table("rom_files") as batch_op:
        batch_op.alter_column(
            "incarnation_token",
            existing_type=sa.String(TOKEN_LENGTH),
            nullable=False,
        )

    with op.batch_alter_table("legacy_migration_catalog_changes") as batch_op:
        batch_op.add_column(
            sa.Column("entity_incarnation_token", sa.String(TOKEN_LENGTH))
        )
        batch_op.add_column(sa.Column("parent_rom_id", sa.Integer()))
        batch_op.add_column(
            sa.Column("parent_incarnation_token", sa.String(TOKEN_LENGTH))
        )
        batch_op.add_column(
            sa.Column(
                "lineage_valid",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    _invalidate_underbound_catalog_changes()

    with op.batch_alter_table("legacy_migration_catalog_changes") as batch_op:
        batch_op.create_check_constraint(
            "ck_lmcc_lineage_shape",
            "(lineage_valid = false AND entity_incarnation_token IS NULL "
            "AND parent_rom_id IS NULL AND parent_incarnation_token IS NULL) OR "
            "(lineage_valid = true AND entity_incarnation_token IS NOT NULL AND "
            "((entity_kind = 'rom' AND parent_rom_id IS NULL "
            "AND parent_incarnation_token IS NULL) OR "
            "(entity_kind = 'rom_file' AND parent_rom_id > 0 "
            "AND parent_incarnation_token IS NOT NULL)))",
        )
        batch_op.alter_column(
            "lineage_valid",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    _ensure_lineage_downgrade_safe()

    with op.batch_alter_table("legacy_migration_catalog_changes") as batch_op:
        batch_op.drop_constraint("ck_lmcc_lineage_shape", type_="check")
        batch_op.drop_column("parent_incarnation_token")
        batch_op.drop_column("parent_rom_id")
        batch_op.drop_column("entity_incarnation_token")
        batch_op.drop_column("lineage_valid")

    op.drop_index("uq_rom_files_incarnation_token", table_name="rom_files")
    op.drop_index("uq_roms_incarnation_token", table_name="roms")
    with op.batch_alter_table("rom_files") as batch_op:
        batch_op.drop_column("incarnation_token")
    with op.batch_alter_table("roms") as batch_op:
        batch_op.drop_column("incarnation_token")
