"""Pure contracts for parent-owned media discovery and storage."""

import pytest

from handler.metadata.rom_media import discover_provider_media


def test_provider_discovery_normalizes_https_url_and_uses_digest_identity() -> None:
    candidates = discover_provider_media(
        "igdb",
        {"url_screenshots": ["https://images.igdb.com/a.png?b=2&a=1#fragment"]},
    )

    assert len(candidates) == 1
    assert candidates[0].url == "https://images.igdb.com/a.png?a=1&b=2"
    assert candidates[0].provider_media_id == (
        "url-sha256:631703e43d3d497a541d2759ae5e2e7e4452558ef853995586db11e59798ac92"
    )


def test_provider_discovery_rejects_non_https_urls() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        discover_provider_media(
            "igdb", {"url_screenshots": ["http://invalid/image.png"]}
        )
