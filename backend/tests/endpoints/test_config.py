import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
import yaml
from fastapi import status

from config.config_manager import (
    DEFAULT_EXCLUDED_DIRS,
    DEFAULT_EXCLUDED_EXTENSIONS,
    DEFAULT_EXCLUDED_FILES,
)
from config.config_manager import config_manager as cm
from exceptions.config_exceptions import ConfigNotWritableException
from handler.auth import oauth_handler


def test_config(client):
    response = client.get("/api/config")
    assert response.status_code == status.HTTP_200_OK

    config = response.json()
    assert config.get("EXCLUDED_PLATFORMS") == sorted(DEFAULT_EXCLUDED_DIRS)
    assert config.get("EXCLUDED_SINGLE_EXT") == sorted(
        e.lower() for e in DEFAULT_EXCLUDED_EXTENSIONS
    )
    assert config.get("EXCLUDED_SINGLE_FILES") == sorted(DEFAULT_EXCLUDED_FILES)
    assert config.get("EXCLUDED_MULTI_FILES") == sorted(DEFAULT_EXCLUDED_DIRS)
    assert config.get("EXCLUDED_MULTI_PARTS_EXT") == sorted(
        e.lower() for e in DEFAULT_EXCLUDED_EXTENSIONS
    )
    assert config.get("EXCLUDED_MULTI_PARTS_FILES") == sorted(DEFAULT_EXCLUDED_FILES)
    assert config.get("PLATFORMS_BINDING") == {}
    assert not config.get("SKIP_HASH_CALCULATION")
    assert config.get("GAMELIST_MEDIA_THUMBNAIL") == "box2d"
    assert config.get("GAMELIST_MEDIA_IMAGE") == "screenshot"
    assert config.get("GAMELIST_AUTO_EXPORT_ON_SCAN") is False
    assert config.get("PEGASUS_AUTO_EXPORT_ON_SCAN") is False
    assert config.get("browser_download_queue_concurrency") == 3


def test_config_parse_error_gated_by_auth(client, access_token: str):
    # The raw parser error can leak the config file path, so it is only
    # returned to authenticated users.
    cfg = cm.get_config()
    cfg.CONFIG_FILE_PARSE_ERROR = 'in "/data/config.yml", line 2'

    with patch.object(cm, "get_config", return_value=cfg):
        anon = client.get("/api/config")
        assert anon.status_code == status.HTTP_200_OK
        assert anon.json().get("CONFIG_FILE_PARSE_ERROR") is None

        auth = client.get(
            "/api/config",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert auth.status_code == status.HTTP_200_OK
        assert (
            auth.json().get("CONFIG_FILE_PARSE_ERROR")
            == 'in "/data/config.yml", line 2'
        )


def test_add_platform_binding_payload_shape(client, access_token: str):
    with patch.object(cm, "add_platform_binding") as add_platform_binding:
        response = client.post(
            "/api/config/system/platforms",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"fs_slug": "n64", "slug": "nintendo-64"},
        )

    assert response.status_code == status.HTTP_200_OK
    add_platform_binding.assert_called_once_with("n64", "nintendo-64")


def test_add_platform_version_payload_shape(client, access_token: str):
    with patch.object(cm, "add_platform_version") as add_platform_version:
        response = client.post(
            "/api/config/system/versions",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"fs_slug": "n64", "slug": "1.0"},
        )

    assert response.status_code == status.HTTP_200_OK
    add_platform_version.assert_called_once_with("n64", "1.0")


def test_add_exclusion_payload_shape(client, access_token: str):
    with patch.object(cm, "add_exclusion") as add_exclusion:
        response = client.post(
            "/api/config/exclude",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"exclusion_type": "single_files", "exclusion_value": "README.txt"},
        )

    assert response.status_code == status.HTTP_200_OK
    add_exclusion.assert_called_once_with("single_files", "README.txt")


def _scan_payload(**overrides):
    payload = {
        "metadata_priority": ["igdb", "moby"],
        "artwork_priority": ["sgdb", "igdb"],
        "cover_priority": ["igdb", "ss"],
        "screenshot_priority": None,
        "manual_priority": None,
        "region_priority": ["us", "eu"],
        "language_priority": ["en", "fr"],
        "media": ["box2d", "screenshot"],
        "gamelist_export": True,
        "gamelist_thumbnail": "box2d",
        "gamelist_image": "screenshot",
        "pegasus_export": False,
    }
    payload.update(overrides)
    return payload


def test_update_scan_settings_payload_shape(client, access_token: str):
    with patch.object(cm, "update_scan_settings") as update_scan_settings:
        response = client.put(
            "/api/config/scan",
            headers={"Authorization": f"Bearer {access_token}"},
            json=_scan_payload(),
        )

    assert response.status_code == status.HTTP_200_OK
    update_scan_settings.assert_called_once_with(
        metadata_priority=["igdb", "moby"],
        artwork_priority=["sgdb", "igdb"],
        artwork_overrides={
            "cover": ["igdb", "ss"],
            "screenshot": None,
            "manual": None,
        },
        region_priority=["us", "eu"],
        language_priority=["en", "fr"],
        media=["box2d", "screenshot"],
        gamelist_export=True,
        gamelist_thumbnail="box2d",
        gamelist_image="screenshot",
        pegasus_export=False,
    )


def test_update_scan_settings_requires_auth(client):
    response = client.put("/api/config/scan", json=_scan_payload())
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_scan_settings_rejects_unknown_source(client, access_token: str):
    with patch.object(cm, "update_scan_settings") as update_scan_settings:
        response = client.put(
            "/api/config/scan",
            headers={"Authorization": f"Bearer {access_token}"},
            json=_scan_payload(metadata_priority=["igdb", "not-a-source"]),
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    update_scan_settings.assert_not_called()


def test_update_scan_settings_rejects_invalid_gamelist_thumbnail(
    client, access_token: str
):
    # `screenshot` is a valid media type but not a valid gamelist thumbnail.
    with patch.object(cm, "update_scan_settings") as update_scan_settings:
        response = client.put(
            "/api/config/scan",
            headers={"Authorization": f"Bearer {access_token}"},
            json=_scan_payload(gamelist_thumbnail="screenshot"),
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    update_scan_settings.assert_not_called()


def test_update_scan_settings_normalizes_codes(client, access_token: str):
    with patch.object(cm, "update_scan_settings") as update_scan_settings:
        response = client.put(
            "/api/config/scan",
            headers={"Authorization": f"Bearer {access_token}"},
            json=_scan_payload(
                region_priority=["US", " eu ", "us", ""],
                language_priority=["EN", "en"],
            ),
        )

    assert response.status_code == status.HTTP_200_OK
    _, kwargs = update_scan_settings.call_args
    assert kwargs["region_priority"] == ["us", "eu"]
    assert kwargs["language_priority"] == ["en"]


@pytest.fixture
def language_config(tmp_path, monkeypatch):
    prior = copy.deepcopy(cm.__dict__)
    path = tmp_path / "config.yml"
    original = {
        "scan": {
            "priority": {"language": ["en", "fr"], "region": ["eu"]},
            "media": ["box2d"],
        },
        "custom": {"keep": 7},
    }
    path.write_text(yaml.safe_dump(original))
    monkeypatch.setattr(cm, "config_file", str(path))
    monkeypatch.setattr(cm, "_config_file_writable", True)
    cm.get_config()
    yield path
    cm.__dict__.clear()
    cm.__dict__.update(prior)


def test_language_route_cas_preserves_unrelated(client, access_token, language_config):
    headers = {"Authorization": f"Bearer {access_token}"}
    body = {"language_priority": ["de-CH"], "expected_language_priority": ["en", "fr"]}
    response = client.put("/api/config/scan/language", headers=headers, json=body)
    assert response.status_code == 200
    assert response.json() == {"language_priority": ["de", "en", "fr"]}
    saved = yaml.safe_load(language_config.read_text())
    assert saved["custom"] == {"keep": 7}
    assert saved["scan"]["priority"]["region"] == ["eu"]
    assert saved["scan"]["media"] == ["box2d"]
    before = language_config.read_bytes()
    stale = client.put("/api/config/scan/language", headers=headers, json=body)
    assert stale.status_code == 409
    assert language_config.read_bytes() == before


def test_language_route_denies_personal_scope(client, admin_user, language_config):
    token = oauth_handler.create_access_token(
        data={"sub": admin_user.username, "iss": "romm:oauth", "scopes": "me.write"},
        expires_delta=timedelta(minutes=1),
    )
    body = {"language_priority": ["fr"], "expected_language_priority": ["en", "fr"]}
    before = language_config.read_bytes()
    assert client.put("/api/config/scan/language", json=body).status_code == 401
    assert (
        client.put(
            "/api/config/scan/language",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 403
    )
    assert language_config.read_bytes() == before


@pytest.mark.parametrize("failure", ["readonly", "serialization", "replace"])
def test_full_scan_persistence_failure_keeps_authority(
    language_config, monkeypatch, failure
):
    before = language_config.read_bytes()
    original_config = cm.config
    if failure == "readonly":
        monkeypatch.setattr(cm, "_config_file_writable", False)
    elif failure == "serialization":
        monkeypatch.setattr(
            yaml,
            "dump",
            lambda *a, **kw: (_ for _ in ()).throw(yaml.YAMLError("serialize")),
        )
    else:
        monkeypatch.setattr(
            "os.replace", lambda *a: (_ for _ in ()).throw(PermissionError("replace"))
        )
    payload = _scan_payload(language_priority=["de"])
    overrides = {
        key: payload.pop(key + "_priority") for key in ("cover", "screenshot", "manual")
    }
    with pytest.raises(ConfigNotWritableException):
        cm.update_scan_settings(**payload, artwork_overrides=overrides)
    assert language_config.read_bytes() == before
    assert cm.config is original_config
    assert cm.config.SCAN_LANGUAGE_PRIORITY == ["en", "fr"]


def test_language_cas_serializes_contenders(client, access_token, language_config):
    def change(locale):
        return client.put(
            "/api/config/scan/language",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "language_priority": [locale],
                "expected_language_priority": ["en", "fr"],
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(change, ["de", "fr"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = next(
        response.json()["language_priority"]
        for response in responses
        if response.status_code == 200
    )
    assert (
        yaml.safe_load(language_config.read_text())["scan"]["priority"]["language"]
        == winner
    )
    assert cm.config.SCAN_LANGUAGE_PRIORITY == winner


@pytest.mark.parametrize("failure", ["readonly", "serialization", "replace"])
def test_language_route_reports_failed_commit(
    client, access_token, language_config, monkeypatch, failure
):
    before = language_config.read_bytes()
    old = cm.config
    if failure == "readonly":
        language_config.chmod(0o444)
    elif failure == "serialization":
        monkeypatch.setattr(
            yaml,
            "dump",
            lambda *a, **kw: (_ for _ in ()).throw(yaml.YAMLError("serialize")),
        )
    else:
        monkeypatch.setattr(
            "os.replace", lambda *a: (_ for _ in ()).throw(PermissionError("replace"))
        )
    response = client.put(
        "/api/config/scan/language",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"language_priority": ["de"], "expected_language_priority": ["en", "fr"]},
    )
    assert response.status_code == 500
    assert language_config.read_bytes() == before
    assert cm.config is old
    assert cm.config.SCAN_LANGUAGE_PRIORITY == ["en", "fr"]


def test_full_scan_and_language_share_serialized_reload(language_config, monkeypatch):
    from threading import Event

    from config import scan_language

    entered, release = Event(), Event()
    persist = scan_language._persist

    def paused(path, raw):
        if raw["scan"]["priority"]["region"] == ["jp"] and raw["scan"]["priority"][
            "language"
        ] == ["en", "fr"]:
            entered.set()
            assert release.wait(5)
        persist(path, raw)

    monkeypatch.setattr(scan_language, "_persist", paused)
    payload = _scan_payload(region_priority=["jp"])
    overrides = {
        key: payload.pop(key + "_priority") for key in ("cover", "screenshot", "manual")
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        full = pool.submit(
            cm.update_scan_settings, **payload, artwork_overrides=overrides
        )
        assert entered.wait(5)
        narrow = pool.submit(cm.update_scan_language, ["fr-CA"], ["en", "fr"])
        release.set()
        full.result(timeout=5)
        assert narrow.result(timeout=5) == ["fr", "en"]
    saved = yaml.safe_load(language_config.read_text())
    assert saved["scan"]["priority"]["region"] == ["jp"]
    assert saved["scan"]["priority"]["language"] == ["fr", "en"]
    assert saved["custom"] == {"keep": 7}


@pytest.mark.parametrize(
    "selected,expected",
    [([], ["en", "fr"]), (["french"], ["fr", "en"]), (["xx-invalid"], ["en", "fr"])],
)
def test_language_normalization_defaults(language_config, selected, expected):
    assert cm.update_scan_language(selected, ["en", "fr"]) == expected


def test_language_mutation_obeys_config_path_flock(language_config):
    import fcntl
    from concurrent.futures import TimeoutError
    from threading import Event

    started = Event()

    def mutate():
        started.set()
        return cm.update_scan_language(["de"], ["en", "fr"])

    with language_config.with_name("config.yml.lock").open("a") as external_lock:
        fcntl.flock(external_lock, fcntl.LOCK_EX)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(mutate)
            try:
                assert started.wait(5)
                with pytest.raises(TimeoutError):
                    pending.result(timeout=0.1)
                assert cm.config.SCAN_LANGUAGE_PRIORITY == ["en", "fr"]
            finally:
                fcntl.flock(external_lock, fcntl.LOCK_UN)
            assert pending.result(timeout=5) == ["de", "en", "fr"]
