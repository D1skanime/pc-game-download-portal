"""Merge Steam metadata and transfer history migration branches.

Revision ID: 0128_merge_steam_and_transfer_history
Revises: 0126_add_steam_metadata, 0127_download_transfer_history_dismissal
"""

revision = "0128_merge_steam_and_transfer_history"
down_revision = (
    "0126_add_steam_metadata",
    "0127_download_transfer_history_dismissal",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
