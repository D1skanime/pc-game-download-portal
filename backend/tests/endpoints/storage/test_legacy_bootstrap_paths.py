from endpoints.storage import _legacy_platform_slug_for_filesystem_slug


def test_pc_legacy_bootstrap_reuses_windows_platform_for_pc_folder():
    assert _legacy_platform_slug_for_filesystem_slug("pc", {"win": "Windows"}) == "win"


def test_legacy_bootstrap_does_not_alias_other_filesystem_platforms():
    assert (
        _legacy_platform_slug_for_filesystem_slug(
            "switch", {"switch": "Nintendo Switch"}
        )
        == "switch"
    )
