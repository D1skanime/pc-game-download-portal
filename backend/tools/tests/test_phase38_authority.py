"""Source contracts run without Docker or application imports."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase38_authority import validate_identity


def identity(name="pc-game-download-portal"):
    return {
        "system": "Linux",
        "host": "team4slinux",
        "root": "/home/d1sk/pc-game-download-portal",
        "workspace": "/home/d1sk/pc-game-download-portal",
        "branch": "codex/phase-38-zockarchive-rebranding",
        "origin": "https://github.com/D1skanime/" + name + ".git",
        "project": "RomM PC Library",
        "state": "Phase38",
        "context": "ZA-BRAND-09",
        "proof": {
            "id": 1415481891,
            "node_id": "R_kgDOVF6KIw",
            "full_name": "D1skanime/" + name,
        },
        "overrides": {},
    }


class AuthorityTests(unittest.TestCase):
    def test_both_exact_same_id_states_pass(self):
        for name in ("pc-game-download-portal", "zockarchive"):
            self.assertEqual(validate_identity(identity(name)), identity(name))

    def test_wrong_execution_identity_rejected(self):
        for key, value in (
            ("system", "Windows"),
            ("host", "foreign"),
            ("root", "/tmp/foreign"),
            ("workspace", "/tmp/foreign"),
            ("branch", "main"),
            ("project", "Other"),
            ("state", "Phase37"),
            ("context", "Other"),
        ):
            with self.subTest(key=key):
                actual = identity()
                actual[key] = value
                with self.assertRaisesRegex(RuntimeError, "identity"):
                    validate_identity(actual)

    def test_wrong_immutable_id_owner_and_pair_rejected(self):
        for key, value in (
            ("id", 1),
            ("node_id", "foreign"),
            ("full_name", "foreign/pc-game-download-portal"),
            ("full_name", "D1skanime/zockarchive"),
        ):
            with self.subTest(key=key, value=value):
                actual = identity()
                actual["proof"][key] = value
                with self.assertRaisesRegex(RuntimeError, "identity"):
                    validate_identity(actual)

    def test_missing_live_proof_rejected(self):
        actual = identity()
        actual["proof"] = None
        with self.assertRaisesRegex(RuntimeError, "identity"):
            validate_identity(actual)

    def test_foreign_origin_rejected(self):
        for origin in (
            "https://foreign.example/D1skanime/pc-game-download-portal.git",
            "https://github.com/foreign/pc-game-download-portal.git",
            "https://github.com/D1skanime/zockarchive.git",
        ):
            actual = identity()
            actual["origin"] = origin
            with self.assertRaisesRegex(RuntimeError, "identity"):
                validate_identity(actual)

    def test_every_inherited_target_override_rejected(self):
        for key in (
            "DB_HOST",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWD",
            "DB_PORT",
            "DB_DRIVER",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_URL",
            "DATABASE_URL",
            "PHASE34_RUN_TOKEN",
            "PHASE34_MANIFEST",
            "COMPOSE_FILE",
            "COMPOSE_PROJECT_NAME",
            "PYTEST_ADDOPTS",
            "P34_REPO",
            "P34_RUNNER_IMAGE",
            "P34_GAMES",
            "P34_CONTROL",
        ):
            actual = identity()
            actual["overrides"] = {key: "foreign"}
            with self.subTest(key=key), self.assertRaisesRegex(
                RuntimeError, "override"
            ):
                validate_identity(actual)


if __name__ == "__main__":
    unittest.main()
