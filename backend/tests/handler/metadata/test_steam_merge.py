from handler.metadata.steam_merge import normalize_steam


def test_normalize_steam_preserves_each_manual_field_and_selected_artwork():
    current = {
        "name": "Manual title",
        "summary": "Manual summary",
        "pc_release_date": 1_600_000_000,
        "manual_metadata": {
            "name": True,
            "summary": True,
            "pc_release_date": True,
        },
        "path_cover_s": "roms/1/manual-cover.webp",
        "path_screenshot": "roms/1/manual-shot.webp",
        "themes": ["Cyberpunk"],
        "franchise": {"name": "Cyberpunk"},
        "related_games": [{"id": 1}],
        "dlc": [{"id": 2}],
    }

    updates = normalize_steam(
        {
            "steam_id": 1091500,
            "name": "Steam title",
            "summary": "Steam summary",
            "pc_release_date": 1_700_000_000,
            "url_cover": "https://cdn.example/cover.jpg",
            "url_screenshots": ["https://cdn.example/shot.jpg"],
        },
        current,
    )

    assert updates["steam_id"] == 1091500
    assert updates["steam_metadata"] == {"app_id": 1091500, "source": "storefront"}
    assert "name" not in updates
    assert "summary" not in updates
    assert "pc_release_date" not in updates
    assert updates["media"] == {
        "cover": ["https://cdn.example/cover.jpg"],
        "screenshots": ["https://cdn.example/shot.jpg"],
    }
    assert not ({"themes", "franchise", "related_games", "dlc"} & updates.keys())
    assert not ({"path_cover_s", "path_screenshot"} & updates.keys())


def test_normalize_steam_prefers_localized_text_over_non_manual_provider_data():
    updates = normalize_steam(
        {
            "steam_id": 1091500,
            "name": "Steam title",
            "summary": "Steam summary",
            "pc_release_date": 1_700_000_000,
            "steam_metadata": {"language": "german"},
        },
        {
            "name": "Legacy title",
            "summary": "Legacy summary",
            "pc_release_date": 1_600_000_000,
            "manual_metadata": {},
            "steam_metadata": {},
        },
    )

    assert updates == {
        "steam_id": 1091500,
        "steam_metadata": {
            "app_id": 1091500,
            "language": "german",
            "source": "storefront",
            "fields": ["name", "summary"],
        },
        "name": "Steam title",
        "summary": "Steam summary",
    }


def test_normalize_steam_keeps_existing_text_when_only_english_fallback_exists():
    updates = normalize_steam(
        {
            "steam_id": 1091500,
            "summary": "English Steam summary",
            "steam_metadata": {
                "language": "german",
                "fallback_language": "english",
                "fallback_fields": ["summary"],
            },
        },
        {
            "summary": "Existing provider summary",
            "manual_metadata": {},
            "steam_metadata": {},
        },
    )

    assert "summary" not in updates


def test_normalize_steam_parses_german_release_dates():
    updates = normalize_steam(
        {
            "steam_id": 292030,
            "steam_metadata": {"release_date": {"date": "18. Mai 2015"}},
        },
        {"manual_metadata": {}, "steam_metadata": {}, "metadata": {}},
    )

    assert updates["metadata"] == {"pc_release_date": 1_431_907_200}


def test_normalize_steam_fills_empty_genres_but_preserves_igdb_and_manual_values():
    empty_updates = normalize_steam(
        {
            "steam_id": 1091500,
            "steam_metadata": {
                "genres": ["Rollenspiel"],
                "categories": ["Einzelspieler", "Steam-Cloud"],
            },
        },
        {"manual_metadata": {}, "steam_metadata": {}, "metadata": {"genres": []}},
    )

    assert empty_updates["metadata"] == {"genres": ["Rollenspiel"]}
    assert empty_updates["steam_metadata"]["categories"] == [
        "Einzelspieler",
        "Steam-Cloud",
    ]

    preserved_updates = normalize_steam(
        {"steam_id": 1091500, "steam_metadata": {"genres": ["Rollenspiel"]}},
        {
            "manual_metadata": {"genres": True},
            "steam_metadata": {},
            "metadata": {"genres": ["Action"]},
        },
    )

    assert "metadata" not in preserved_updates


def test_normalize_steam_replaces_only_steam_owned_or_empty_fields_and_drops_empty_values():
    updates = normalize_steam(
        {
            "steam_id": "1091500",
            "name": "  Steam title  ",
            "summary": "",
            "main_developer": "  CD Projekt  ",
            "publishers": ["CD Projekt", "", None],
            "pc_release_date": "not-a-date",
            "url_cover": "",
            "url_screenshots": ["", None],
        },
        {
            "name": "Old Steam title",
            "summary": "",
            "pc_release_date": None,
            "manual_metadata": {},
            "steam_metadata": {
                "app_id": 1091500,
                "source": "storefront",
                "fields": ["name"],
            },
        },
    )

    assert updates == {
        "steam_id": 1091500,
        "steam_metadata": {
            "app_id": 1091500,
            "source": "storefront",
            "fields": ["main_developer", "name", "publishers"],
        },
        "name": "Steam title",
        "metadata": {
            "main_developer": "CD Projekt",
            "publishers": ["CD Projekt"],
        },
    }


def test_normalize_steam_drops_malformed_data_without_clearing_existing_values():
    current = {
        "name": "Existing title",
        "summary": "Existing summary",
        "pc_release_date": 1_600_000_000,
        "manual_metadata": {},
        "steam_metadata": {},
        "path_cover_s": "roms/1/selected-cover.webp",
        "path_screenshots": ["roms/1/selected-shot.webp"],
    }

    assert normalize_steam({"steam_id": False, "name": ""}, current) == {}


def test_d04_normalize_steam_preserves_manual_developer_and_publisher_fields():
    updates = normalize_steam(
        {
            "steam_id": 1091500,
            "main_developer": "Steam developer",
            "publishers": ["Steam publisher"],
        },
        {
            "manual_metadata": {
                "main_developer": True,
                "publishers": True,
            },
            "metadata": {
                "main_developer": "Manual developer",
                "publishers": ["Manual publisher"],
            },
        },
    )

    assert updates == {
        "steam_id": 1091500,
        "steam_metadata": {"app_id": 1091500, "source": "storefront"},
    }
