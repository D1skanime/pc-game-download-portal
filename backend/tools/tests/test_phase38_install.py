"""Negative ownership and populated-state receipts require no Docker resources."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase38_install import validate_volume

TOKEN = "a" * 32
NAME = "pgdp34-" + TOKEN + "_owned"


def volume(name=NAME):
    return {
        "Name": name,
        "Labels": {
            "org.pgdp.phase34.run": TOKEN,
            "com.docker.compose.project": "pgdp34-" + TOKEN,
        },
    }


class InstallTests(unittest.TestCase):
    def test_exact_owned_volume_passes(self):
        self.assertEqual(validate_volume(volume(), TOKEN, NAME), NAME)

    def test_foreign_named_volume_is_rejected_even_with_copied_labels(self):
        with self.assertRaisesRegex(RuntimeError, "identity"):
            validate_volume(volume("production"), TOKEN, "production")

    def test_wrong_owned_volume_is_rejected(self):
        for item in (
            {},
            {"Name": NAME},
            volume("other"),
            {"Name": NAME, "Labels": {"org.pgdp.phase34.run": "b" * 32}},
        ):
            with self.subTest(item=item), self.assertRaisesRegex(
                RuntimeError, "identity"
            ):
                validate_volume(item, TOKEN, NAME)

    def test_missing_or_wrong_project_label_is_rejected(self):
        for project in (None, "production", "pgdp34-" + "b" * 32):
            item = volume()
            item["Labels"]["com.docker.compose.project"] = project
            with self.assertRaisesRegex(RuntimeError, "identity"):
                validate_volume(item, TOKEN, NAME)


if __name__ == "__main__":
    unittest.main()
