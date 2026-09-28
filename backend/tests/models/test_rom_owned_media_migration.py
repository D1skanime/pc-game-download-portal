import importlib.util
from pathlib import Path


def _migration():
    migration_path = (
        Path(__file__).parents[3]
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
    assert "provider" not in source.lower().replace("romm-legacy-owned", "")


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
