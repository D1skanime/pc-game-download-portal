"""Current naming and fresh-install evidence contracts using tracked source only."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "docs/zockarchive-branding-contract.md"


class VerifierTests(unittest.TestCase):
    def test_contract_and_phase_owned_evidence(self):
        contract = (ROOT / CONTRACT).read_text()
        self.assertIn("ZockArchive", contract)
        self.assertIn("Retained compatibility", contract)
        naming = (ROOT / "scripts/verify-pgdp-naming.sh").read_text()
        self.assertIn(CONTRACT, naming)
        self.assertNotIn(".planning/", naming)
        fresh = (ROOT / "scripts/verify-pgdp-fresh-stack.sh").read_text()
        self.assertIn(
            "38-zockarchive-product-and-repository-rebranding/evidence/install/", fresh
        )
        self.assertNotIn("32-03-SUMMARY.md", fresh)
        self.assertNotIn("32-NAMING-INVENTORY.md", fresh)
        for retained in (
            "label=com.docker.compose.project=${project}",
            'test "${volume_project}" = "${project}"',
            "down --volumes --remove-orphans",
            "/tmp/pgdp-fresh-proof.*",
        ):
            self.assertIn(retained, fresh)

    def test_portainer_retains_operator_and_persistence_contracts(self):
        source = (ROOT / "scripts/verify-portainer-stack.sh").read_text()
        self.assertIn(CONTRACT, source)
        self.assertNotIn("github.com/D1skanime/pc-game-download-portal.git", source)
        for retained in (
            "pc-game-download-portal:portainer",
            "pgdp-db",
            "DB_NAME: pgdp",
            "DB_USER: pgdp-user",
            "/romm/library",
            "read_only: true",
            "/romm/assets",
            "/romm/config",
            "/romm/resources",
            "/redis-data",
            "/var/lib/mysql",
            "ROMM_AUTH_SECRET_KEY",
            "condition: service_healthy",
            "PGDP_PROJECT_NAME",
        ):
            self.assertIn(retained, source)


class FreshCloneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="za-38-07-clone-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.clone = Path(cls.temporary.name) / "source"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-local",
                "--depth",
                "1",
                ROOT.as_uri(),
                str(cls.clone),
            ],
            check=True,
            capture_output=True,
        )
        shutil.rmtree(cls.clone / ".planning", ignore_errors=True)

    def run_gate(self, script="verify-pgdp-naming.sh"):
        return subprocess.run(
            ["bash", "scripts/" + script],
            cwd=self.clone,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_fresh_committed_clone_passes_without_planning(self):
        self.assertFalse((self.clone / ".planning").exists())
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_gate("verify-portainer-stack.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wrong_visible_brand_and_source_url_fail(self):
        for name, old, new in (
            ("frontend/index.html", "ZockArchive", "PGDP"),
            ("frontend/public/site.webmanifest", "ZockArchive", "RomM"),
            ("frontend/public/site.webmanifest", '"ZA"', '"PGDP"'),
            ("README.md", "D1skanime/zockarchive", "foreign/zockarchive"),
            ("README.md", "# ZockArchive", "# RomM"),
        ):
            path = self.clone / name
            original = path.read_text()
            self.assertIn(old, original)
            try:
                path.write_text(original.replace(old, new))
                result = self.run_gate()
                self.assertNotEqual(result.returncode, 0, name)
            finally:
                path.write_text(original)

    def test_unclassified_brand_and_missing_contract_fail(self):
        path = self.clone / "README.md"
        original = path.read_text()
        try:
            path.write_text(original + "\nPGDP is the product name.\n")
            self.assertNotEqual(self.run_gate().returncode, 0)
        finally:
            path.write_text(original)
        contract = self.clone / CONTRACT
        if contract.exists():
            original = contract.read_text()
            try:
                contract.unlink()
                self.assertNotEqual(self.run_gate().returncode, 0)
            finally:
                contract.write_text(original)

    def test_required_portainer_inputs_fail_before_provisioning(self):
        source = (self.clone / "examples/portainer.env.example").read_text()
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("PGDP_")
        }
        for key in (
            "PGDP_DB_PASSWORD",
            "PGDP_DB_ROOT_PASSWORD",
            "PGDP_AUTH_SECRET_KEY",
            "PGDP_LIBRARY_PATH",
            "PGDP_ASSETS_PATH",
            "PGDP_CONFIG_PATH",
        ):
            with self.subTest(key=key):
                env_file = Path(self.temporary.name) / (key + ".env")
                env_file.write_text(
                    "\n".join(
                        line
                        for line in source.splitlines()
                        if not line.startswith(key + "=")
                    )
                )
                result = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "--env-file",
                        str(env_file),
                        "-f",
                        "examples/portainer-stack.yml",
                        "config",
                        "--quiet",
                    ],
                    cwd=self.clone,
                    env=environment,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key.encode(), result.stderr)
