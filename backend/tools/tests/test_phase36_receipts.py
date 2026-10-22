"""Portable acceptance contract checks, without canonical host assumptions."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase36_browser import browser_config


class BrowserContracts(unittest.TestCase):
    def test_dedicated_connected_spec(self):
        config = browser_config()
        self.assertEqual(config["testMatch"], "phase36-descriptions.spec.ts")

    def test_isolated_serial_execution(self):
        config = browser_config()
        self.assertEqual(config["workers"], 1)
        self.assertEqual(config["retries"], 0)
        with self.assertRaises(RuntimeError):
            browser_config("http://127.0.0.1:3100")


class ReceiptContracts(unittest.TestCase):
    def test_rejects_historical_phase(self):
        from phase36_receipts import validate_index

        with self.assertRaises(RuntimeError):
            validate_index({"phase": 35, "entries": []}, Path("."))

    def test_rejects_incomplete_phase(self):
        from phase36_receipts import validate_index

        with self.assertRaises(RuntimeError):
            validate_index({"phase": 36, "entries": []}, Path("."))


if __name__ == "__main__":
    unittest.main()
