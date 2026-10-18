"""Host-only behavior tests for runner boundaries and evidence classification."""

import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import phase34 as runner  # noqa: E402
from phase34_fixtures import (  # noqa: E402
    backend_command,
    expected_red,
    frontend_command,
    prepare,
    schema_commands,
    source_manifest,
)


class RunnerTests(unittest.TestCase):
    def test_explicit_backend_frontend_commands(self):
        back = backend_command(["tests/foo.py", "-q"])
        self.assertEqual(
            back[:5], ["uv", "run", "pytest", "-c", "/app/backend/pytest.ini"]
        )
        self.assertIn("--junitxml=/phase34/evidence/backend.xml", back)
        front = frontend_command(["src/foo.test.ts"])
        self.assertEqual(front[:5], ["npm", "run", "test", "--", "--run"])

    def test_inherited_targets_rejected_before_process(self):
        for key in (
            "DB_HOST",
            "DB_NAME",
            "DB_USER",
            "REDIS_HOST",
            "REDIS_URL",
            "COMPOSE_FILE",
        ):
            with self.subTest(key=key), patch.dict(
                os.environ, {key: "live"}, clear=True
            ), patch.object(runner.subprocess, "run") as process:
                with self.assertRaisesRegex(RuntimeError, "inherited target"):
                    runner.host_preflight()
                process.assert_not_called()

    def test_config_precedence_uses_generated_environment_only(self):
        with tempfile.TemporaryDirectory() as temp:
            run: Any = runner.Run.__new__(runner.Run)
            run.token = "a" * 32
            run.root = Path(temp)
            run.project = "pgdp34-" + "a" * 32
            run.evidence = Path(temp) / "evidence"
            run.control = Path(temp) / "control"
            run.driver = "mariadb"
            run.env = runner.expected_environment(run.token, run.driver)
            with patch.dict(
                os.environ,
                {
                    "DB_HOST": "live",
                    "COMPOSE_FILE": "dirty.yml",
                    "OTHER_SECRET": "secret",
                },
                clear=True,
            ):
                env = run.process_env()
            self.assertEqual(env["DB_HOST"], "sql-" + run.token)
            self.assertNotIn("COMPOSE_FILE", env)
            self.assertNotIn("OTHER_SECRET", env)

    def test_compose_is_standalone_and_explicit(self):
        run: Any = runner.Run.__new__(runner.Run)
        run.project = "pgdp34-" + "a" * 32
        run.command = Mock()
        run.compose("up", "-d")
        command = run.command.call_args.args[0]
        self.assertEqual(
            command[:5], ["docker", "compose", "--env-file", "/dev/null", "-p"]
        )
        self.assertEqual(command[command.index("-f") + 1], str(runner.COMPOSE))
        self.assertNotIn("docker-compose.override.yml", command)

    def test_unsafe_test_arguments_refused(self):
        for args in (
            [],
            ["../live.py"],
            ["/live.py"],
            ["tests/conftest.py", "-c", "unsafe.ini"],
            ["tests/conftest.py", "-n", "2"],
            ["tests/missing.py"],
        ):
            with self.subTest(args=args):
                with self.assertRaises(RuntimeError):
                    runner.safe_test_args(args)
        runner.safe_test_args(["tests/conftest.py", "-q"])

    def test_no_app_execution_before_verified_manifest(self):
        run: Any = runner.Run.__new__(runner.Run)
        run.manifest = None
        run.command = Mock()
        with self.assertRaisesRegex(RuntimeError, "not verified"):
            run.exec(["uv", "run", "pytest"])
        run.command.assert_not_called()

    def test_cleanup_rejects_foreign_labels_without_deleting(self):
        run: Any = runner.Run.__new__(runner.Run)
        run.token = "a" * 32
        run.project = "pgdp34-" + run.token
        run.command = Mock(return_value=argparse.Namespace(stdout="container-id\n"))
        run.inspect = Mock(
            return_value={"Config": {"Labels": {runner.LABEL: "foreign"}}}
        )
        with self.assertRaisesRegex(RuntimeError, "ownership mismatch"):
            run.owned("container")
        self.assertEqual(run.command.call_count, 1)
        self.assertNotIn("rm", run.command.call_args.args[0])

    def test_cleanup_removes_only_verified_exact_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            run: Any = runner.Run.__new__(runner.Run)
            run.root = Path(temp)
            run.evidence = Path(temp)
            run.runner = None
            run.token = "a" * 32
            run.project = "pgdp34-" + "a" * 32
            run.before = []
            run.owned = Mock(
                side_effect=[
                    ["exact-container"],
                    ["exact-volume"],
                    ["exact-network"],
                    [],
                    [],
                    [],
                ]
            )
            run.command = Mock()
            run.close()
            commands = [call.args[0] for call in run.command.call_args_list]
            self.assertEqual(
                commands,
                [
                    ["docker", "container", "rm", "-f", "exact-container"],
                    ["docker", "volume", "rm", "exact-volume"],
                    ["docker", "network", "rm", "exact-network"],
                ],
            )
            self.assertTrue(
                json.loads((Path(temp) / "cleanup.json").read_text())["clean"]
            )

    def test_snapshot_cleanup_preserves_evidence_and_rejects_symlinks(self):
        project = "pgdp34-" + "a" * 32
        with tempfile.TemporaryDirectory(prefix=project + "-") as temp:
            root = Path(temp)
            (root / "checkout").mkdir()
            (root / "evidence").mkdir()
            (root / "evidence/receipt.json").write_text("{}")
            runner.cleanup_snapshot(root, project)
            self.assertFalse((root / "checkout").exists())
            self.assertTrue((root / "evidence/receipt.json").is_file())
            (root / "checkout").symlink_to(root / "evidence", target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "containment"):
                runner.cleanup_snapshot(root, project)
            self.assertTrue((root / "evidence/receipt.json").is_file())

    def test_evidence_redacts_bearer_values_without_breaking_xml(self):
        from xml.etree import ElementTree

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "proof.xml"
            path.write_text(
                '<testsuite><testcase name="case"><failure message="Bearer abc.def.ghi">test-token</failure></testcase></testsuite>'
            )
            path.chmod(0o444)
            runner.redact_evidence(root, "test-token")
            payload = path.read_text()
            self.assertNotIn("abc.def.ghi", payload)
            self.assertNotIn("test-token", payload)
            self.assertEqual(ElementTree.fromstring(payload).tag, "testsuite")

    def test_schema_enforces_three_real_dialects_and_all_directions(self):
        commands = schema_commands()
        self.assertEqual(commands[1][2:], ["alembic", "upgrade", "head"])
        self.assertEqual(
            commands[2][2:],
            ["alembic", "downgrade", "0138_rom_metadata_facet_roles_view"],
        )
        self.assertEqual(commands[3][2:], ["alembic", "upgrade", "head"])
        with patch.object(sys, "argv", ["phase34.py", "schema"]), patch.object(
            runner, "host_preflight"
        ), patch.object(
            runner, "execute", side_effect=[RuntimeError("unavailable"), None, None]
        ) as execute:
            with self.assertRaisesRegex(RuntimeError, "mariadb: unavailable"):
                runner.main()
            self.assertEqual(execute.call_count, 3)
        with patch.object(
            sys, "argv", ["phase34.py", "schema", "--dialects", "sqlite"]
        ), patch.object(runner, "host_preflight"), patch.object(
            runner, "execute"
        ) as execute:
            with self.assertRaisesRegex(RuntimeError, "independently"):
                runner.main()
            execute.assert_not_called()

    def test_red_requires_exact_assertions_not_import_or_infra_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.xml"
            path.write_text(
                '<testsuite><testcase name="case"><failure message="P34_EXPECTED">AssertionError</failure></testcase></testsuite>'
            )
            self.assertEqual(expected_red(path, {"case": "P34_EXPECTED"})["cases"], 1)
            for content in (
                '<testsuite><testcase name="case"><error>connection refused</error></testcase></testsuite>',
                '<testsuite><testcase name="case"><failure>ImportError</failure></testcase></testsuite>',
                '<testsuite><testcase name="case"/></testsuite>',
                "<testsuite/>",
            ):
                path.write_text(content)
                with self.assertRaises(RuntimeError):
                    expected_red(path, {"case": "P34_EXPECTED"})

    def test_fixture_snapshot_does_not_follow_external_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            for folder in ("backend", "frontend"):
                (repo / folder).mkdir()
            for name in ("pyproject.toml", "uv.lock"):
                (repo / name).write_text("synthetic")
            (repo / "frontend/external").symlink_to("/missing/external")
            run_root = root / "run"
            run_root.mkdir()
            games, snapshot = prepare(run_root, repo)
            self.assertEqual(len(source_manifest(games)), 8)
            self.assertTrue((snapshot / "frontend/external").is_symlink())
            before = source_manifest(games)
            next(games.rglob("*.bin")).write_bytes(b"changed")
            self.assertNotEqual(before, source_manifest(games))

    def test_later_gates_refuse_missing_helpers_before_launch(self):
        cases = [
            ["e2e", "--suite", "lifecycle"],
            ["production", "--mode", "portainer", "--suite", "fresh-install"],
            ["evidence", "--assert-complete"],
        ]
        for args in cases:
            with self.subTest(args=args), patch.object(
                sys, "argv", ["phase34.py", *args]
            ), patch.object(runner, "host_preflight"), patch.object(
                runner.Path, "is_file", return_value=False
            ), patch.object(
                runner.subprocess, "call"
            ) as process, patch.object(
                runner, "execute", side_effect=AssertionError("unexpected provisioning")
            ):
                with self.assertRaisesRegex(RuntimeError, "missing helper"):
                    runner.main()
                process.assert_not_called()

    def test_later_evidence_gate_delegates_exact_contract(self):
        with patch.object(
            sys, "argv", ["phase34.py", "evidence", "--assert-complete"]
        ), patch.object(runner, "host_preflight"), patch.object(
            runner.Path, "is_file", return_value=True
        ), patch.object(
            runner.subprocess, "call", return_value=1
        ) as process, patch.object(
            runner, "execute", side_effect=AssertionError("unexpected provisioning")
        ):
            self.assertEqual(runner.main(), 1)
            self.assertEqual(
                process.call_args.args[0],
                [
                    sys.executable,
                    str(TOOLS / "phase34_evidence.py"),
                    "--assert-complete",
                ],
            )
