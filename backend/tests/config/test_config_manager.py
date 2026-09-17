import pytest

from config.config_manager import (
    BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_DEFAULT,
    BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_MAX,
    BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_MIN,
    ConfigManager,
)


def test_browser_download_queue_concurrency_defaults_and_parses(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("browser_download_queue_concurrency: 6\n")

    loader = ConfigManager(str(config_file))

    assert loader.config.BROWSER_DOWNLOAD_QUEUE_CONCURRENCY == 6


@pytest.mark.parametrize(
    "value",
    [
        BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_MIN - 1,
        BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_MAX + 1,
        "six",
    ],
)
def test_browser_download_queue_concurrency_rejects_invalid_values(tmp_path, value):
    config_file = tmp_path / "config.yml"
    config_file.write_text(f"browser_download_queue_concurrency: {value}\n")

    with pytest.raises(SystemExit, match="3"):
        ConfigManager(str(config_file))


def test_browser_download_queue_concurrency_has_bounded_default(tmp_path):
    loader = ConfigManager(str(tmp_path / "missing.yml"))

    assert loader.config.BROWSER_DOWNLOAD_QUEUE_CONCURRENCY == (
        BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_DEFAULT
    )
    assert (
        BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_MIN
        <= loader.config.BROWSER_DOWNLOAD_QUEUE_CONCURRENCY
    )
    assert (
        loader.config.BROWSER_DOWNLOAD_QUEUE_CONCURRENCY
        <= BROWSER_DOWNLOAD_QUEUE_CONCURRENCY_MAX
    )
