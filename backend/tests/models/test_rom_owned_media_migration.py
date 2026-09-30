import importlib.util
import json
from pathlib import Path

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext


def _migration():
    migration_path = (
        Path(__file__).parents[2]
        / "alembic/versions/0129_backfill_legacy_rom_owned_media.py"
    )
    spec = importlib.util.spec_from_file_location(
        "legacy_owned_media_migration", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_legacy_owned_media_migration_has_portable_lineage_and_no_filesystem_api():
    migration = _migration()

    assert migration.revision == "0129_backfill_legacy_rom_owned_media"
    assert migration.down_revision == "0128_owned_media_role_and_display_label"
    source = Path(migration.__file__).read_text()
    assert "os." not in source
    assert "pathlib" not in source
    assert "open(" not in source
    assert "http" not in source.lower()


def test_legacy_resource_path_accepts_only_owned_image_identifiers():
    migration = _migration()

    assert migration._owned_image_path("roms/13/media/screenshot-01.webp")
    assert migration._owned_image_path("roms/13/cover/large.jpg")
    assert not migration._owned_image_path("/roms/13/cover/large.jpg")
    assert not migration._owned_image_path("roms/13/../../source.jpg")
    assert not migration._owned_image_path("https://provider.example/image.webp")
    assert not migration._owned_image_path("roms/13/cover/not-an-image.txt")


def test_legacy_identity_is_stable_role_bound_and_safe_for_a_28_item_gallery():
    migration = _migration()
    paths = [f"roms/13/screenshots/{index:02}.webp" for index in range(28)]
    identities = [migration._legacy_identity("screenshot", path) for path in paths]

    assert len(identities) == 28
    assert len(set(identities)) == 28
    assert identities[0] == migration._legacy_identity("screenshot", paths[0])
    assert identities[0] != migration._legacy_identity("artwork", paths[0])
    assert all(
        identity.startswith("legacy-") and len(identity) == 71
        for identity in identities
    )


def test_legacy_rows_keep_screenshot_order_and_deduplicate_compatible_covers():
    migration = _migration()
    rows = migration._legacy_rows(
        13,
        ["roms/13/screenshots/first.webp", "roms/13/screenshots/second.webp"],
        "roms/13/covers/small.webp",
        "roms/13/covers/large.jpg",
    )

    assert [(row["role"], row["owned_path"]) for row in rows] == [
        ("screenshot", "roms/13/screenshots/first.webp"),
        ("screenshot", "roms/13/screenshots/second.webp"),
        ("artwork", "roms/13/covers/small.webp"),
        ("artwork", "roms/13/covers/large.jpg"),
    ]
    assert [row["display_label"] for row in rows] == [
        "first.webp",
        "second.webp",
        "small.webp",
        "large.jpg",
    ]


def test_upgrade_is_idempotent_preserves_tombstones_and_downgrades_only_legacy_rows():
    migration = _migration()
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    roms = sa.Table(
        "roms",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("path_screenshots", sa.Text),
        sa.Column("path_cover_s", sa.Text),
        sa.Column("path_cover_l", sa.Text),
    )
    media = sa.Table(
        "rom_owned_media",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rom_id", sa.Integer),
        sa.Column("origin", sa.String),
        sa.Column("role", sa.String),
        sa.Column("state", sa.String),
        sa.Column("mime_type", sa.String),
        sa.Column("owned_path", sa.String),
        sa.Column("provider", sa.String),
        sa.Column("provider_media_id", sa.String),
        sa.Column("display_label", sa.String),
    )
    placements = sa.Table(
        "rom_owned_media_placements",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rom_id", sa.Integer),
        sa.Column("media_id", sa.Integer),
        sa.Column("surface", sa.String),
        sa.Column("position", sa.Integer),
    )
    metadata.create_all(engine)
    screenshots = [f"roms/13/screenshots/{index:02}.webp" for index in range(28)]
    tombstone_path = screenshots[0]
    with engine.begin() as connection:
        connection.execute(
            roms.insert().values(
                id=13,
                path_screenshots=json.dumps(screenshots),
                path_cover_s="roms/13/covers/small.webp",
                path_cover_l="roms/13/covers/large.jpg",
            )
        )
        connection.execute(
            media.insert().values(
                rom_id=13,
                origin="provider",
                role="screenshot",
                state="tombstoned",
                mime_type="image/webp",
                owned_path=None,
                provider=migration._LEGACY_PROVIDER,
                provider_media_id=migration._legacy_identity(
                    "screenshot", tombstone_path
                ),
                display_label="00.webp",
            )
        )
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        first_media = connection.execute(sa.select(media)).mappings().all()
        first_placements = (
            connection.execute(sa.select(placements).order_by(placements.c.position))
            .mappings()
            .all()
        )
        migration.upgrade()
        assert connection.scalar(sa.select(sa.func.count()).select_from(media)) == len(
            first_media
        )
        assert connection.scalar(
            sa.select(sa.func.count()).select_from(placements)
        ) == len(first_placements)
        tombstone = (
            connection.execute(
                sa.select(media).where(
                    media.c.provider_media_id
                    == migration._legacy_identity("screenshot", tombstone_path)
                )
            )
            .mappings()
            .one()
        )
        assert tombstone["state"] == "tombstoned"
        assert [item["position"] for item in first_placements] == list(range(1, 28))
        assert [item["media_id"] for item in first_placements]
        migration.downgrade()
        assert connection.scalar(sa.select(sa.func.count()).select_from(media)) == 0
        assert (
            connection.scalar(sa.select(sa.func.count()).select_from(placements)) == 0
        )
