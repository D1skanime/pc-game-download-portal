"""Evidence must never turn missing, changed or failed runs into acceptance."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase34_evidence import (
    read_json,
    run_directory,
    validate_fault_receipts,
    validate_index,
)


class EvidenceTests(unittest.TestCase):
    def test_empty_index_is_incomplete(self):
        errors = validate_index({"runs": []})
        self.assertIn("missing passing gate: faults", errors)
        self.assertIn("shared live UAT has not been accepted", errors)

    def test_foreign_run_receipt_refused(self):
        with self.assertRaisesRegex(RuntimeError, "exact disposable"):
            run_directory("/home/d1sk/pc-game-download-portal/Media/evidence")

    def test_changed_fingerprint_refused(self):
        with tempfile.TemporaryDirectory(prefix="pgdp34-" + "a" * 32 + "-") as root:
            evidence = Path(root) / "evidence"
            evidence.mkdir()
            (evidence / "commands.json").write_text("[]")
            row = {
                "gate": "faults",
                "evidence": str(evidence),
                "passed": True,
                "files": {"commands.json": "incorrect"},
            }
            self.assertTrue(
                any("changed" in error for error in validate_index({"runs": [row]}))
            )

    def test_symlink_receipt_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path / "real").write_text(json.dumps({"passed": True}))
            (path / "link").symlink_to(path / "real")
            with self.assertRaisesRegex(RuntimeError, "unsafe"):
                read_json(path / "link")

    def test_missing_stable_output_orders_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path / "stable-output-faults.json").write_text(
                json.dumps({"schema": 1, "proofs": []})
            )
            with self.assertRaisesRegex(RuntimeError, "missing stable-output"):
                validate_fault_receipts(path)

    def test_mismatched_stable_output_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path / "stable-output-faults.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "proofs": [
                            {
                                "family": "ra",
                                "order": "stale_after_cancel",
                                "passed": True,
                                "verifier_exit_confirmed": True,
                                "expected_sha256": "a" * 64,
                                "observed_sha256": "b" * 64,
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(RuntimeError, "invalid stable-output"):
                validate_fault_receipts(path)


if __name__ == "__main__":
    unittest.main()
