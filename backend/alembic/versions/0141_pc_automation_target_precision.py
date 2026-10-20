"""Preserve fractional target versions in the PC automation queue.

Revision ID: 0141_queue_target_precision
Revises: 0140_scan_collection_folders
"""

from alembic import op
from sqlalchemy.dialects.mysql import TIMESTAMP

revision = "0141_queue_target_precision"
down_revision = "0140_scan_collection_folders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name not in {"mysql", "mariadb"}:
        return
    op.alter_column(
        "pc_automation_queue",
        "target_updated_at",
        existing_type=TIMESTAMP(),
        type_=TIMESTAMP(fsp=6),
        existing_nullable=False,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name not in {"mysql", "mariadb"}:
        return
    op.alter_column(
        "pc_automation_queue",
        "target_updated_at",
        existing_type=TIMESTAMP(fsp=6),
        type_=TIMESTAMP(),
        existing_nullable=False,
    )
