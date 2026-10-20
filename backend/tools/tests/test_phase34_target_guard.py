"""Host-only guard tests. Never import the application or parent conftest."""

import builtins
import os
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[2]


class ImportBoundaryTests(unittest.TestCase):
    def test_unsafe_collection_stops_before_dependencies(self):
        calls = []
        original = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in {
                "alembic",
                "pytest",
                "sqlalchemy",
                "config",
                "handler",
            }:
                calls.append(name)
                raise AssertionError("unsafe dependency import before target guard")
            return original(name, *args, **kwargs)

        with patch.dict(os.environ, {}, clear=True), patch.object(
            sys, "path", [str(BACKEND), *sys.path]
        ), patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaisesRegex(RuntimeError, "Phase34 target refused"):
                runpy.run_path(str(BACKEND / "tests/conftest.py"))
        self.assertEqual(calls, [])


class TargetGuardTests(unittest.TestCase):
    def setUp(self):
        import json
        import tempfile

        sys.path.insert(0, str(BACKEND))
        from tools import phase34_target_guard as guard

        self.guard = guard
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.token = "a" * 32
        self.env = guard.expected_environment(self.token, "mariadb")
        self.path = Path(self.temp.name) / "manifest.json"
        self.env["PHASE34_MANIFEST"] = str(self.path)
        project = "pgdp34-" + self.token
        network_id = "b" * 64
        self.manifest = {
            "token": self.token,
            "environment": guard.expected_environment(self.token, "mariadb"),
            "project": project,
            "network": {
                "name": project + "_isolated",
                "id": network_id,
                "internal": True,
                "labels": {guard.LABEL: self.token},
            },
            "redis_run_id": "e" * 40,
        }
        for service, identity in (("sql", "c" * 64), ("redis", "d" * 64)):
            self.manifest[service] = {
                "id": identity,
                "networks": [network_id],
                "labels": {
                    guard.LABEL: self.token,
                    "com.docker.compose.project": project,
                    "com.docker.compose.service": service,
                },
            }
        self.path.write_text(json.dumps(self.manifest))

    def test_valid_target_and_resolved_url(self):
        from types import SimpleNamespace

        url = SimpleNamespace(
            drivername="mariadb+mariadbconnector",
            host=self.env["DB_HOST"],
            port=3306,
            database=self.env["DB_NAME"],
            username=self.env["DB_USER"],
            password=self.env["DB_PASSWD"],
            query={},
        )
        with patch.object(self.guard, "verify_redis_identity") as identity:
            self.guard.validate_target(self.env, url)
            identity.assert_called_once()
        for attr, value in (
            ("host", "localhost"),
            ("database", "pgdp"),
            ("username", "root"),
            ("port", 3307),
            ("drivername", "sqlite"),
            ("password", "wrong"),
            ("query", {"host": "live"}),
        ):
            with self.subTest(attr=attr), patch.object(url, attr, value), patch.object(
                self.guard.socket, "create_connection"
            ) as connect:
                with self.assertRaisesRegex(RuntimeError, "resolved SQLAlchemy"):
                    self.guard.validate_target(self.env, url)
                connect.assert_not_called()

    def test_invalid_environment_performs_no_io(self):
        cases = [
            ("PHASE34_RUN_TOKEN", ""),
            ("DB_HOST", "localhost"),
            ("DB_HOST", "127.0.0.1"),
            ("DB_HOST", "pgdp-db"),
            ("DB_NAME", "pgdp"),
            ("DB_USER", "root"),
            ("DB_PASSWD", "passwd"),
            ("DB_PORT", "1"),
            ("ROMM_DB_DRIVER", "sqlite"),
            ("ROMM_BASE_PATH", "/romm"),
            ("ROMM_TMP_PATH", "/Games"),
            ("REDIS_HOST", "localhost"),
            ("REDIS_URL", "redis://live/0"),
            ("REDIS_DB", "1"),
            ("REDIS_SSL", "true"),
            ("DB_QUERY_JSON", '{"host":"live"}'),
            ("DATABASE_URL", "mysql://live/pgdp"),
            ("PYTEST_XDIST_WORKER", "gw0"),
            ("PYTEST_XDIST_WORKER", "../live"),
            ("PYTEST_ADDOPTS", "-n 2"),
            ("PHASE34_MANIFEST", "/missing"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value), patch.object(
                self.guard.socket, "create_connection"
            ) as connect, patch("os.makedirs") as mkdir, patch(
                "pathlib.Path.write_text"
            ) as write:
                with self.assertRaisesRegex(RuntimeError, "Phase34 target refused"):
                    self.guard.validate_target({**self.env, key: value})
                connect.assert_not_called()
                mkdir.assert_not_called()
                write.assert_not_called()

    def test_manifest_tampering_refused_before_connection(self):
        import copy
        import json

        for target, key, value in (
            ("network", "internal", False),
            ("network", "id", "bad"),
            ("sql", "networks", ["live"]),
            ("redis", "labels", {}),
            ("sql", "id", "d" * 64),
        ):
            changed = copy.deepcopy(self.manifest)
            changed[target][key] = value
            self.path.write_text(json.dumps(changed))
            with self.subTest(target=target, key=key), patch.object(
                self.guard.socket, "create_connection"
            ) as connect:
                with self.assertRaises(RuntimeError):
                    self.guard.validate_target(self.env)
                connect.assert_not_called()

    def test_redis_instance_mismatch_is_refused(self):
        import io

        payload = b"run_id:" + b"f" * 40 + b"\r\n"
        response = (
            b"+OK\r\n$" + str(len(payload)).encode() + b"\r\n" + payload + b"\r\n"
        )
        from unittest.mock import MagicMock

        stream = MagicMock()
        reader = io.BytesIO(response)
        stream.readline.side_effect = reader.readline
        stream.read.side_effect = reader.read
        conn = MagicMock()
        conn.makefile.return_value.__enter__.return_value = stream
        with patch.object(self.guard.socket, "create_connection") as connect:
            connect.return_value.__enter__.return_value = conn
            with self.assertRaisesRegex(RuntimeError, "Redis instance mismatch"):
                self.guard.validate_target(self.env)

    def test_destructive_entries_recheck_before_mutation(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock

        tree = ast.parse((BACKEND / "tests/conftest.py").read_text())
        names = {"_ensure_database_exists", "setup_database", "clear_database"}
        functions = [
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names
        ]
        for function in functions:
            function.decorator_list = []
        mutation = Mock()
        namespace = {
            "validate_target": self.guard.validate_target,
            "ConfigManager": SimpleNamespace(get_db_engine=lambda: None),
            "engine": SimpleNamespace(url=None),
            "session": mutation,
            "create_engine": mutation,
            "alembic": mutation,
        }
        exec(
            compile(
                ast.Module(body=list[ast.stmt](functions), type_ignores=[]),
                "<fixtures>",
                "exec",
            ),
            namespace,
        )
        for name in names:
            with self.subTest(name=name), patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "Phase34 target refused"):
                    namespace[name]()
                mutation.assert_not_called()
