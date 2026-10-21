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

    def test_alternate_root_is_an_explicit_post_setup_fixture_edit(self):
        with tempfile.TemporaryDirectory(
            prefix="pgdp34-" + "a" * 32 + "-"
        ) as directory:
            root = Path(directory)
            games = root / "Games"
            games.mkdir()
            with patch.object(
                self.fixture,
                "original_prepare",
                return_value=(games, root / "checkout"),
            ):
                self.fixture.prepare(root, root / "repo")
            self.assertEqual(
                {path.name for path in games.iterdir()}, {"pc", "My Games"}
            )
            before = self.fixture.manifest(games)
            after = self.fixture.edit(root, "alternate-root")
            self.assertNotEqual(before, after)
            alternate = games / "alternate/pc/Known.Game/Base/game.bin"
            self.assertEqual(alternate.read_bytes(), b"different synthetic root bytes")

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


class BrowserReceiptGuards(unittest.TestCase):
    def test_missing_browser_receipt_rejected(self):
        from phase35_browser_receipts import validate_browser

        with self.assertRaises(RuntimeError):
            validate_browser({})

    def test_unsafe_browser_target_rejected(self):
        from phase35_browser import browser_config

        with self.assertRaises(RuntimeError):
            browser_config("http://127.0.0.1:3100")


class BrowserReceiptTampering(unittest.TestCase):
    def browser(self):
        from phase35_browser_receipts import REQUIRED

        return {
            "passed": True,
            "checks": dict.fromkeys(REQUIRED, True),
            "screenshots": [
                {"case": str(width) + "-" + theme}
                for width in (320, 600, 960, 1280, 1920, 3840)
                for theme in ("dark", "light")
            ],
            "variants": ["de_DE", "zh_CN", "zoom200", "reduced-motion"],
        }

    def test_complete_browser_matrix_passes(self):
        from phase35_browser_receipts import validate_browser

        validate_browser(self.browser())

    def test_each_missing_or_failed_scenario_rejected(self):
        from phase35_browser_receipts import REQUIRED, validate_browser

        for key in REQUIRED:
            for value in (False, None):
                receipt = self.browser()
                receipt["checks"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(
                    RuntimeError
                ):
                    validate_browser(receipt)

    def test_each_missing_responsive_theme_rejected(self):
        from phase35_browser_receipts import validate_browser

        for index in range(12):
            receipt = self.browser()
            receipt["screenshots"].pop(index)
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                validate_browser(receipt)

    def test_missing_locale_or_accessibility_variant_rejected(self):
        from phase35_browser_receipts import validate_browser

        for index in range(4):
            receipt = self.browser()
            receipt["variants"].pop(index)
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                validate_browser(receipt)

    def test_empty_source_manifest_rejected(self):
        from phase35_browser_receipts import current_sources

        with self.assertRaises(RuntimeError):
            current_sources({"files": {}})

    def test_partial_source_manifest_rejected(self):
        from phase35_browser_receipts import current_sources

        with self.assertRaises(RuntimeError):
            current_sources({"files": {"backend/../CLAUDE.md": "0" * 64}})


class RetainedBrowserEvidenceTampering(unittest.TestCase):
    def test_changed_artifact_hash_is_rejected_before_reading_claims(self):
        import tempfile
        from unittest.mock import patch

        from phase35_browser_receipts import verify_retained

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "commands.json").write_text("tampered")
            entry = {"evidence": directory, "files": {"commands.json": "0" * 64}}
            with patch(
                "phase34_evidence.run_directory", return_value=root
            ), self.assertRaisesRegex(RuntimeError, "tampered"):
                verify_retained(entry)

    def test_incomplete_quality_command_set_is_rejected(self):
        import json
        import tempfile

        from phase35_browser_receipts import validate_result

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "phase35-browser-result.json").write_text(
                json.dumps(
                    {
                        "passed": True,
                        "kind": "quality",
                        "checks": [{"command": ["npm", "run", "test"], "exit": 0}],
                    }
                )
            )
            (root / "commands.json").write_text(json.dumps([{"exit": 0}]))
            (root / "cleanup.json").write_text(
                json.dumps(
                    {
                        "clean": True,
                        "snapshot_removed": True,
                        "source_unchanged": True,
                        "remaining": {"container": [], "network": [], "volume": []},
                    }
                )
            )
            with self.assertRaisesRegex(RuntimeError, "quality"):
                validate_result(root, exact=False)
