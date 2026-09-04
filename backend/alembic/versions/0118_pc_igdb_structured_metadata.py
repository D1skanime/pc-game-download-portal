"""Add structured PC IGDB metadata.

Revision ID: 0118_pc_igdb_structured_metadata
Revises: 0117_component_owned_media_notes
Create Date: 2026-09-04 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

from utils.database import is_postgresql

revision = "0118_pc_igdb_structured_metadata"
down_revision = "0117_component_owned_media_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rom_component_metadata", sa.Column("main_developer", sa.String(length=255))
    )
    op.add_column(
        "rom_component_metadata", sa.Column("publishers", sa.JSON(), nullable=True)
    )
    op.add_column(
        "rom_component_metadata", sa.Column("themes", sa.JSON(), nullable=True)
    )
    op.add_column(
        "rom_component_metadata",
        sa.Column("pc_release_date", sa.BigInteger(), nullable=True),
    )
    op.execute(_metadata_view_sql(is_postgresql(op.get_bind())))


def downgrade() -> None:
    op.execute(
        _metadata_view_sql(is_postgresql(op.get_bind()), include_pc_fields=False)
    )
    op.drop_column("rom_component_metadata", "pc_release_date")
    op.drop_column("rom_component_metadata", "themes")
    op.drop_column("rom_component_metadata", "publishers")
    op.drop_column("rom_component_metadata", "main_developer")


def _metadata_view_sql(is_pg: bool, *, include_pc_fields: bool = True) -> str:
    fields = [
        "generated_genres AS genres",
        "generated_franchises AS franchises",
        "generated_collections AS collections",
        "generated_companies AS companies",
        "generated_game_modes AS game_modes",
        "generated_age_ratings AS age_ratings",
        "generated_first_release_date AS first_release_date",
        "generated_average_rating AS average_rating",
        "generated_player_count AS player_count",
    ]
    if include_pc_fields:
        if is_pg:
            fields.extend(
                [
                    "NULLIF(igdb_metadata ->> 'main_developer', '') AS main_developer",
                    "COALESCE(igdb_metadata -> 'publishers', '[]'::jsonb) AS publishers",
                    "COALESCE(igdb_metadata -> 'themes', '[]'::jsonb) AS themes",
                    "CASE WHEN igdb_metadata ->> 'pc_release_date' ~ '^[0-9]+$' "
                    "THEN (igdb_metadata ->> 'pc_release_date')::bigint END AS pc_release_date",
                ]
            )
        else:
            fields.extend(
                [
                    "NULLIF(JSON_UNQUOTE(JSON_EXTRACT(igdb_metadata, '$.main_developer')), '') "
                    "AS main_developer",
                    "COALESCE(JSON_EXTRACT(igdb_metadata, '$.publishers'), JSON_ARRAY()) "
                    "AS publishers",
                    "COALESCE(JSON_EXTRACT(igdb_metadata, '$.themes'), JSON_ARRAY()) AS themes",
                    "CASE WHEN JSON_UNQUOTE(JSON_EXTRACT(igdb_metadata, '$.pc_release_date')) "
                    "REGEXP '^[0-9]+$' THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(igdb_metadata, "
                    "'$.pc_release_date')) AS UNSIGNED) END AS pc_release_date",
                ]
            )
    projection = ",\n        ".join(fields)
    return f"""CREATE OR REPLACE VIEW roms_metadata AS
    SELECT
        id AS rom_id,
        NOW() AS created_at,
        NOW() AS updated_at,
        {projection}
    FROM roms"""  # nosec B608
