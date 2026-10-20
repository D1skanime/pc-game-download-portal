"""Adversarial checks for the isolated Phase 33 fixture controller."""

import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import phase33_collection_fixture  # noqa: E402
from phase33_uat import watch_fixture_additions  # noqa: E402
from phase34_fixtures import source_manifest  # noqa: E402

VALIDATOR_PATH = (
    TOOLS.parents[1]
    / ".planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-evidence-validate.py"
)
_spec = importlib.util.spec_from_file_location(
    "phase33_evidence_validator", VALIDATOR_PATH
)
assert _spec and _spec.loader
validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validator)


class MountEvidenceTests(unittest.TestCase):
    def state(self):
        return {
            "compose_project": "pgdp34-" + "a" * 32,
            "uat_root": "/tmp/pgdp34-" + "a" * 32 + "-owned",
        }

    def write_mounts(self, root, state, *, source=None, writable=False):
        expected = (state["uat_root"] + "/fixture/Games").replace(
            "a" * 32, "[run-token]"
        )
        item = {
            "Config": {
                "Labels": {
                    "com.docker.compose.project": "pgdp34-[run-token]",
                }
            },
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": source or expected,
                    "Destination": destination,
                    "Mode": "rw" if writable else "ro",
                    "RW": writable,
                }
                for destination in ("/app/romm/library", "/phase34/owned/library")
            ],
        }
        (root / "31.log").write_text(json.dumps([item]))

    def test_equivalent_compose_path_requires_exact_daemon_mounts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = self.state()
            source = state["uat_root"] + "/Games/../fixture/Games"
            rendered = root / "rendered.json"
            rendered.write_text(
                json.dumps(
                    {
                        "services": {
                            "runner": {
                                "volumes": [
                                    {
                                        "type": "bind",
                                        "source": source,
                                        "target": target,
                                        "read_only": True,
                                    }
                                    for target in (
                                        "/app/romm/library",
                                        "/phase34/owned/library",
                                    )
                                ]
                            }
                        }
                    }
                )
            )
            validator.validate_rendered(
                rendered, "/fixture/Games", "/app/romm/library", state
            )
            with self.assertRaisesRegex(RuntimeError, "authoritative"):
                validator.validate_daemon_mounts(root, state)
            self.write_mounts(root, state)
            validator.validate_daemon_mounts(root, state)

    def test_similarly_named_external_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            rendered = Path(directory) / "rendered.json"
            rendered.write_text(
                json.dumps(
                    {
                        "services": {
                            "runner": {
                                "volumes": [
                                    {
                                        "type": "bind",
                                        "source": "/outside/fixture/Games",
                                        "target": "/app/romm/library",
                                        "read_only": True,
                                    }
                                ]
                            }
                        }
                    }
                )
            )
            with self.assertRaisesRegex(RuntimeError, "owned fixture"):
                validator.validate_rendered(
                    rendered, "/fixture/Games", "/app/romm/library", self.state()
                )

    def test_daemon_writable_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_mounts(root, self.state(), writable=True)
            with self.assertRaisesRegex(RuntimeError, "authoritative"):
                validator.validate_daemon_mounts(root, self.state())

    def test_daemon_wrong_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_mounts(root, self.state(), source="/outside/fixture/Games")
            with self.assertRaisesRegex(RuntimeError, "authoritative"):
                validator.validate_daemon_mounts(root, self.state())


class FixtureAdditionTests(unittest.TestCase):
    def test_fixture_actions_refuse_unverified_targets_before_database_access(self):
        actions = (
            lambda: phase33_collection_fixture.seed_parent(1),
            lambda: phase33_collection_fixture.inspect_parent(1),
            phase33_collection_fixture.run_cleanup,
            lambda: phase33_collection_fixture.run_scheduled(1),
        )
        with patch.dict(os.environ, {}, clear=True):
            for action in actions:
                with self.subTest(action=action), self.assertRaisesRegex(
                    RuntimeError, "invalid run identity"
                ):
                    action()

    def test_standalone_fixture_adds_backend_import_root_after_authority_check(self):
        backend = str(TOOLS.parent)
        handler = ModuleType("handler")
        handler.__path__ = []
        database = ModuleType("handler.database")
        database.__path__ = []
        base = ModuleType("handler.database.base_handler")
        base.__dict__["sync_engine"] = SimpleNamespace(url="verified-owned-target")
        modules = {
            "handler": handler,
            "handler.database": database,
            "handler.database.base_handler": base,
        }
        with patch.object(
            sys, "path", [entry for entry in sys.path if entry != backend]
        ), patch.dict(sys.modules, modules), patch.object(
            phase33_collection_fixture, "validate_target"
        ) as guard:
            phase33_collection_fixture.authority()
            self.assertEqual(sys.path[0], backend)
            self.assertEqual(guard.call_count, 2)
            guard.assert_called_with(resolved_url="verified-owned-target")

    def make_run(self, root):
        games = root / "Games"
        games.mkdir()
        folder = games / "pc/Castlevania"
        folder.mkdir(parents=True)
        (folder / "existing.rar").write_bytes(b"existing immutable game")
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "Games").symlink_to(games, target_is_directory=True)
        evidence = root / "evidence"
        evidence.mkdir()
        before = source_manifest(games)
        (evidence / "before.json").write_text(json.dumps(before))
        return SimpleNamespace(root=root, evidence=evidence, before=before)

    def test_application_mutation_stops_fixture_addition(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.make_run(Path(folder))
            (run.root / "Games/pc/Castlevania/existing.rar").write_bytes(b"changed")
            (run.evidence / "add-normal-child.request").write_text("request")
            errors: list[str] = []
            watch_fixture_additions(run, threading.Event(), errors)
            self.assertEqual(len(errors), 1)
            self.assertFalse(
                (run.root / "Games/pc/Castlevania/Newly.Added.Game").exists()
            )
            self.assertFalse((run.evidence / "add-normal-child.ready").exists())

    def test_named_additions_preserve_every_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.make_run(Path(folder))
            original = run.before
            stop = threading.Event()
            errors: list[str] = []
            for stage in ("normal", "scheduled"):
                (run.evidence / ("add-" + stage + "-child.request")).write_text(
                    "untrusted path ignored"
                )
            worker = threading.Thread(
                target=watch_fixture_additions, args=(run, stop, errors), daemon=True
            )
            worker.start()
            deadline = time.monotonic() + 3
            ready = run.evidence / "add-scheduled-child.ready"
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            stop.set()
            worker.join(timeout=1)
            self.assertTrue(ready.exists())
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])
            after = {
                entry["path"]: entry for entry in source_manifest(run.root / "Games")
            }
            for entry in original:
                self.assertEqual(after[entry["path"]], entry)
            self.assertEqual(len(after), len(original) + 4)
            segments = json.loads((run.evidence / "fixture-segments.json").read_text())
            self.assertEqual(len(segments), 2)


if __name__ == "__main__":
    unittest.main()
