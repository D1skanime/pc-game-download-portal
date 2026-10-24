"""Host/SQL test-profile boundary and complete-checkout workflow contracts."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_target
import ci_test_profiles as profiles
from phase38_cutover_source import test_membership as receipt_membership


class ProfileTests(unittest.TestCase):
    def test_complete_selection_is_partitioned_without_drops(self):
        sql = ["tests/test_runtime.py", "tools/tests/test_phase38_cutover.py"]
        files = sorted([*sql, *profiles.HOST_TEST_FILES])
        result = profiles.classify_test_files(files)
        self.assertEqual(result["host"], list(profiles.HOST_TEST_FILES))
        self.assertEqual(result["sql"], sql)
        self.assertEqual(result["all"], files)
        self.assertEqual(set(result["host"]) & set(result["sql"]), set())
        self.assertEqual(sorted(result["host"] + result["sql"]), files)

    def test_missing_or_duplicate_required_host_selection_fails(self):
        for files in (
            [],
            list(profiles.HOST_TEST_FILES[:-1]),
            [*profiles.HOST_TEST_FILES, profiles.HOST_TEST_FILES[0]],
        ):
            with self.assertRaisesRegex(RuntimeError, "test profile"):
                profiles.classify_test_files(files)

    def test_readonly_receipts_use_same_complete_selection(self):
        names = ["backend/" + name for name in profiles.HOST_TEST_FILES]
        names += ["backend/tests/test_app.py", "backend/tools/tests/test_guard.py"]
        with patch("phase38_cutover_source.objects", return_value=dict.fromkeys(names)):
            with patch(
                "phase38_cutover_source.git",
                return_value="[pytest]\npython_files = test_*.py\n",
            ):
                selected = receipt_membership("a" * 40)
        self.assertEqual(selected["host"], list(profiles.HOST_TEST_FILES))
        self.assertEqual(
            selected["sql"], ["tests/test_app.py", "tools/tests/test_guard.py"]
        )

    def test_required_host_files_match_actual_tracked_patterns(self):
        root = Path(__file__).resolve().parents[3]
        names = ["backend/" + name for name in profiles.HOST_TEST_FILES]
        with patch.object(
            ci_target.subprocess, "check_output", return_value="\0".join(names)
        ):
            selected = ci_target.tracked_test_files(root)
        self.assertEqual(selected, list(profiles.HOST_TEST_FILES))

    def test_workflow_requires_host_job_with_pinned_prerequisites_and_artifact(self):
        from ci_host_contracts import workflow_contract

        text = """
jobs:
  host-contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955
        with:
          fetch-depth: 0
      - uses: actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c
        with:
          python-version: "3.13"
      - uses: actions/setup-node@a0853c24544627f65ddf259abe73b1d18a591444
        with:
          node-version: "24"
      - run: python3 backend/tools/ci_host_contracts.py
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: host-contracts-evidence
"""
        workflow_contract(text)
        for old, new in (
            ("host-contracts:", "optional-contracts:"),
            ('node-version: "24"', 'node-version: "20"'),
            ("ci_host_contracts.py", "ci_target.py"),
            ("fetch-depth: 0", "fetch-depth: 1"),
        ):
            with self.subTest(old=old):
                with self.assertRaises(RuntimeError):
                    workflow_contract(text.replace(old, new))


if __name__ == "__main__":
    unittest.main()
