"""Portable adversarial acceptance-receipt regressions."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase36_description_probe import validate_receipt


class ReceiptTests(unittest.TestCase):
    def test_old_inventory_receipt_cannot_claim_connected_description_proof(self):
        receipt: dict[str, Any] = {
            "passed": True,
            "scenario": "descriptions",
            "observed_worker": True,
            "source_unchanged": True,
            "stages": ["cold", "warm-manual", "warm-scheduled"],
            "cleanup": {
                "clean": True,
                "snapshot_removed": True,
                "source_unchanged": True,
                "remaining": {},
                "exact_resources": {
                    "container": ["owned"],
                    "volume": ["owned"],
                    "network": ["owned"],
                },
            },
        }
        with self.assertRaisesRegex(RuntimeError, "description"):
            validate_receipt(copy.deepcopy(receipt))

    def test_authority_receipt_requires_both_providers_at_both_boundaries(self):
        receipt: dict[str, Any] = {
            "passed": True,
            "observed_worker": True,
            "description_stages": ["repair-de"],
            "source_hashes": {"actual": "a" * 64},
            "wire_requests": [{"endpoint": "/api/appdetails"}],
            "scenario": "authority",
            "cleanup": {
                "clean": True,
                "snapshot_removed": True,
                "source_unchanged": True,
                "remaining": {},
                "exact_resources": {
                    "container": ["owned"],
                    "volume": ["owned"],
                    "network": ["owned"],
                },
            },
        }
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_receipt(receipt)

    def test_identity_expectations_are_injected_and_fail_closed(self):
        from phase36_description_probe import assert_identity

        expected = (
            "Linux",
            "fixture-host",
            Path("/owned/repo"),
            "fixture-branch",
            "fixture-origin",
        )
        assert_identity(expected, expected)
        for index in range(len(expected)):
            actual = list(expected)
            actual[index] = "foreign"
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                assert_identity(tuple(actual), expected)

    def test_foreign_fixture_root_refused_before_preparation(self):
        from phase36_description_fixture import prepare

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "fixture"):
                prepare(Path(directory), Path(directory))

    def test_source_symlink_refused(self):
        from phase35_incremental_scan_fixture import manifest

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "foreign").symlink_to(root / "absent")
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                manifest(root)

    def test_external_sql_and_live_url_environment_refused(self):
        from phase34_target_guard import expected_environment, validate_target

        environment = expected_environment("a" * 32, "mariadb")
        for key, value in (
            ("DB_HOST", "live-db"),
            ("DB_NAME", "romm"),
            ("PHASE34_RUN_TOKEN", "wrong"),
            ("REDIS_URL", "redis://live"),
            ("DATABASE_URL", "postgres://live"),
        ):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_target({**environment, key: value}, verify_redis=False)

    def test_authority_rejects_changed_catalog_or_false_success(self):
        from phase36_description_assertions import assert_authority

        valid = {
            "mutated": {"text": "protected"},
            "after": {"text": "protected"},
            "stats_before": {"provider_requests": 0},
            "stats_after": {"provider_requests": 0},
            "state": "failed",
            "job_status": "finished",
            "intentional_mutation": {"verified": True},
        }
        assert_authority(valid)
        for key, value in (
            ("after", {}),
            ("stats_after", {"provider_requests": 1}),
            ("state", "completed"),
            ("job_status", "started"),
            ("intentional_mutation", {}),
        ):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                assert_authority({**valid, key: value})

    def test_stale_source_hash_and_fabricated_cleanup_are_rejected(self):
        source = {"sha256": "a" * 64, "files": {"backend/owned.py": "b" * 64}}
        receipt: dict[str, Any] = {
            "passed": True,
            "scenario": "descriptions",
            "observed_worker": True,
            "description_stages": ["repair-de"],
            "source_hashes": source,
            "wire_requests": [{"endpoint": "/api/appdetails"}],
            "cleanup": {
                "clean": True,
                "snapshot_removed": True,
                "source_unchanged": True,
                "remaining": {},
                "exact_resources": {
                    "container": ["owned"],
                    "volume": ["owned"],
                    "network": ["owned"],
                },
            },
        }
        validate_receipt(receipt, source)
        with self.assertRaisesRegex(RuntimeError, "stale"):
            validate_receipt(receipt, {**source, "sha256": "c" * 64})
        for key in ("clean", "snapshot_removed", "source_unchanged"):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_receipt(
                    {**receipt, "cleanup": {**receipt["cleanup"], key: False}}
                )
        with self.assertRaises(RuntimeError):
            validate_receipt(
                {
                    **receipt,
                    "cleanup": {
                        **receipt["cleanup"],
                        "remaining": {"container": ["foreign"]},
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()
