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
            "GITHUB_REPOSITORY": "D1skanime/pc-game-download-portal",
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

    def run_gate(self, gate, failure=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        run = MagicMock()
        run.evidence = Path(temporary.name)
        if failure:
            run.exec.side_effect = RuntimeError("native command failed")
        with patch.object(ci_target, "preflight"):
            with patch.object(ci_target, "CIRun", return_value=run):
                if failure:
                    with self.assertRaisesRegex(RuntimeError, "native command"):
                        ci_target.execute("mariadb", gate)
                else:
                    ci_target.execute("mariadb", gate)
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
