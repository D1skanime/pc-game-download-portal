"""Portable acceptance contract checks, without canonical host assumptions."""

import json
import sys
import tempfile
import unittest
import zipfile
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


class ArtifactContracts(unittest.TestCase):
    def setUp(self):
        from phase36_receipts import digest

        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.evidence = self.root / "run"
        self.evidence.mkdir()
        self.source = {"files": {"backend/example.py": "a" * 64}}
        values = {
            "code-before.json": self.source,
            "cleanup.json": {
                "clean": True,
                "snapshot_removed": True,
                "source_unchanged": True,
                "remaining": dict.fromkeys(("container", "network", "volume"), []),
                "exact_resources": {
                    kind: [kind + "-owned"]
                    for kind in ("container", "network", "volume")
                },
            },
            "commands.json": [{"command": ["checked"], "exit": 0}],
            "result.json": {
                "phase": 36,
                "kind": "security",
                "dialect": "static",
                "passed": True,
                "threats": dict.fromkeys(("T-36-14", "T-36-15", "T-36-16"), "resolved"),
            },
        }
        for name, value in values.items():
            (self.evidence / name).write_text(json.dumps(value))
        self.entry = {
            "kind": "security",
            "dialect": "static",
            "evidence": "run",
            "artifacts": {name: digest(self.evidence / name) for name in values},
        }

    def validate(self):
        from phase36_receipts import validate_entry

        return validate_entry(self.entry, self.root, self.source)

    def mutate(self, name, transform):
        from phase36_receipts import digest

        path = self.evidence / name
        value = json.loads(path.read_text())
        transform(value)
        path.write_text(json.dumps(value))
        self.entry["artifacts"][name] = digest(path)

    def test_accepts_digest_checked_security(self):
        self.assertEqual(self.validate(), ("security", "static"))

    def test_rejects_artifact_tamper(self):
        (self.evidence / "result.json").write_text("{}")
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_missing_artifact(self):
        (self.evidence / "cleanup.json").unlink()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_security_barrier_removed_even_with_new_digest(self):
        self.mutate("result.json", lambda value: value["threats"].pop("T-36-14"))
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_partial_cleanup_even_with_new_digest(self):
        self.mutate("cleanup.json", lambda value: value.update(snapshot_removed=False))
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_wrong_source_even_with_new_digest(self):
        self.mutate(
            "code-before.json",
            lambda value: value["files"].update({"backend/example.py": "b" * 64}),
        )
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_wrong_dialect(self):
        self.entry["dialect"] = "postgresql"
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_wrong_scenario(self):
        self.mutate("result.json", lambda value: value.update(kind="browser"))
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_failed_commands(self):
        self.mutate("commands.json", lambda value: value[0].update(exit=1))
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_traversal(self):
        self.entry["evidence"] = "../run"
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_symlink(self):
        link = self.root / "linked"
        try:
            link.symlink_to(self.evidence, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation unavailable")
        self.entry["evidence"] = "linked"
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_partial_final_gate_set(self):
        from phase36_receipts import validate_index

        with self.assertRaises(RuntimeError):
            validate_index(
                {"phase": 36, "source_hashes": self.source, "entries": [self.entry]},
                self.root,
                current=self.source,
            )


class SanitizationContracts(unittest.TestCase):
    def test_scrubs_token_jwt_and_headers_inside_trace(self):
        from phase36_receipts import sanitize

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token = "a" * 32
            trace = root / "trace.zip"
            value = {
                "headers": [{"name": "Cookie", "value": "session-secret"}],
                "action": "fill " + token,
                "response": "eyJhbGciOiJIUzI1NiJ9.secret.signature",
            }
            with zipfile.ZipFile(trace, "w") as archive:
                archive.writestr("test.trace", json.dumps(value))
            sanitize(root, token)
            with zipfile.ZipFile(trace) as archive:
                data = archive.read("test.trace").decode()
            self.assertNotIn(token, data)
            self.assertNotIn("session-secret", data)
            self.assertNotIn("eyJ", data)


class ProviderObservationContracts(unittest.TestCase):
    def response(self, markup=False):
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch

        import phase36_description_worker as worker

        rows = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "provider-control.json").write_text(
                json.dumps({"enabled": True, "markup": markup})
            )
            with patch.object(worker, "EVIDENCE", root), patch.object(
                worker, "record", side_effect=lambda kind, **facts: rows.append(facts)
            ):
                server = ThreadingHTTPServer(("127.0.0.1", 0), worker.Provider)
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    url = "http://127.0.0.1:" + str(server.server_port)
                    data = urllib.request.urlopen(
                        url + "/api/appdetails?appids=1245620&l=german", timeout=5
                    ).read()
                finally:
                    server.shutdown()
                    thread.join()
                    server.server_close()
        return json.loads(data), rows[0], data

    def test_observed_payload_digest_matches_actual_wire_bytes(self):
        import hashlib

        _, row, data = self.response()
        self.assertEqual(row.get("response_sha256"), hashlib.sha256(data).hexdigest())
        self.assertEqual(row.get("requested_language"), "german")
        self.assertNotIn("source_language", row)

    def test_markup_control_reaches_provider_payload(self):
        payload, _, _ = self.response(markup=True)
        self.assertIn("<img", payload["1245620"]["data"]["short_description"])


if __name__ == "__main__":
    unittest.main()
