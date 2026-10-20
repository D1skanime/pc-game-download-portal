"""Fail-closed exact contract generation guards."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ContractGuards(unittest.TestCase):
    def helper(self):
        import phase35_contracts

        return phase35_contracts

    def test_only_owned_loopback_schema_is_accepted(self):
        helper = self.helper()
        run = SimpleNamespace(
            token="a" * 32,
            project="pgdp34-" + "a" * 32,
            manifest={"token": "a" * 32, "project": "pgdp34-" + "a" * 32},
        )
        helper.validate_authority(run, "http://127.0.0.1:3344/openapi.json")
        for target in [
            "http://localhost:3344/openapi.json",
            "http://127.0.0.1:3000/openapi.json",
            "http://dev/openapi.json",
            "https://127.0.0.1:3344/openapi.json",
            "http://127.0.0.1:3344/openapi.json?x=1",
        ]:
            with self.subTest(target=target), self.assertRaises(RuntimeError):
                helper.validate_authority(run, target)
        run.manifest["token"] = "b" * 32
        with self.assertRaises(RuntimeError):
            helper.validate_authority(run, helper.SCHEMA_URL)

    def test_missing_or_mismatched_ownership_is_rejected(self):
        helper = self.helper()
        for manifest in [None, {}, {"token": "a" * 32, "project": "live"}]:
            with self.subTest(manifest=manifest), self.assertRaises(RuntimeError):
                helper.validate_authority(
                    SimpleNamespace(
                        token="a" * 32, project="pgdp34-" + "a" * 32, manifest=manifest
                    ),
                    helper.SCHEMA_URL,
                )

    def test_copy_rejects_source_drift_and_symlinks_before_writes(self):
        helper = self.helper()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source", root / "target"
            source.mkdir()
            target.mkdir()
            (source / "index.ts").write_text("generated")
            (target / "index.ts").write_text("original")
            baseline = helper.generated_manifest(target)
            (target / "index.ts").write_text("concurrent")
            with self.assertRaises(RuntimeError):
                helper.copy_generated(source, target, baseline)
            self.assertEqual((target / "index.ts").read_text(), "concurrent")
            (target / "index.ts").write_text("original")
            (source / "escape.ts").symlink_to(target / "index.ts")
            with self.assertRaises(RuntimeError):
                helper.copy_generated(source, target, baseline)
            self.assertEqual((target / "index.ts").read_text(), "original")
