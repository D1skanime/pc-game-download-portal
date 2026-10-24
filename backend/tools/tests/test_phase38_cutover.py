"""Read-only repository rename continuity and acceptance contracts."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import phase38_cutover as cutover
import phase38_cutover_source as source_module
import phase38_cutover_validation as validation
from phase38_cutover_source import manifest, source_proof

SHA = "a" * 40


def snapshot(name):
    url = "https://github.com/D1skanime/" + name
    return {
        "schema": 1,
        "repository": {
            "id": 1415481891,
            "node_id": "R_kgDOVF6KIw",
            "owner": "D1skanime",
            "name": name,
            "default_branch": "main",
            "visibility": "public",
            "description": "PC Game Download Portal",
            "homepage": None,
        },
        "origins": {"fetch": url + ".git", "push": url + ".git"},
        "refs": [
            ["refs/heads/main", SHA],
            ["refs/tags/v1", "b" * 40],
            ["refs/tags/v1^{}", SHA],
        ],
        "releases": [
            {
                "id": 10,
                "node_id": "release",
                "tag_name": "v1",
                "name": "Original",
                "body": "Keep https://github.com/D1skanime/pc-game-download-portal",
                "draft": False,
                "prerelease": False,
                "target_commitish": "main",
                "html_url": url + "/releases/tag/v1",
                "assets": [
                    {
                        "id": 11,
                        "node_id": "asset",
                        "name": "app.zip",
                        "size": 42,
                        "digest": "sha256:" + "c" * 64,
                        "browser_download_url": url + "/releases/download/v1/app.zip",
                    }
                ],
            }
        ],
        "issues": [
            {
                "id": 12,
                "node_id": "issue",
                "number": 1,
                "title": "Old name",
                "body": "PC Game Download Portal",
                "html_url": url + "/issues/1",
            }
        ],
        "pull_requests": [],
        "metadata_edits": {},
    }


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.before = snapshot("pc-game-download-portal")
        self.after = snapshot("zockarchive")
        self.backup = patch.object(cutover, "verify_backup")
        self.backup.start()
        self.addCleanup(self.backup.stop)

    def test_same_id_and_url_rewrite_only_pass(self):
        cutover.continuity(self.before, self.after)

    def test_explicit_about_edit(self):
        self.after["repository"]["description"] = "ZockArchive PC and console library"
        self.after["metadata_edits"] = {
            "description": [
                "PC Game Download Portal",
                "ZockArchive PC and console library",
            ]
        }
        cutover.continuity(self.before, self.after)

    def test_id_refs_metadata_and_history_mutations_fail(self):
        cases = []
        for key, value in (
            ("id", 123),
            ("node_id", "foreign"),
            ("owner", "foreign"),
            ("visibility", "private"),
            ("default_branch", "master"),
        ):
            changed = copy.deepcopy(self.after)
            changed["repository"][key] = value
            cases.append(changed)
        for field in ("refs", "releases", "issues", "pull_requests"):
            changed = copy.deepcopy(self.after)
            del changed[field]
            cases.append(changed)
        for refs in (
            self.after["refs"][:-1],
            self.after["refs"] + [["refs/heads/new", SHA]],
            self.after["refs"][::-1],
            self.after["refs"] * 2,
        ):
            changed = copy.deepcopy(self.after)
            changed["refs"] = refs
            cases.append(changed)
        for field in ("body", "name", "tag_name"):
            changed = copy.deepcopy(self.after)
            changed["releases"][0][field] = "changed"
            cases.append(changed)
        for field in ("id", "name", "size", "digest"):
            changed = copy.deepcopy(self.after)
            changed["releases"][0]["assets"][0][field] = "changed"
            cases.append(changed)
        changed = copy.deepcopy(self.after)
        changed["issues"][0]["body"] = "ZockArchive"
        cases.append(changed)
        changed = copy.deepcopy(self.after)
        changed["origins"]["push"] = "https://github.com/foreign/repo.git"
        cases.append(changed)
        changed = copy.deepcopy(self.after)
        changed["repository"]["description"] = "unrecorded"
        cases.append(changed)
        for changed in cases:
            with self.subTest(changed=changed):
                with self.assertRaises((ValueError, RuntimeError)):
                    cutover.continuity(self.before, changed)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="za-38-09-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "canonical"
        self.root.mkdir()
        self.backups = Path(self.temp.name) / "backups"
        self.backups.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.root / "source").write_text("runtime")
        self.git("add", "source")
        self.git("commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD").strip()
        self.git("tag", "-a", "v1", "-m", "annotated")
        self.git("branch", "unpublished")
        self.bundle = self.backups / "local.bundle"
        self.git("bundle", "create", str(self.bundle), "--all")
        refs = cutover.parse_refs(self.git("bundle", "list-heads", str(self.bundle)))
        self.row = {
            "path": str(self.bundle),
            "sha256": hashlib.sha256(self.bundle.read_bytes()).hexdigest(),
            "refs": refs,
        }
        self.patches = [
            patch.object(cutover, "ROOT", self.root),
            patch.object(cutover, "BACKUP_ROOT", self.backups),
        ]
        for mocked in self.patches:
            mocked.start()
            self.addCleanup(mocked.stop)

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL
        )

    def test_real_bundle_hash_refs_and_unpublished_source(self):
        cutover.verify_bundle(self.row, self.sha)

    def test_missing_foreign_tampered_and_unreachable_backups_fail(self):
        for key, value in (
            ("path", "/etc/passwd"),
            ("path", str(self.backups / "missing")),
            ("sha256", "0" * 64),
            ("refs", []),
        ):
            changed = copy.deepcopy(self.row)
            changed[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises((ValueError, RuntimeError)):
                    cutover.verify_bundle(changed, self.sha)
        with self.assertRaises((ValueError, RuntimeError)):
            cutover.verify_bundle(self.row, "f" * 40)

    def test_complete_local_and_remote_backups(self):
        mirror = self.backups / "remote.git"
        self.git("clone", "--mirror", str(self.root), str(mirror))
        advertised = cutover.parse_refs(self.git("show-ref", "--dereference"))
        remote_refs = [r for r in advertised if not r[0].endswith("^{}")]
        remote_bundle = self.backups / "remote.bundle"
        self.git(
            "--git-dir=" + str(mirror),
            "bundle",
            "create",
            str(remote_bundle),
            *[r[0] for r in remote_refs],
        )
        remote_head = self.sha
        self.git("branch", "-m", "unpublished-feature")
        (self.root / "source").write_text("unpublished feature source")
        self.git("add", "source")
        self.git("commit", "-qm", "unpublished feature")
        self.sha = self.git("rev-parse", "HEAD").strip()
        local_final = self.backups / "local-final.bundle"
        self.git("bundle", "create", str(local_final), "--all")
        self.row = {
            "path": str(local_final),
            "sha256": hashlib.sha256(local_final.read_bytes()).hexdigest(),
            "refs": cutover.parse_refs(
                self.git("bundle", "list-heads", str(local_final))
            ),
        }
        before = {
            "repository_head": remote_head,
            "refs": advertised,
            "local_refs": self.row["refs"],
            "backup": {
                "source": self.sha,
                "local": self.row,
                "local_refs": self.row["refs"],
                "mirror": str(mirror),
                "remote": {
                    "path": str(remote_bundle),
                    "refs": remote_refs,
                    "sha256": hashlib.sha256(remote_bundle.read_bytes()).hexdigest(),
                },
            },
        }
        cutover.verify_backup(before)
        before["backup"]["local_refs"] = before["backup"]["local_refs"][:-1]
        with self.assertRaises(ValueError):
            cutover.verify_backup(before)

    def test_symlink_escape_rejected(self):
        link = self.backups / "escape.bundle"
        link.symlink_to(self.root / "source")
        self.row["path"] = str(link)
        with self.assertRaises(ValueError):
            cutover.verify_bundle(self.row, self.sha)


def proof():
    return {
        "commit": SHA,
        "manifest": {"files": {"backend/app.py": "b" * 40}, "sha256": "c" * 64},
    }


def acceptance():
    source = proof()
    action = {
        "id": 123,
        "head_sha": SHA,
        "repository_id": 1415481891,
        "url": "https://github.com/D1skanime/zockarchive/actions/runs/123",
        "status": "completed",
        "conclusion": "success",
    }
    rows = []
    for dialect in ("mariadb", "postgresql"):
        for shard in range(1, 9):
            rows.append(
                {
                    "dialect": dialect,
                    "shard": shard,
                    "files": [f"tests/test_{shard}.py"],
                    "source": source,
                    "action": action,
                    "tests": 10,
                    "failures": 0,
                    "errors": 0,
                    "skipped": 0,
                    "passed": True,
                }
            )
    return {
        "schema": 1,
        "repository_id": 1415481891,
        "pr_head": SHA,
        "final_source": source,
        "backend": rows,
        "schema_gates": [
            {
                "dialect": d,
                "source": source,
                "passed": True,
                "steps": ["upgrade-head", "downgrade-base", "upgrade-head"],
                "failures": 0,
                "skipped": 0,
            }
            for d in ("mariadb", "mysql", "postgresql")
        ],
        "actions": [action],
        "links": [
            {
                "kind": kind,
                "url": url,
                "status": 200,
                "source": source,
                "final_url": url,
                "classification": "current",
            }
            for kind, url in validation.REQUIRED_LINKS.items()
        ],
        "limitations": {key: "unavailable" for key in validation.LIMITATIONS},
        "later_ref_changes": [],
    }


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.row = acceptance()
        mocked = patch.object(validation, "source_proof", return_value=SHA)
        mocked.start()
        self.addCleanup(mocked.stop)
        mocked = patch.object(
            validation,
            "test_membership",
            return_value=[f"tests/test_{i}.py" for i in range(1, 9)],
        )
        mocked.start()
        self.addCleanup(mocked.stop)

    def test_all_required_gates_pass(self):
        validation.validate(self.row)

    def test_missing_failed_skipped_stale_and_wrong_membership_fail(self):
        changes = [
            lambda r: r["backend"].pop(),
            lambda r: r["backend"].append(copy.deepcopy(r["backend"][0])),
            lambda r: r["backend"][0].update(passed=False),
            lambda r: r["backend"][0].update(skipped=1),
            lambda r: r["backend"][0].update(tests=0),
            lambda r: r["backend"][0].update(files=[]),
            lambda r: r["backend"][0]["action"].update(head_sha="d" * 40),
            lambda r: r["backend"][0]["action"].update(repository_id=9),
            lambda r: r["backend"][0]["action"].update(conclusion="skipped"),
            lambda r: r["schema_gates"].pop(),
            lambda r: r["schema_gates"][0].update(steps=["upgrade-head"]),
            lambda r: r["schema_gates"][0].update(skipped=1),
            lambda r: r.update(actions=[]),
            lambda r: r["links"].pop(),
            lambda r: r["links"][0].update(status=403),
            lambda r: r["links"][0].update(final_url="https://github.com/foreign"),
            lambda r: r.update(limitations={}),
            lambda r: r.update(pr_head="e" * 40),
        ]
        for change in changes:
            row = copy.deepcopy(self.row)
            change(row)
            with self.subTest(change=change):
                with self.assertRaises((ValueError, RuntimeError)):
                    validation.validate(row)


class SourceTests(BackupTests):
    def test_real_manifest_rejects_incomplete_digest_and_equivalent_flag(self):
        mocked = patch.object(source_module, "ROOT", self.root)
        mocked.start()
        self.addCleanup(mocked.stop)
        sha = self.sha
        row = {"commit": sha, "manifest": manifest(sha, "full")}
        source_proof(row, sha, "full")
        for changed in (
            {"commit": sha, "equivalent": True},
            {
                "commit": sha,
                "manifest": {"files": {}, "sha256": row["manifest"]["sha256"]},
            },
            {
                "commit": sha,
                "manifest": {"files": row["manifest"]["files"], "sha256": "0" * 64},
            },
        ):
            with self.assertRaises(ValueError):
                source_proof(changed, sha, "full")

    def test_changed_full_source_rejected_and_schema_coverage_fixed(self):
        mocked = patch.object(source_module, "ROOT", self.root)
        mocked.start()
        self.addCleanup(mocked.stop)
        (self.root / "backend").mkdir()
        (self.root / "backend/app.py").write_text("runtime")
        self.git("add", "backend/app.py")
        self.git("commit", "-qm", "runtime input")
        previous = self.git("rev-parse", "HEAD").strip()
        observed_files = source_module.runtime_manifest(previous)
        receipt = {
            "commit": previous,
            "manifest": manifest(previous, "schema"),
            "observed_inputs": {
                "files": observed_files,
                "sha256": hashlib.sha256(
                    json.dumps(observed_files, sort_keys=True).encode()
                ).hexdigest(),
            },
        }
        (self.root / "source").write_text("helper documentation")
        self.git("add", "source")
        self.git("commit", "-qm", "non schema input")
        current = self.git("rev-parse", "HEAD").strip()
        source_proof(receipt, current, "schema")
        for altered in (
            {"commit": previous, "manifest": receipt["manifest"]},
            {**receipt, "observed_inputs": {"files": {}, "sha256": "0" * 64}},
        ):
            with self.assertRaises(ValueError):
                source_proof(altered, current, "schema")
        with self.assertRaises(ValueError):
            source_proof(
                {"commit": previous, "manifest": manifest(previous, "full")},
                current,
                "full",
            )
        (self.root / "backend/app.py").write_text("changed runtime")
        self.git("add", "backend/app.py")
        self.git("commit", "-qm", "changed runtime")
        with self.assertRaises(ValueError):
            source_proof(receipt, self.git("rev-parse", "HEAD").strip(), "schema")


if __name__ == "__main__":
    unittest.main()
