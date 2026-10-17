from handler.database import db_platform_handler, db_rom_handler
from models.platform import Platform
from models.rom import Rom


def test_rescan_preserves_user_authored_fields(platform):
    """A rescan merges a freshly built Platform over the existing row.

    The scan pipeline never populates `custom_name` or `description`, so both
    must survive the merge rather than being reset to their column defaults.
    """
    db_platform_handler.update_platform(
        platform.id,
        {
            "custom_name": "Sega - Genesis/ Mega Drive (Unofficial)",
            "description": "Aftermarket only",
        },
    )

    # Mirrors endpoints/sockets/scan.py: build a platform from scan metadata,
    # graft the existing id onto it, then merge.
    scanned = Platform(
        name=platform.name,
        slug=platform.slug,
        fs_slug=platform.fs_slug,
    )
    scanned.id = platform.id

    merged = db_platform_handler.add_platform(scanned)

    assert merged.custom_name == "Sega - Genesis/ Mega Drive (Unofficial)"
    assert merged.description == "Aftermarket only"


def test_mark_missing_platforms_limits_reconciliation_and_canonicalizes_pc(platform):
    pc_platform = db_platform_handler.add_platform(
        Platform(name="PC", slug="win", fs_slug="pc")
    )
    other_platform = db_platform_handler.add_platform(
        Platform(name="Other", slug="other", fs_slug="other")
    )
    pc_rom = db_rom_handler.add_rom(
        Rom(
            platform_id=pc_platform.id,
            name="PC game",
            slug="pc-game",
            fs_name="pc.zip",
        )
    )
    other_rom = db_rom_handler.add_rom(
        Rom(
            platform_id=other_platform.id,
            name="Other game",
            slug="other-game",
            fs_name="other.zip",
        )
    )

    missing = db_platform_handler.mark_missing_platforms(
        ["win"], platform_ids=[pc_platform.id]
    )

    assert missing == []
    assert db_platform_handler.get_platform(other_platform.id).missing_from_fs is False
    assert db_rom_handler.get_rom(other_rom.id).missing_from_fs is False
    assert db_rom_handler.get_rom(pc_rom.id).missing_from_fs is False


def test_get_platform_by_fs_slug_reuses_pc_row_for_canonical_win(platform):
    platform.fs_slug = "pc"
    updated = db_platform_handler.update_platform(platform.id, {"fs_slug": "pc"})

    assert db_platform_handler.get_platform_by_fs_slug("win").id == updated.id
