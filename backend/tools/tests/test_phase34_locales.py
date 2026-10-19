"""Native plural category counts differ without losing interpolation tokens."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase34_fixtures import interpolation_matches


class LocaleInterpolationTests(unittest.TestCase):
    def test_native_plural_categories_preserve_variables(self):
        self.assertTrue(
            interpolation_matches(
                "{count} platform | {count} platforms",
                "{count} platforma | {count} platformy | {count} platforem | {count} platform",
            )
        )

    def test_missing_plural_variable_is_rejected(self):
        self.assertFalse(
            interpolation_matches(
                "{done}/{total} files | {done}/{total} files",
                "{done} soubor | {done} soubory",
            )
        )

    def test_foreign_variable_is_rejected(self):
        self.assertFalse(
            interpolation_matches(
                "{count} game | {count} games",
                "{count} hra | {path} hry",
            )
        )

    def test_nonplural_repetitions_stay_strict(self):
        self.assertFalse(
            interpolation_matches("{name} replaces {name}", "{name} replaces it")
        )


if __name__ == "__main__":
    unittest.main()
