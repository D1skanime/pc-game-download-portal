"""Keep the UAT nginx proxy aligned with the owned-media upload limit."""

from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
UAT_NGINX_CONFIGS = (
    REPOSITORY_ROOT / "backend" / "nginx.phase9.conf",
    REPOSITORY_ROOT / "backend" / "nginx.phase10.conf",
)


@pytest.mark.parametrize("config_path", UAT_NGINX_CONFIGS)
def test_uat_nginx_allows_backend_sized_media_uploads(config_path: Path) -> None:
    """The proxy must not reject uploads before the 512 MiB backend guard runs."""
    assert "client_max_body_size 513m;" in config_path.read_text()
