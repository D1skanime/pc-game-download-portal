"""Persist explicit collection decisions and exact retained cleanup evidence.

Revision ID: 0140_scan_collection_folders
Revises: 0139_scan_operations
"""

import sqlalchemy as sa
from alembic import op

revision = "0140_scan_collection_folders"
down_revision = "0139_scan_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_collection_folders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("storage_root_id", sa.Integer(), nullable=False),
        sa.Column("mapping_relative_path", sa.String(700), nullable=False),
        sa.Column("binding_digest", sa.String(64), nullable=False),
        sa.Column("parent_relative_path", sa.String(700), nullable=False),
        sa.Column("path_digest", sa.String(64), nullable=False),
        sa.Column("parent_rom_id", sa.Integer(), nullable=False),
        sa.Column("parent_incarnation", sa.String(32), nullable=False),
        sa.Column("selected_child_relative_path", sa.String(700), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("audit", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "mapping_id",
            "binding_digest",
            "path_digest",
            name="uq_scan_collection_binding_path",
        ),
    )
    op.add_column(
        "retained_catalog_identities",
        sa.Column("retained_audit", sa.JSON(), nullable=True),
    )
    op.add_column(
        "owned_cleanup_intents", sa.Column("exact_manifest", sa.JSON(), nullable=True)
    )
    op.add_column(
        "owned_cleanup_intents", sa.Column("exact_progress", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("owned_cleanup_intents", "exact_progress")
    op.drop_column("owned_cleanup_intents", "exact_manifest")
    op.drop_column("retained_catalog_identities", "retained_audit")
    op.drop_table("scan_collection_folders")
