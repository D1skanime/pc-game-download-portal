from copy import deepcopy

import pytest

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


def test_normalize_steam_merges_valid_text_variants_by_language():
    updates = normalize_steam(
        {
            "steam_id": 1091500,
            "steam_metadata": {
                "text_variants": {
                    "de": {
                        "name": "Cyberpunk 2077",
                        "summary": "Neue deutsche Beschreibung",
                        "source_language": "german",
                    }
                }
            },
        },
        {
            "manual_metadata": {},
            "steam_metadata": {
                "app_id": 1091500,
                "source": "storefront",
                "text_variants": {
                    "en": {
                        "name": "Cyberpunk 2077",
                        "summary": "English description",
                        "source_language": "english",
                    },
                    "de": {
                        "name": "Cyberpunk 2077",
                        "summary": "Alte deutsche Beschreibung",
                        "source_language": "german",
                    },
                },
            },
        },
    )

    assert updates["steam_metadata"]["text_variants"] == {
        "de": {
            "name": "Cyberpunk 2077",
            "summary": "Neue deutsche Beschreibung",
            "source_language": "german",
        },
        "en": {
            "name": "Cyberpunk 2077",
            "summary": "English description",
            "source_language": "english",
        },
    }


def test_normalize_steam_rejects_malformed_text_variants_without_clearing_existing_data():
    updates = normalize_steam(
        {
            "steam_id": 1091500,
            "steam_metadata": {
                "text_variants": {
                    "german": {"name": "Wrong key", "summary": "Ignored"},
                    "de": {"name": "", "summary": "Also ignored"},
                }
            },
        },
        {
            "manual_metadata": {},
            "steam_metadata": {
                "text_variants": {
                    "en": {
                        "name": "Cyberpunk 2077",
                        "summary": "English description",
                        "source_language": "english",
                    }
                }
            },
        },
    )

    assert updates["steam_metadata"]["text_variants"] == {
        "en": {
            "name": "Cyberpunk 2077",
            "summary": "English description",
            "source_language": "english",
        }
    }


@pytest.mark.parametrize(
    "incoming",
    [
        {"name": "New title"},
        {"name": "New title", "summary": "  "},
        {"name": "New title", "summary": "x" * 65536},
    ],
)
def test_partial_variant_preserves_saved_summary_and_other_locales(incoming):
    current = {
        "steam_id": 38,
        "manual_metadata": {"descriptions": {"de": "Manuell", "en": "Manual"}},
        "steam_metadata": {
            "app_id": 38,
            "source": "storefront",
            "text_variants": {
                "de": {
                    "name": "Old title",
                    "summary": "Deutsch",
                    "source_language": "german",
                },
                "fr": {"summary": "Francais", "source_language": "french"},
            },
        },
        "summary": "Legacy",
        "metadata": {"genres": ["Saved"]},
    }
    before = deepcopy(current)
    result = normalize_steam(
        {
            "steam_id": 38,
            "steam_metadata": {
                "text_variants": {
                    "de": {**incoming, "source_language": "german"},
                }
            },
        },
        current,
    )
    variants = result["steam_metadata"]["text_variants"]
    assert variants["de"] == {
        "name": "New title",
        "summary": "Deutsch",
        "source_language": "german",
    }
    assert variants["fr"] == {"summary": "Francais", "source_language": "french"}
    assert current == before
    assert not ({"summary", "manual_metadata", "metadata", "media"} & result.keys())


@pytest.mark.parametrize("english_in_incoming", [True, False])
def test_ambiguous_incoming_summary_preserves_saved_german(english_in_incoming):
    current_variants = {
        "de": {"summary": "Deutsch", "source_language": "german"},
        "en": {"summary": "English", "source_language": "english"},
    }
    incoming = {"de": {"summary": " English ", "source_language": "german"}}
    if english_in_incoming:
        incoming["en"] = {"summary": "English", "source_language": "english"}
    result = normalize_steam(
        {"steam_id": 38, "steam_metadata": {"text_variants": incoming}},
        {
            "steam_id": 38,
            "steam_metadata": {
                "app_id": 38,
                "source": "storefront",
                "text_variants": current_variants,
            },
        },
    )
    assert result["steam_metadata"]["text_variants"] == current_variants


@pytest.mark.parametrize(
    "invalid",
    [
        {"app_id": 39},
        {"app_id": True},
        {"type": "movie"},
        {"source": "other"},
    ],
)
def test_wrong_incoming_metadata_provenance_cannot_replace_saved_variant(invalid):
    saved = {"de": {"summary": "Deutsch", "source_language": "german"}}
    result = normalize_steam(
        {
            "steam_id": 38,
            "steam_metadata": {
                **invalid,
                "text_variants": {
                    "de": {"summary": "Untrusted", "source_language": "german"},
                },
            },
        },
        {
            "steam_metadata": {
                "app_id": 38,
                "source": "storefront",
                "text_variants": saved,
            }
        },
    )
    assert result["steam_metadata"]["text_variants"] == saved


def test_valid_historical_identical_slots_survive_empty_refresh():
    saved = {
        locale: {"summary": "Shared", "source_language": language}
        for locale, language in (("de", "german"), ("en", "english"))
    }
    result = normalize_steam(
        {"steam_id": 38, "steam_metadata": {"text_variants": {}}},
        {
            "steam_metadata": {
                "app_id": 38,
                "source": "storefront",
                "text_variants": saved,
            }
        },
    )
    assert result["steam_metadata"]["text_variants"] == saved


def test_new_separate_de_fr_en_slots_and_evidence_survive_merge():
    variants = {
        locale: {
            "summary": summary,
            "source_language": language,
            "requested_language": language,
            "language_evidence": "provider_slot",
        }
        for locale, language, summary in (
            ("de", "german", "Deutsch"),
            ("fr", "french", "Francais"),
            ("en", "english", "English"),
        )
    }
    result = normalize_steam(
        {"steam_id": 38, "steam_metadata": {"text_variants": variants}},
        {"manual_metadata": {"descriptions": {"en": "Protected"}}},
    )
    assert result["steam_metadata"]["text_variants"] == variants
