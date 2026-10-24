"""Product display metadata must leave telemetry and logging transport intact."""

import ast
import logging
from pathlib import Path

import pytest
from main import app

from logger.formatter import LOGGING_CONFIG, Formatter, strip_ansi
from logger.logger import log


def test_openapi_display_identity():
    assert app.openapi()["info"]["title"] == "ZockArchive API"
    assert app.docs_url == "/api/docs"
    assert app.redoc_url == "/api/redoc"


@pytest.mark.parametrize(
    "level",
    [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
)
def test_formatter_preserves_channel_and_message(level):
    record = logging.LogRecord("romm", level, __file__, 1, "archive ready", (), None)
    record.module_name = "scan"
    output = strip_ansi(Formatter().format(record))
    assert "[ZockArchive][scan]" in output
    assert "archive ready" in output
    assert log.name == record.name == "romm"
    handlers = LOGGING_CONFIG["handlers"]
    assert isinstance(handlers, dict)
    assert handlers["default"]["formatter"] == "pgdp"


@pytest.mark.parametrize("module", ["main.py", "startup.py"])
def test_telemetry_release_keeps_dsn_and_version(module):
    tree = ast.parse((Path(__file__).parents[1] / module).read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "sentry_sdk"
        and node.func.attr == "init"
    ]
    assert len(calls) == 1
    values = {item.arg: item.value for item in calls[0].keywords}
    assert set(values) == {"dsn", "release"}
    assert isinstance(values["dsn"], ast.Name) and values["dsn"].id == "SENTRY_DSN"
    release = eval(
        compile(ast.Expression(values["release"]), module, "eval"),
        {"get_version": lambda: "1.2.3"},
    )
    assert release == "za@1.2.3"
