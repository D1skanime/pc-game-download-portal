"""Expose Phase 29 facet identities and company roles through roms_metadata.

Revision ID: 0138_rom_metadata_facet_roles_view
Revises: 0137_pc_component_provider_media_content_identity
"""

from alembic import op

from utils.database import is_postgresql

revision = "0138_rom_metadata_facet_roles_view"
down_revision = "0137_pc_component_provider_media_content_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(_metadata_view_sql(is_postgresql(op.get_bind())))


def downgrade() -> None:
    op.execute(_metadata_view_sql(is_postgresql(op.get_bind()), include_phase_29=False))


def _metadata_view_sql(is_pg: bool, *, include_phase_29: bool = True) -> str:
    fields = [
        "generated_genres AS genres",
        "generated_franchises AS franchises",
        "generated_collections AS collections",
        "generated_companies AS companies",
        "generated_game_modes AS game_modes",
        "generated_age_ratings AS age_ratings",
        "generated_first_release_date AS first_release_date",
        "generated_average_rating AS average_rating",
        (
            "generated_player_count::text AS player_count"
            if is_pg
            else "generated_player_count AS player_count"
        ),
    ]
    if include_phase_29:
        if is_pg:
            fields.extend(
                [
                    "COALESCE(igdb_metadata -> 'genre_ids', '[]'::jsonb) AS genre_ids",
                    "COALESCE(igdb_metadata -> 'theme_ids', '[]'::jsonb) AS theme_ids",
                    "COALESCE(igdb_metadata -> 'genre_options', '[]'::jsonb) AS genre_options",
                    "COALESCE(igdb_metadata -> 'theme_options', '[]'::jsonb) AS theme_options",
                    "COALESCE(igdb_metadata -> 'company_roles', '[]'::jsonb) AS company_roles",
                ]
            )
        else:
            fields.extend(
                [
                    "COALESCE(JSON_EXTRACT(igdb_metadata, '$.genre_ids'), JSON_ARRAY()) AS genre_ids",
                    "COALESCE(JSON_EXTRACT(igdb_metadata, '$.theme_ids'), JSON_ARRAY()) AS theme_ids",
                    "COALESCE(JSON_EXTRACT(igdb_metadata, '$.genre_options'), JSON_ARRAY()) AS genre_options",
                    "COALESCE(JSON_EXTRACT(igdb_metadata, '$.theme_options'), JSON_ARRAY()) AS theme_options",
                    "COALESCE(JSON_EXTRACT(igdb_metadata, '$.company_roles'), JSON_ARRAY()) AS company_roles",
                ]
            )
    if is_pg:
        fields.extend(
            [
                "NULLIF(igdb_metadata ->> 'main_developer', '') AS main_developer",
                "COALESCE(igdb_metadata -> 'publishers', '[]'::jsonb) AS publishers",
                "COALESCE(igdb_metadata -> 'themes', '[]'::jsonb) AS themes",
                "CASE WHEN igdb_metadata ->> 'pc_release_date' ~ '^[0-9]+$' THEN (igdb_metadata ->> 'pc_release_date')::bigint END AS pc_release_date",
            ]
        )
    else:
        fields.extend(
            [
                "NULLIF(JSON_UNQUOTE(JSON_EXTRACT(igdb_metadata, '$.main_developer')), '') AS main_developer",
                "COALESCE(JSON_EXTRACT(igdb_metadata, '$.publishers'), JSON_ARRAY()) AS publishers",
                "COALESCE(JSON_EXTRACT(igdb_metadata, '$.themes'), JSON_ARRAY()) AS themes",
                "CASE WHEN JSON_UNQUOTE(JSON_EXTRACT(igdb_metadata, '$.pc_release_date')) REGEXP '^[0-9]+$' THEN CAST(JSON_UNQUOTE(JSON_EXTRACT(igdb_metadata, '$.pc_release_date')) AS UNSIGNED) END AS pc_release_date",
            ]
        )
    projection = ",\n        ".join(fields)
    return f"""CREATE OR REPLACE VIEW roms_metadata AS
    SELECT
        id AS rom_id,
        NOW() AS created_at,
        NOW() AS updated_at,
        {projection}
    FROM roms"""
