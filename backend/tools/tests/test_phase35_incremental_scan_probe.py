"""Stdlib guard and immutable fixture regression checks."""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ProbeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.probe = importlib.import_module("phase35_incremental_scan_probe")
        self.fixture = importlib.import_module("phase35_incremental_scan_fixture")

    def test_wrong_branch_is_rejected(self):
        with patch.object(self.probe.phase34, "host_preflight"), patch.object(
            self.probe, "git_value", return_value="main"
        ):
            with self.assertRaisesRegex(RuntimeError, "branch"):
                self.probe.preflight()

    def test_manifest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "game.bin").write_bytes(b"fixture")
            before = self.fixture.manifest(root)
            (root / "game.bin").write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "source"):
                self.fixture.assert_immutable(root, before)

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "link").symlink_to("/etc")
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                self.fixture.manifest(root)

    def test_edit_rejects_unowned_root(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "fixture"):
                self.fixture.edit(Path(directory), "add")

    def test_edit_restores_top_directory_mtime(self):
        with tempfile.TemporaryDirectory(
            prefix="pgdp34-" + "a" * 32 + "-"
        ) as directory:
            root = Path(directory)
            game = root / "fixture/Games/pc/Known.Game"
            game.mkdir(parents=True)
            before = game.stat().st_mtime_ns
            self.fixture.edit(root, "add")
            self.assertEqual(game.stat().st_mtime_ns, before)
            self.assertTrue((game / "DLC/Expansion/content.bin").is_file())

    def test_unknown_edit_is_rejected(self):
        with tempfile.TemporaryDirectory(
            prefix="pgdp34-" + "a" * 32 + "-"
        ) as directory:
            with self.assertRaisesRegex(RuntimeError, "edit"):
                self.fixture.edit(Path(directory), "../escape")

    def test_partial_and_failed_receipts_are_rejected(self):
        for receipt in ({}, {"passed": True}, {"passed": False}):
            with self.subTest(receipt=receipt), self.assertRaises(RuntimeError):
                self.probe.validate_receipt(receipt)

    def test_remaining_resource_rejects_receipt(self):
        receipt = {
            "scenario": "incremental",
            "passed": True,
            "observed_worker": True,
            "stages": ["cold", "warm-manual", "warm-scheduled"],
            "source_unchanged": True,
            "cleanup": {
                "clean": True,
                "snapshot_removed": True,
                "source_unchanged": True,
                "remaining": {"container": ["alien"]},
            },
        }
        with self.assertRaisesRegex(RuntimeError, "cleanup"):
            self.probe.validate_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
