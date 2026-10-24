"""Defaults may change without rewriting operator values or stream security."""

import runpy
import urllib.error
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import config
from config.config_manager import ConfigManager
from endpoints import streaming
from models.user import Role


@pytest.mark.parametrize(
    "custom", [None, "My private Switch shelf", "RomM Switch Library"]
)
def test_welcome_default_and_explicit_operator_values(monkeypatch, custom):
    monkeypatch.setattr("dotenv.load_dotenv", lambda: None)
    if custom is None:
        monkeypatch.delenv("TINFOIL_WELCOME_MESSAGE", raising=False)
    else:
        monkeypatch.setenv("TINFOIL_WELCOME_MESSAGE", custom)
    values = runpy.run_path(config.__file__)
    assert values["TINFOIL_WELCOME_MESSAGE"] == (
        custom if custom is not None else "ZockArchive Switch Library"
    )


def test_unknown_config_media_warns_without_changing_known_values(tmp_path):
    file = tmp_path / "config.yml"
    file.write_text("scan:\n  media: [box2d, future_media]\n")
    with patch("config.config_manager.log.warning") as warning:
        manager = ConfigManager(str(file))
    assert manager.config.SCAN_MEDIA == ["box2d"]
    assert any(
        "newer ZockArchive version" in str(call) for call in warning.call_args_list
    )


def test_unreachable_broker_status_and_display():
    with patch.object(
        streaming, "_broker_url", return_value="http://broker:8000/launch"
    ), patch.object(
        streaming, "_broker_request", side_effect=urllib.error.URLError("offline")
    ):
        with pytest.raises(HTTPException) as raised:
            streaming._call_broker({}, "game.rom", "Game")
    assert raised.value.status_code == 503
    assert (
        raised.value.detail
        == "Could not reach ROM broker at http://broker:8000/launch. Check that broker.py is running inside the emulator container and that port 8000 is reachable from the ZockArchive host."
    )


def test_stream_session_owner_permission_is_unchanged():
    session = {"user_id": 7}
    for id, role in [(7, Role.USER), (8, Role.ADMIN)]:
        streaming._assert_session_owner(
            session, SimpleNamespace(user=SimpleNamespace(id=id, role=role))
        )
    with pytest.raises(HTTPException) as raised:
        streaming._assert_session_owner(
            session, SimpleNamespace(user=SimpleNamespace(id=8, role=Role.USER))
        )
    assert raised.value.status_code == 403
    assert raised.value.detail == "Session is claimed by another user"
