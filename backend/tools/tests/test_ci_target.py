"""Contracts for CI gates without connecting to any application target."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_target


class CITargetTests(unittest.TestCase):
    def setUp(self):
        cwd = patch.object(
            ci_target.Path,
            "cwd",
            return_value=Path(ci_target.__file__).resolve().parents[2],
        )
        cwd.start()
        self.addCleanup(cwd.stop)
        self.workspace = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "D1skanime/zockarchive",
            "GITHUB_WORKSPACE": str(Path(ci_target.__file__).resolve().parents[2]),
        }

    def test_non_linux_is_refused_before_git_or_docker(self):
        with patch.object(ci_target.platform, "system", return_value="Windows"):
            with patch.object(ci_target.subprocess, "check_output") as git:
                with self.assertRaisesRegex(RuntimeError, "Linux"):
                    ci_target.preflight()
                git.assert_not_called()

    def test_inherited_target_is_refused(self):
        with patch.dict(
            ci_target.os.environ, {**self.workspace, "DB_HOST": "live-db"}, clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "inherited target override"):
                ci_target.preflight()

    def test_origin_mismatch_is_refused(self):
        root = str(Path(ci_target.__file__).resolve().parents[2])
        with patch.dict(ci_target.os.environ, self.workspace, clear=True):
            with patch.object(
                ci_target.subprocess, "check_output", side_effect=[root, "wrong"]
            ):
                with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
                    ci_target.preflight()

    def test_checkout_origin_without_git_suffix_is_accepted(self):
        root = str(Path(ci_target.__file__).resolve().parents[2])
        with patch.dict(ci_target.os.environ, self.workspace, clear=True):
            with patch.object(
                ci_target.subprocess,
                "check_output",
                side_effect=[root, ci_target.ORIGIN.removesuffix(".git")],
            ):
                self.assertEqual(ci_target.preflight(), Path(root))

    def test_current_origin_positive_and_foreign_negatives(self):
        root = str(Path(ci_target.__file__).resolve().parents[2])
        for origin in (
            "https://github.com/D1skanime/zockarchive.git",
            "https://github.com/D1skanime/zockarchive",
            "https://github.com/D1skanime/pc-game-download-portal.git",
            "https://github.com/foreign/zockarchive.git",
            "https://foreign.example/D1skanime/zockarchive.git",
        ):
            with self.subTest(origin=origin), patch.dict(
                ci_target.os.environ, self.workspace, clear=True
            ), patch.object(
                ci_target.subprocess, "check_output", side_effect=[root, origin]
            ):
                if (
                    origin.removesuffix(".git")
                    == "https://github.com/D1skanime/zockarchive"
                ):
                    self.assertEqual(ci_target.preflight(), Path(root))
                else:
                    with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
                        ci_target.preflight()

    def test_ci_workspace_positive_and_identity_negatives(self):
        root = Path("/actions/zockarchive/zockarchive")
        for overrides in (
            {},
            {"GITHUB_REPOSITORY": "foreign/zockarchive"},
            {"GITHUB_REPOSITORY": "D1skanime/pc-game-download-portal"},
            {"GITHUB_WORKSPACE": "/actions/foreign"},
            {"GITHUB_ACTIONS": "false"},
        ):
            with self.subTest(overrides=overrides), patch.object(
                ci_target, "__file__", str(root / "backend/tools/ci_target.py")
            ), patch.object(ci_target.Path, "cwd", return_value=root), patch.dict(
                ci_target.os.environ,
                {**self.workspace, "GITHUB_WORKSPACE": str(root), **overrides},
                clear=True,
            ), patch.object(
                ci_target.subprocess,
                "check_output",
                side_effect=[str(root), "https://github.com/D1skanime/zockarchive.git"],
            ) as git, patch.object(
                ci_target.Path, "is_file", return_value=True
            ):
                if overrides:
                    with self.assertRaisesRegex(RuntimeError, "workspace"):
                        ci_target.preflight()
                    git.assert_not_called()
                else:
                    self.assertEqual(ci_target.preflight(), root)

    def test_all_inherited_target_overrides_fail_before_git(self):
        for key in (
            "DB_HOST",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWD",
            "REDIS_HOST",
            "REDIS_URL",
            "DATABASE_URL",
            "PHASE34_RUN_TOKEN",
            "COMPOSE_FILE",
            "COMPOSE_PROJECT_NAME",
            "PYTEST_ADDOPTS",
        ):
            with self.subTest(key=key), patch.dict(
                ci_target.os.environ, {**self.workspace, key: "foreign"}, clear=True
            ), patch.object(ci_target.subprocess, "check_output") as git:
                with self.assertRaisesRegex(RuntimeError, "inherited target override"):
                    ci_target.preflight()
                git.assert_not_called()

    def run_gate(self, gate, failure=False, shard=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        run = MagicMock()
        run.evidence = Path(temporary.name)
        if failure:
            run.exec.side_effect = RuntimeError("native command failed")
        with patch.object(ci_target, "preflight"), patch.object(
            ci_target,
            "tracked_test_files",
            return_value=[f"tests/test_case_{index}.py" for index in range(16)],
        ):
            with patch.object(ci_target, "CIRun", return_value=run):
                if failure:
                    with self.assertRaisesRegex(RuntimeError, "native command"):
                        ci_target.execute("mariadb", gate, shard)
                else:
                    ci_target.execute("mariadb", gate, shard)
        run.start.assert_called_once()
        run.close.assert_called_once()
        result = json.loads((run.evidence / "ci-result.json").read_text())
        self.assertEqual(result["passed"], not failure)
        return run

    def test_schema_preserves_every_existing_command_in_order(self):
        run = self.run_gate("schema")
        self.assertEqual(
            [call.args[0] for call in run.exec.call_args_list],
            ci_target.schema_commands(),
        )

    def test_native_schema_failure_propagates_and_cleans(self):
        run = self.run_gate("schema", failure=True)
        self.assertEqual(run.exec.call_count, 1)

    def test_pytest_preserves_complete_suite_and_owned_output(self):
        command = self.run_gate("pytest").exec.call_args
        self.assertEqual(command.args[0][-1], ".")
        self.assertNotIn("-n", command.args[0])
        self.assertIn("--cov", command.args[0])
        self.assertEqual(
            command.kwargs["extra"]["COVERAGE_FILE"], "/phase34/owned/.coverage"
        )

    def test_pytest_executes_only_the_selected_complete_files(self):
        run = self.run_gate("pytest", shard=2)
        command = run.exec.call_args.args[0]
        self.assertEqual(command[-2:], ["tests/test_case_1.py", "tests/test_case_9.py"])
        self.assertNotIn(".", command)
        receipt = json.loads((run.evidence / "shard-files.json").read_text())
        self.assertEqual(receipt["shard"], 2)
        self.assertEqual(len(receipt["all_files"]), 16)

    def test_eight_shards_cover_every_file_once(self):
        files = sorted(
            [f"tests/test_case_{index}.py" for index in range(101)]
            + ["tools/tests/test_guard.py"]
        )
        shards = [ci_target.shard_files(files, index) for index in range(1, 9)]
        flattened = [name for shard in shards for name in shard]
        self.assertCountEqual(flattened, files)
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertTrue(all(shards))

    def test_invalid_shard_is_refused(self):
        for shard in (0, 9):
            with self.assertRaisesRegex(RuntimeError, "invalid CI shard"):
                ci_target.shard_files(["tests/test_guard.py"], shard)

    def test_tracked_discovery_uses_declared_pytest_patterns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "backend").mkdir()
            (root / "backend/pytest.ini").write_text(
                "[pytest]\npython_files = test_*.py special_*.py\n"
            )
            names = "\0".join(
                [
                    "backend/tests/test_one.py",
                    "backend/tools/tests/test_guard.py",
                    "backend/tests/helpers.py",
                    "backend/tests/special_boundary.py",
                    "backend/tests/legacy_test.py",
                ]
            )
            with patch.object(ci_target.subprocess, "check_output", return_value=names):
                self.assertEqual(
                    ci_target.tracked_test_files(root),
                    [
                        "tests/special_boundary.py",
                        "tests/test_one.py",
                        "tools/tests/test_guard.py",
                    ],
                )

    def test_snapshot_prunes_only_untracked_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            original = source / "untracked.py"
            original.write_text("source remains")
            snapshot = root / "checkout"
            snapshot.mkdir()
            (snapshot / "tracked.py").write_text("tracked")
            (snapshot / "untracked.py").write_text("copied")
            with patch.object(
                ci_target, "prepare_snapshot", return_value=(root / "Games", snapshot)
            ):
                with patch.object(
                    ci_target.subprocess, "check_output", return_value="tracked.py\0"
                ):
                    ci_target.prepare_ci_snapshot(root, source)
            self.assertTrue((snapshot / "tracked.py").is_file())
            self.assertFalse((snapshot / "untracked.py").exists())
            self.assertEqual(original.read_text(), "source remains")

    def test_snapshot_keeps_legacy_fixture_separate_from_synthetic_games(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            fixture = repo / "tests/fixtures/model/game.bin"
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(b"committed PC fixture")
            (fixture.parent / "untracked.bin").write_bytes(b"private")
            games = root / "Games"
            (games / "SNES Super Nintendo").mkdir(parents=True)
            synthetic = games / "SNES Super Nintendo/synthetic.bin"
            synthetic.write_bytes(b"synthetic")
            snapshot = root / "checkout"
            legacy = snapshot / "backend/romm_test/library/n64/roms/game.z64"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"committed legacy fixture")
            tracked = "\0".join(
                [
                    "backend/romm_test/library/n64/roms/game.z64",
                    "tests/fixtures/model/game.bin",
                ]
            )
            with patch.object(
                ci_target, "prepare_snapshot", return_value=(games, snapshot)
            ):
                with patch.object(
                    ci_target.subprocess, "check_output", return_value=tracked
                ):
                    ci_target.prepare_ci_snapshot(root, repo)
            self.assertEqual(synthetic.read_bytes(), b"synthetic")
            self.assertFalse((games / "n64").exists())
            self.assertEqual(legacy.read_bytes(), b"committed legacy fixture")
            self.assertEqual(
                (snapshot / "tests/fixtures/model/game.bin").read_bytes(),
                fixture.read_bytes(),
            )
            self.assertFalse((snapshot / "tests/fixtures/model/untracked.bin").exists())
            self.assertEqual(
                (fixture.parent / "untracked.bin").read_bytes(), b"private"
            )

    def test_validator_support_is_exact_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                ci_target.phase34.tempfile, "mkdtemp", return_value=directory
            ):
                run = ci_target.CIRun("mariadb")
            config = json.loads(run.override.read_text())
            mount = config["services"]["runner"]["volumes"][0]
            self.assertIs(mount["read_only"], True)
            self.assertEqual(mount["target"], "/app/" + ci_target.VALIDATOR)
            self.assertEqual(
                Path(mount["source"]).read_bytes(),
                (ci_target.phase34.REPO / ci_target.VALIDATOR).read_bytes(),
            )
            self.assertTrue((run.evidence / "test-support.json").is_file())
            fixtures = config["services"]["runner"]["volumes"][1]
            self.assertEqual(fixtures["target"], "/app/tests/fixtures")
            self.assertIs(fixtures["read_only"], True)
            docker = config["services"]["runner"]["volumes"][2]
            self.assertEqual(docker["target"], "/app/docker")
            self.assertIs(docker["read_only"], True)
            guide = config["services"]["runner"]["volumes"][3]
            self.assertEqual(guide["target"], "/app/" + ci_target.OPERATOR_GUIDE)
            self.assertIs(guide["read_only"], True)

    def test_start_failure_still_cleans_and_records_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            run = MagicMock()
            run.evidence = Path(directory)
            run.start.side_effect = RuntimeError("target refused")
            with patch.object(ci_target, "preflight"):
                with patch.object(ci_target, "CIRun", return_value=run):
                    with self.assertRaisesRegex(RuntimeError, "target refused"):
                        ci_target.execute("postgresql", "pytest")
            run.close.assert_called_once()
            self.assertFalse(
                json.loads((run.evidence / "ci-result.json").read_text())["passed"]
            )


if __name__ == "__main__":
    unittest.main()
