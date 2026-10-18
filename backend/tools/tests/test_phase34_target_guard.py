"""Host-only guard tests. Never import the application or parent conftest."""

import builtins
import os
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[2]


class ImportBoundaryTests(unittest.TestCase):
    def test_unsafe_collection_stops_before_dependencies(self):
        calls = []
        original = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in {
                "alembic",
                "pytest",
                "sqlalchemy",
                "config",
                "handler",
            }:
                calls.append(name)
                raise AssertionError("unsafe dependency import before target guard")
            return original(name, *args, **kwargs)

        with patch.dict(os.environ, {}, clear=True), patch.object(
            sys, "path", [str(BACKEND), *sys.path]
        ), patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaisesRegex(RuntimeError, "Phase34 target refused"):
                runpy.run_path(str(BACKEND / "tests/conftest.py"))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
