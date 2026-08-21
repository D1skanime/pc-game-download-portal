"""Persist private source-observed identity evidence.

Revision ID: 0114_legacy_source_identities
Revises: 0113_legacy_change_lineage
Create Date: 2026-08-21 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0114_legacy_source_identities"
down_revision = "0113_legacy_change_lineage"
branch_labels = None
depends_on = None

DIGEST_LENGTH = 64
INVALIDATION_BATCH_SIZE = 500


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


def _invalidate_selectable_results(*, with_identity_evidence: bool) -> None:
    connection = op.get_bind()
    results = sa.table(
        "legacy_detection_results",
        sa.column("id", sa.Integer()),
        sa.column("selectable", sa.Boolean()),
        sa.column("lower_bound", sa.Boolean()),
        sa.column("state", sa.String()),
        sa.column("safe_problem_code", sa.String()),
        sa.column("source_fingerprint", sa.String()),
        sa.column("version", sa.Integer()),
    )
    identities = sa.table(
        "legacy_detection_source_identities",
        sa.column("detection_result_id", sa.Integer()),
    )

    while True:
        query = (
            sa.select(results.c.id)
            .where(results.c.selectable.is_(True))
            .order_by(results.c.id)
            .limit(INVALIDATION_BATCH_SIZE)
        )
        if with_identity_evidence:
            query = query.where(
                sa.exists(
                    sa.select(1).where(identities.c.detection_result_id == results.c.id)
                )
            )
        result_ids = list(connection.execute(query).scalars())
        if not result_ids:
            break
        connection.execute(
            sa.update(results)
            .where(results.c.id.in_(result_ids), results.c.selectable.is_(True))
            .values(
                selectable=False,
                lower_bound=True,
                state="manual_mapping_required",
                safe_problem_code="fingerprint_refresh_required",
                source_fingerprint=None,
                version=results.c.version + 1,
            )
        )


def upgrade() -> None:
    _invalidate_selectable_results(with_identity_evidence=False)

    op.create_table(
        "legacy_detection_source_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("detection_result_id", sa.Integer(), nullable=False),
        sa.Column("identity_digest", sa.String(DIGEST_LENGTH), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "CHAR_LENGTH(identity_digest) = 64 AND "
            "identity_digest = LOWER(identity_digest) AND "
            "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE("
            "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE("
            "REPLACE(REPLACE(identity_digest, '0', ''), '1', ''), '2', ''), "
            "'3', ''), '4', ''), '5', ''), '6', ''), '7', ''), '8', ''), "
            "'9', ''), 'a', ''), 'b', ''), 'c', ''), 'd', ''), 'e', ''), "
            "'f', '') = ''",
            name="ck_legacy_detection_source_identities_digest_format",
        ),
        sa.ForeignKeyConstraint(
            ["detection_result_id"],
            ["legacy_detection_results.id"],
            name="fk_legacy_detection_source_identities_detection_result_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_legacy_detection_source_identities"),
        sa.UniqueConstraint(
            "detection_result_id",
            "identity_digest",
            name="uq_legacy_detection_source_identities_result_digest",
        ),
    )
    op.create_index(
        "ix_legacy_detection_source_identities_order",
        "legacy_detection_source_identities",
        ["detection_result_id", "identity_digest"],
    )


def downgrade() -> None:
    _invalidate_selectable_results(with_identity_evidence=True)
    _invalidate_selectable_results(with_identity_evidence=False)
    op.drop_index(
        "ix_legacy_detection_source_identities_order",
        table_name="legacy_detection_source_identities",
    )
    op.drop_table("legacy_detection_source_identities")
