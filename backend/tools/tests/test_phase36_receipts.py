"""Portable acceptance contract checks, without canonical host assumptions."""

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

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
        self.entry: dict[str, Any] = {
            "kind": "security",
            "dialect": "static",
            "evidence": "run",
            "dependencies": {
                "scenario": "security",
                "files": self.source["files"].copy(),
                "snapshot_delta": [],
            },
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

    def test_rejects_removed_relevant_dependency(self):
        self.entry["dependencies"]["files"] = {}
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_dependency_from_another_scenario(self):
        self.entry["dependencies"]["scenario"] = "browser"
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_tampered_relevant_dependency_hash(self):
        self.entry["dependencies"]["files"]["backend/example.py"] = "b" * 64
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_unexplained_snapshot_delta(self):
        self.entry["dependencies"]["snapshot_delta"] = [{"file": "invented.py"}]
        with self.assertRaises(RuntimeError):
            self.validate()

    def backend_result(self, skips=None, count=None):
        RVZ_SKIPS = {
            "tests/utils/test_rvz_hasher.py::test_real_gamecube_rvz_matches_retroachievements_hash": "mock GameCube RVZ not present",
            "tests/utils/test_rvz_hasher.py::test_real_wii_rvz_matches_retroachievements_hash": "mock Wii RVZ not present",
        }

        rows = (
            [
                {"nodeid": nodeid, "reason": reason}
                for nodeid, reason in RVZ_SKIPS.items()
            ]
            if skips is None
            else skips
        )
        self.entry.update(kind="backend", dialect="mariadb")
        self.mutate(
            "result.json",
            lambda value: value.update(
                kind="backend",
                dialect="mariadb",
                full_suite=True,
                tests=916,
                failures=0,
                errors=0,
                skipped=len(rows) if count is None else count,
                skip_details=rows,
            ),
        )

    def test_backend_accepts_only_recorded_missing_rvz_fixtures(self):
        from phase36_quality import validate_backend_summary

        self.backend_result()
        validate_backend_summary(
            json.loads((self.evidence / "result.json").read_text())
        )
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_inherited_permission_skip_requires_verified_root_environment(self):
        from phase36_quality import validate_backend_summary

        row = {
            "nodeid": "tests/handler/filesystem/test_roms_handler.py::TestExtractCHDHash::test_extract_chd_hash_permission_error",
            "reason": "root bypasses file permission bits",
            "environment": {"runner_config_user": "", "pytest_exec_user": "default"},
        }
        self.backend_result([row])
        payload = json.loads((self.evidence / "result.json").read_text())
        validate_backend_summary(payload)
        for environment in (
            {},
            {"runner_config_user": "1000", "pytest_exec_user": "default"},
            {"runner_config_user": "", "pytest_exec_user": "override"},
        ):
            with self.subTest(environment=environment), self.assertRaises(RuntimeError):
                validate_backend_summary(
                    {**payload, "skip_details": [{**row, "environment": environment}]}
                )

    def test_exact_historical_delete_skips_stay_source_bound_and_unexecuted(self):
        from phase36_quality import validate_backend_summary

        names = (
            "test_delete_rom_file_success",
            "test_delete_rom_file_wrong_rom_returns_404",
            "test_delete_rom_file_unknown_file_returns_404",
            "test_delete_rom_file_tolerates_missing_disk_file",
            "test_delete_rom_file_forbidden_viewer",
            "test_delete_rom_file_forbidden_without_delete_grant",
            "test_delete_rom_file_allowed_for_editor",
        )
        rows = [
            {
                "nodeid": "tests/endpoints/roms/test_files.py::" + name,
                "reason": "Superseded by bounded external denial matrix",
                "baseline_source_sha256": "9716bb9f42ae8efdb054fff981af6822c5e9d4884654b784575baef4d8f96ee3",
                "disposition": "historical_unexecuted_http_delete_role_flows",
            }
            for name in names
        ]
        self.backend_result(rows)
        payload = json.loads((self.evidence / "result.json").read_text())
        validate_backend_summary(payload)
        self.assertEqual(payload["skipped"], 7)
        for key, value in (
            ("nodeid", "tools/tests/test_phase36_receipts.py::test_security"),
            ("reason", "different reason"),
            ("baseline_source_sha256", "b" * 64),
            ("disposition", "passed"),
        ):
            changed = [{**row} for row in rows]
            changed[0][key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_backend_summary({**payload, "skip_details": changed})
        with self.assertRaises(RuntimeError):
            validate_backend_summary({**payload, "skipped": 6})
        with self.assertRaises(RuntimeError):
            validate_backend_summary(
                {**payload, "skip_details": rows[:-1], "skipped": 6}
            )

    def test_backend_rejects_unknown_skip(self):
        self.backend_result([{"nodeid": "tests/new.py::test_new", "reason": "missing"}])
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_backend_rejects_changed_skip_reason(self):
        self.backend_result()
        self.mutate(
            "result.json",
            lambda value: value["skip_details"][0].update(reason="different"),
        )
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_backend_rejects_skip_count_mismatch(self):
        self.backend_result(count=0)
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_backend_rejects_duplicate_skip(self):
        self.backend_result()
        self.mutate(
            "result.json",
            lambda value: value.update(
                skip_details=[value["skip_details"][0]] * 2,
            ),
        )
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
    def test_unchanged_read_only_artifact_needs_no_write(self):
        from unittest.mock import patch

        from phase36_receipts import sanitize

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "worker.pid"
            artifact.write_bytes(b"20\n")
            with patch.object(
                Path, "write_bytes", side_effect=PermissionError("read-only evidence")
            ):
                sanitize(root, "secret-token")
            artifact.write_text("secret-token")
            with patch.object(
                Path, "write_bytes", side_effect=PermissionError("read-only evidence")
            ):
                with self.assertRaises(PermissionError):
                    sanitize(root, "secret-token")

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

    def test_large_jsonl_member_is_scrubbed_record_by_record(self):
        from phase36_receipts import sanitize

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token = "b" * 32
            record = (
                json.dumps(
                    {"cookie": "secret-cookie", "action": token, "padding": "x" * 1024}
                )
                + "\n"
            )
            trace = root / "trace.zip"
            with zipfile.ZipFile(
                trace, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.writestr("trace.network", record * 30000)
            sanitize(root, token)
            with zipfile.ZipFile(trace) as archive:
                for line in archive.open("trace.network"):
                    value = json.loads(line)
                    self.assertEqual(value["cookie"], "[redacted]")
                    self.assertNotIn(token, value["action"])

    def test_archive_limits_each_line_member_and_total(self):
        from unittest.mock import patch

        import phase36_receipts as receipts

        for limit in ("TRACE_LINE_BYTES", "TRACE_MEMBER_BYTES", "TRACE_ARCHIVE_BYTES"):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with zipfile.ZipFile(root / "trace.zip", "w") as archive:
                    archive.writestr(
                        "trace.network", json.dumps({"padding": "x" * 128}) + "\n"
                    )
                with patch.object(receipts, limit, 64, create=True):
                    with self.assertRaises(RuntimeError):
                        receipts.sanitize(root, "b" * 32)

    def test_archive_rejects_unsafe_member_paths_and_links(self):
        from phase36_receipts import sanitize

        for name, link in (
            ("../trace.network", False),
            ("/trace.network", False),
            ("trace.network", True),
        ):
            with self.subTest(
                name=name, link=link
            ), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with zipfile.ZipFile(root / "trace.zip", "w") as archive:
                    info = zipfile.ZipInfo(name)
                    if link:
                        info.create_system = 3
                        info.external_attr = 0o120777 << 16
                    archive.writestr(info, "{}")
                with self.assertRaises(RuntimeError):
                    sanitize(root, "b" * 32)


class ProviderObservationContracts(unittest.TestCase):
    def response(
        self, markup=False, endpoint="/api/appdetails?appids=1245620&l=german"
    ):
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
                    data = urllib.request.urlopen(url + endpoint, timeout=5).read()
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

    def test_ss_name_search_has_canonical_region(self):
        payload, _, _ = self.response(
            endpoint="/api2/jeuRecherche.php?recherche=Control&systemeid=4"
        )
        names = payload["response"]["jeux"][0]["noms"]
        self.assertTrue(
            any(name["region"] == "ss" and name["text"] == "Control" for name in names)
        )

    def test_markup_control_reaches_provider_payload(self):
        payload, _, _ = self.response(markup=True)
        self.assertIn("<img", payload["1245620"]["data"]["short_description"])


class BackendShardContracts(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch

        import phase36_receipts as receipts

        fixture = ArtifactContracts()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        self.evidence = fixture.evidence
        self.entry = fixture.entry
        self.files = [f"tests/test_shard{index}.py" for index in range(1, 9)]
        self.addCleanup(patch.stopall)
        patch("ci_target.tracked_test_files", return_value=self.files).start()
        self.payload: dict[str, Any] = {
            "phase": 36,
            "kind": "backend",
            "dialect": "mariadb",
            "passed": True,
            "full_suite": True,
            "tests": 800,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "skip_details": [],
            "subtests_passed": 0,
            "junit_tests": 800,
            "shards": [f"shard{index}" for index in range(1, 9)],
        }
        self.entry.update(kind="backend", dialect="mariadb")
        for index, selected in enumerate(self.files, 1):
            folder = self.evidence / f"shard{index}"
            folder.mkdir()
            for name in ("cleanup.json", "code-before.json"):
                (folder / name).write_bytes((self.evidence / name).read_bytes())
            values = {
                "ci-result.json": {
                    "gate": "pytest",
                    "dialect": "mariadb",
                    "passed": True,
                },
                "shard-files.json": {
                    "shard": index,
                    "shards": 8,
                    "all_files": self.files,
                    "selected_files": [selected],
                },
                "commands.json": [
                    {
                        "command": [
                            "uv",
                            "run",
                            "pytest",
                            "--junitxml=/phase34/evidence/backend.xml",
                            selected,
                        ],
                        "exit": 0,
                        "log": "pytest.log",
                    }
                ],
            }
            for name, value in values.items():
                (folder / name).write_text(json.dumps(value))
            (folder / "pytest.log").write_text("=== 100 passed in 0.01s ===\n")
            cases = "".join(
                f'<testcase classname="tests.test_shard{index}" name="test_{case}"/>'
                for case in range(100)
            )
            (folder / "backend.xml").write_text(
                '<testsuites><testsuite tests="100" failures="0" errors="0" skipped="0">'
                + cases
                + "</testsuite></testsuites>"
            )
        self.write_payload()
        self.receipts = receipts

    def write_payload(self):
        from phase36_receipts import digest

        (self.evidence / "result.json").write_text(json.dumps(self.payload))
        self.entry["artifacts"] = {
            path.relative_to(self.evidence).as_posix(): digest(path)
            for path in self.evidence.rglob("*")
            if path.is_file()
        }

    def validate(self):
        return self.receipts.validate_entry(self.entry, self.root, None)

    def test_complete_real_xml_union_passes(self):
        self.assertEqual(self.validate(), ("backend", "mariadb"))

    def add_subtests(self, reported=1):
        target = self.evidence / "shard1/backend.xml"
        target.write_text(target.read_text().replace('tests="100"', 'tests="101"'))
        (self.evidence / "shard1/pytest.log").write_text(
            f"=== 100 passed, {reported} subtests passed in 0.01s ===\n"
        )
        self.payload["subtests_passed"] = 1
        self.payload["junit_tests"] = 801
        self.write_payload()

    def test_accepts_actual_junit_passed_subtest_shape(self):
        self.add_subtests()
        self.assertEqual(self.validate(), ("backend", "mariadb"))

    def test_rejects_unexplained_subtest_delta(self):
        self.add_subtests(reported=2)
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_forged_base_summary(self):
        self.add_subtests()
        (self.evidence / "shard1/pytest.log").write_text(
            "=== 99 passed, 1 subtests passed in 0.01s ===\n"
        )
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_failed_subtest_in_terminal(self):
        self.add_subtests()
        (self.evidence / "shard1/pytest.log").write_text(
            "=== 100 passed, 1 subtests failed in 0.01s ===\n"
        )
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_summary_counts_without_all_shards(self):
        self.payload["shards"].pop()
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_duplicate_shard(self):
        self.payload["shards"][-1] = "shard1"
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_fabricated_xml_counts(self):
        target = self.evidence / "shard1/backend.xml"
        target.write_text(target.read_text().replace('tests="100"', 'tests="101"'))
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_xml_failure_even_when_summary_is_green(self):
        target = self.evidence / "shard1/backend.xml"
        target.write_text(
            target.read_text().replace(
                'name="test_0"/>',
                'name="test_0"><failure>actual failure</failure></testcase>',
            )
        )
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_wrong_selected_union(self):
        target = self.evidence / "shard8/shard-files.json"
        row = json.loads(target.read_text())
        row["selected_files"] = [self.files[0]]
        target.write_text(json.dumps(row))
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_unexecuted_selection(self):
        target = self.evidence / "shard1/commands.json"
        target.write_text(json.dumps([{"command": ["uv", "run", "pytest"], "exit": 0}]))
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_partial_shard_cleanup(self):
        target = self.evidence / "shard1/cleanup.json"
        row = json.loads(target.read_text())
        row["snapshot_removed"] = False
        target.write_text(json.dumps(row))
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_wrong_shard_dialect(self):
        target = self.evidence / "shard1/ci-result.json"
        row = json.loads(target.read_text())
        row["dialect"] = "postgresql"
        target.write_text(json.dumps(row))
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_rejects_xml_from_unselected_module(self):
        target = self.evidence / "shard1/backend.xml"
        target.write_text(
            target.read_text().replace("tests.test_shard1", "tests.test_foreign")
        )
        self.write_payload()
        with self.assertRaises(RuntimeError):
            self.validate()


class RootSkipEvidenceContracts(unittest.TestCase):
    def test_requires_indexed_inspection_and_default_exec_user(self):
        from phase36_quality import ROOT_ENVIRONMENT, root_skip_environment

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            path = folder / "inspect.json"

            def inspection(user):
                path.write_text(
                    json.dumps([{"Name": "/owned-runner-1", "Config": {"User": user}}])
                )

            inspection("")
            commands: list[dict[str, Any]] = [
                {
                    "command": [
                        "docker",
                        "exec",
                        "owned-runner",
                        "uv",
                        "run",
                        "pytest",
                    ],
                    "log": "pytest.log",
                },
                {
                    "command": ["docker", "container", "inspect", "owned-runner"],
                    "log": "inspect.json",
                },
            ]
            artifacts = {"shard/inspect.json": "a" * 64}
            self.assertEqual(
                root_skip_environment(commands, folder, artifacts, "shard"),
                ROOT_ENVIRONMENT,
            )
            with self.assertRaises(RuntimeError):
                root_skip_environment(commands, folder, {}, "shard")
            inspection("1000")
            with self.assertRaises(RuntimeError):
                root_skip_environment(commands, folder, artifacts, "shard")
            inspection("")
            commands[0]["command"].insert(2, "--user=0")
            with self.assertRaises(RuntimeError):
                root_skip_environment(commands, folder, artifacts, "shard")


class ShardSourceDeltaContracts(unittest.TestCase):
    def test_only_reviewed_unexecuted_gate_files_can_differ(self):
        from phase36_quality import shard_source_delta

        name = "backend/tools/phase36_quality.py"
        before, after = {"files": {name: "a" * 64}}, {"files": {name: "b" * 64}}
        selected = [
            "tools/tests/test_phase33_uat.py",
            "tools/tests/test_phase35_incremental_scan_probe.py",
        ]
        delta = [
            {
                "file": name,
                "tested": "a" * 64,
                "current": "b" * 64,
                "reason": "evidence_gate_only_outside_reviewed_shard_imports",
            }
        ]
        shard_source_delta(before, after, 1, selected, delta)
        for number, files, record in (
            (2, selected, delta),
            (1, selected + ["tools/tests/test_phase36_receipts.py"], delta),
            (1, selected, []),
        ):
            with self.subTest(
                number=number, selected=files, record=record
            ), self.assertRaises(RuntimeError):
                shard_source_delta(before, after, number, files, record)

    def test_reviewed_non_receipt_groups_allow_only_evidence_gate_deltas(self):
        from phase36_quality import shard_source_delta

        name = "backend/tools/phase36_quality.py"
        before, after = {"files": {name: "a" * 64}}, {"files": {name: "b" * 64}}
        delta = [
            {
                "file": name,
                "tested": "a" * 64,
                "current": "b" * 64,
                "reason": "evidence_gate_only_outside_reviewed_shard_imports",
            }
        ]
        reviewed = {
            4: "tools/tests/test_phase34_portainer.py",
            5: "tools/tests/test_phase34_runner.py",
            6: "tools/tests/test_phase34_target_guard.py",
            7: "tools/tests/test_phase35_acceptance_invariants.py",
        }
        for number, selected in reviewed.items():
            with self.subTest(number=number):
                shard_source_delta(before, after, number, [selected], delta)
                with self.assertRaises(RuntimeError):
                    shard_source_delta(
                        before,
                        after,
                        number,
                        [selected, "tools/tests/test_phase36_receipts.py"],
                        delta,
                    )
        with self.assertRaises(RuntimeError):
            shard_source_delta(
                before, after, 3, ["tools/tests/test_phase36_receipts.py"], delta
            )

    def test_unselected_fixture_delta_is_limited_to_reviewed_seed_groups(self):
        from phase36_quality import shard_source_delta

        name = "backend/tests/endpoints/test_storage_policy_denials.py"
        before, after = {"files": {name: "a" * 64}}, {"files": {name: "b" * 64}}
        selected = [
            "tools/tests/test_phase33_uat.py",
            "tools/tests/test_phase35_incremental_scan_probe.py",
        ]
        delta = [
            {
                "file": name,
                "tested": "a" * 64,
                "current": "b" * 64,
                "reason": "unselected_unimported_storage_policy_fixture_alignment",
            }
        ]
        shard_source_delta(before, after, 1, selected, delta)
        for number, files in (
            (3, selected),
            (1, selected + [name.removeprefix("backend/")]),
        ):
            with self.subTest(number=number, selected=files), self.assertRaises(
                RuntimeError
            ):
                shard_source_delta(before, after, number, files, delta)
        with self.assertRaises(RuntimeError):
            shard_source_delta(before, after, 1, selected, [])

    def test_product_delta_cannot_claim_gate_only_exemption(self):
        from phase36_quality import shard_source_delta

        name = "backend/handler/scan_description_retry.py"
        before, after = {"files": {name: "a" * 64}}, {"files": {name: "b" * 64}}
        selected = [
            "tools/tests/test_phase33_uat.py",
            "tools/tests/test_phase35_incremental_scan_probe.py",
        ]
        delta = [
            {
                "file": name,
                "tested": "a" * 64,
                "current": "b" * 64,
                "reason": "evidence_gate_only_outside_reviewed_shard_imports",
            }
        ]
        with self.assertRaises(RuntimeError):
            shard_source_delta(before, after, 1, selected, delta)


if __name__ == "__main__":
    unittest.main()


class CIInventoryContracts(unittest.TestCase):
    def test_rejects_mis_scoped_backend_before_host_inventory(self):
        from unittest.mock import patch

        from phase36_receipts import source_dependencies

        with patch(
            "phase36_quality.ci_source_files",
            side_effect=AssertionError("host inventory must not execute"),
        ):
            with self.assertRaises(RuntimeError):
                source_dependencies(
                    {"kind": "backend", "dependencies": {"scenario": "security"}},
                    {"files": {"backend/product.py": "a" * 64}},
                    {"files": {"backend/product.py": "a" * 64}},
                )

    def test_backend_binds_independent_tracked_inventory(self):
        from unittest.mock import patch

        from phase36_receipts import dependency_files, source_dependencies

        tracked = {
            "backend/product.py": "a" * 64,
            "tests/fixtures/support.bin": "b" * 64,
        }
        current = {
            "files": {
                "backend/product.py": "a" * 64,
                "backend/.hypothesis/cache": "c" * 64,
            }
        }
        delta = [
            {
                "file": "backend/.hypothesis/cache",
                "tested": None,
                "current": "c" * 64,
                "reason": "outside_scenario",
            },
            {
                "file": "tests/fixtures/support.bin",
                "tested": "b" * 64,
                "current": None,
                "reason": "ci_tracked_support",
            },
        ]
        entry = {
            "kind": "backend",
            "dependencies": {
                "scenario": "backend",
                "files": tracked,
                "snapshot_delta": delta,
            },
        }
        with patch(
            "phase36_quality.ci_source_files", return_value=tracked, create=True
        ):
            self.assertEqual(dependency_files("backend", current), tracked)
            source_dependencies(entry, {"files": tracked}, current)
            for tested in (
                {
                    "files": {
                        "backend/product.py": "d" * 64,
                        "tests/fixtures/support.bin": "b" * 64,
                    }
                },
                {"files": {"backend/product.py": "a" * 64}},
                {"files": {**tracked, "backend/untracked.py": "e" * 64}},
            ):
                with self.subTest(tested=tested), self.assertRaises(RuntimeError):
                    source_dependencies(entry, tested, current)

    def test_third_reviewed_helper_delta_is_exact(self):
        from phase36_quality import shard_source_delta

        name = "backend/tools/phase36_receipts.py"
        selected = ["tools/tests/test_phase34_runner.py"]
        before, after = {"files": {name: "a" * 64}}, {"files": {name: "b" * 64}}
        delta = [
            {
                "file": name,
                "tested": "a" * 64,
                "current": "b" * 64,
                "reason": "evidence_gate_only_outside_reviewed_shard_imports",
            }
        ]
        shard_source_delta(before, after, 5, selected, delta)
        shard_source_delta(
            before,
            after,
            8,
            ["tools/tests/test_ci_target.py", "tools/tests/test_phase35_contracts.py"],
            delta,
        )
        for number, files, record in (
            (3, selected, delta),
            (5, selected + ["tools/tests/test_phase36_receipts.py"], delta),
            (5, selected, []),
        ):
            with self.subTest(number=number, files=files), self.assertRaises(
                RuntimeError
            ):
                shard_source_delta(before, after, number, files, record)


class EquivalentAdapterImportContracts(unittest.TestCase):
    def test_only_exact_reviewed_nonexecuted_import_transition_is_allowed(self):
        from phase36_quality import shard_source_delta

        name = "frontend/src/v2/composables/useSystemLanguage/index.ts"
        old = "08bff5c812bf708c61be3543db5af6d2aea02f5c943d1b062564f6568b081ef5"
        new = "fb30a9488a5dec6c817d623b0ebaee705c096eaa33a5af69824f37e5c994ab2e"
        selected = ["tools/tests/test_phase34_runner.py"]
        delta = [
            {
                "file": name,
                "tested": old,
                "current": new,
                "reason": "equivalent_existing_v2_config_adapter_import",
            }
        ]
        shard_source_delta(
            {"files": {name: old}}, {"files": {name: new}}, 5, selected, delta
        )
        for number, before, after, files, record in (
            (3, old, new, selected, delta),
            (5, "a" * 64, new, selected, delta),
            (5, old, "b" * 64, selected, delta),
            (5, old, new, selected, []),
            (5, old, new, selected + ["tools/tests/test_phase36_receipts.py"], delta),
        ):
            with self.subTest(
                number=number, before=before, after=after
            ), self.assertRaises(RuntimeError):
                shard_source_delta(
                    {"files": {name: before}},
                    {"files": {name: after}},
                    number,
                    files,
                    record,
                )


class QualityCommandContracts(unittest.TestCase):
    def test_actual_seven_command_owner_shape_requires_full_vitest(self):
        from phase34_fixtures import frontend_command
        from phase36_receipts import quality

        commands = [
            ["npm", "run", name]
            for name in ("generate", "typecheck", "build", "v2:maintainability")
        ]
        commands += [frontend_command([])]
        commands += [
            ["python3", "src/locales/" + name]
            for name in ("check_i18n_locales.py", "check_i18n_sorted.py")
        ]
        payload = {"checks": [{"command": command, "exit": 0} for command in commands]}
        quality(payload)
        for changed in (["npm", "run", "test"], frontend_command(["src/only.test.ts"])):
            invalid = {
                "checks": [
                    {
                        **row,
                        "command": (
                            changed
                            if row["command"] == frontend_command([])
                            else row["command"]
                        ),
                    }
                    for row in payload["checks"]
                ]
            }
            with self.subTest(command=changed), self.assertRaises(RuntimeError):
                quality(invalid)
