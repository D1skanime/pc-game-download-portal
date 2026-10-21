"""Reject false catalog, media and authority acceptance receipts."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class AcceptanceInvariantTests(unittest.TestCase):
    def test_media_replacement_with_same_bytes_is_rejected(self):
        from phase35_incremental_assertions import assert_preserved

        with self.assertRaisesRegex(RuntimeError, "media"):
            assert_preserved(
                {"media": [{"inode": 1}]}, {"media": [{"inode": 2}]}, keys=("media",)
            )

    def test_authority_catalog_write_is_rejected(self):
        from phase35_incremental_assertions import assert_preserved

        with self.assertRaisesRegex(RuntimeError, "baselines"):
            assert_preserved(
                {"baselines": [{"digest": "old"}]},
                {"baselines": [{"digest": "stale"}]},
                keys=("baselines",),
            )

    def test_component_manifest_mismatch_is_rejected(self):
        from phase35_incremental_assertions import assert_game_files

        with self.assertRaisesRegex(RuntimeError, "ordinary"):
            assert_game_files(
                {
                    "roms": [{"id": 1, "name": "Known.Game"}],
                    "files": [],
                    "components": [],
                    "members": [],
                },
                {"Base/game.bin": {"size": 4, "sha256": "x"}},
            )

    def test_missing_barrier_is_not_authority_evidence(self):
        from phase35_incremental_assertions import assert_authority

        with self.assertRaisesRegex(RuntimeError, "barrier"):
            assert_authority({"before": {}, "after": {}})

    def test_manifest_paths_are_game_relative(self):
        from phase35_incremental_assertions import assert_game_files

        data = {
            "roms": [{"id": 1, "name": "Known.Game"}],
            "files": [
                {"rom_id": 1, "path": "Known.Game/Base", "name": "game.bin", "size": 4}
            ],
            "components": [{"id": 2, "rom_id": 1, "name": "Base"}],
            "members": [
                {
                    "component_id": 2,
                    "path": "Base/game.bin",
                    "size": 4,
                    "sha256": "x",
                    "missing": False,
                }
            ],
        }
        assert_game_files(data, {"Base/game.bin": {"size": 4, "sha256": "x"}})

    def test_authority_runner_requires_every_live_barrier(self):
        from phase35_incremental_scan_probe import validate_receipt

        receipt = {
            "scenario": "authority",
            "passed": True,
            "observed_worker": True,
            "source_unchanged": True,
            "stages": ["cold", "warm-manual", "warm-scheduled"],
            "cleanup": {
                "clean": True,
                "snapshot_removed": True,
                "source_unchanged": True,
                "remaining": {},
            },
        }
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_receipt(receipt)
