"""Current project metadata and stable desktop compatibility contracts."""

import hashlib
import json
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = "https://github.com/D1skanime/zockarchive"
DESCRIPTION = "A self-hosted PC and console game library and download portal"


def read(name):
    return (ROOT / name).read_text()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def frozen(name):
    if name.endswith(".json"):
        value = json.loads(read(name))
        if name.endswith("package-lock.json"):
            value.pop("name")
            value["packages"][""].pop("name")
        else:
            for field in ("name", "description", "homepage", "repository", "bugs"):
                value.pop(field)
    else:
        value = tomllib.loads(read(name))
        if name == "uv.lock":
            root = next(
                p for p in value["package"] if p.get("source") == {"virtual": "."}
            )
            root["name"] = "<project>"
        else:
            for field in ("name", "description", "urls"):
                value["project"].pop(field)
    return digest(value)


class ProductMetadataTests(unittest.TestCase):
    def test_current_package_and_source_metadata(self):
        package = json.loads(read("frontend/package.json"))
        self.assertEqual(package["name"], "zockarchive")
        self.assertTrue(package["private"])
        self.assertEqual(package["description"], DESCRIPTION)
        self.assertEqual(package["homepage"], SOURCE)
        self.assertEqual(
            package["repository"], {"type": "git", "url": "git+" + SOURCE + ".git"}
        )
        self.assertEqual(package["bugs"]["url"], SOURCE + "/issues")
        project = tomllib.loads(read("pyproject.toml"))["project"]
        self.assertEqual(project["name"], "zockarchive")
        self.assertEqual(project["description"], DESCRIPTION)
        self.assertEqual(project["urls"], {"Homepage": SOURCE, "Source": SOURCE})

    def test_root_lock_identity_matches_project(self):
        lock = json.loads(read("frontend/package-lock.json"))
        self.assertEqual(lock["name"], "zockarchive")
        self.assertEqual(lock["packages"][""]["name"], "zockarchive")
        uv = tomllib.loads(read("uv.lock"))
        roots = [p for p in uv["package"] if p.get("source") == {"virtual": "."}]
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["name"], "zockarchive")

    def test_frozen_dependencies_authors_licenses_and_tooling(self):
        # Canonical fingerprints exclude only the explicitly mutable root metadata.
        for name, expected in FROZEN.items():
            with self.subTest(file=name):
                self.assertEqual(frozen(name), expected)

    def test_desktop_display_and_installer_identity_are_separate(self):
        config = json.loads(read("desktop/src-tauri/tauri.conf.json"))
        self.assertEqual(config["productName"], "RomM Desktop")
        self.assertEqual(config["identifier"], "org.romm.desktop")
        self.assertEqual(config["app"]["windows"][0]["title"], "ZockArchive Desktop")
        self.assertIn(
            "<title>ZockArchive Desktop</title>", read("desktop/ui/index.html")
        )
        self.assertIn(
            'class="eyebrow">ZockArchive Desktop</p>', read("desktop/ui/src/app.ts")
        )

    def test_persistent_native_identity_and_security_owners_are_unchanged(self):
        # Byte fingerprints protect IPC, credential, capability and job/part owners.
        for name, expected in NATIVE.items():
            with self.subTest(file=name):
                self.assertEqual(
                    hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected
                )
        self.assertIn(
            'keyring::Entry::new("org.romm.desktop", "device-token")',
            read("desktop/src-tauri/src/auth.rs"),
        )
        self.assertIn(
            'const STORE_NAME: &str = ".romm-jobs.json";',
            read("desktop/crates/romm-download-core/src/job_store.rs"),
        )


FROZEN = {
    "frontend/package.json": "3f18f688721b051f8855ed10dc76e059dcb8fd474100384cd3da400123ec44db",
    "frontend/package-lock.json": "cd9015304c956ccd235b562584e01a9a506a9ba5027d9d525fa3c98d1d20d10a",
    "pyproject.toml": "821db200abf32cc92618c96de6484bce303a1b0ac4f28e9fc0c2272f2aa70e46",
    "uv.lock": "74a773f2aa112a572dac228102087df524efd54a5754c4020cd7f642ae613187",
}
NATIVE = {
    "desktop/src-tauri/Cargo.toml": "9450806c522ed3dbc0c9f0a6abe7da2012469fff64febb074078818f9ed589e4",
    "desktop/Cargo.lock": "10f26d897eb89e38af9c4205fb4acedbdee5b0413dacac7707f08477ced12f5d",
    "desktop/src-tauri/src/auth.rs": "fa7260142446876b55efd82c1d0825a0071dadf7052696da2325a7b54092dc68",
    "desktop/src-tauri/src/main.rs": "6865bb469924a337671cd841b6e8fc0e9f22f9b576568f5638e3af4ed34d875f",
    "desktop/src-tauri/src/commands.rs": "2aaa81f3a7a80fabc17be834d2c5acbaecc2818c8bab54ae4e6771703f2b110a",
    "desktop/src-tauri/capabilities/default.json": "ab44af4ae0d9739d9e7798c846c20821b6e439aaf1483b77acf8bd1b1136fd50",
    "desktop/crates/romm-download-core/src/job_store.rs": "a436358e82e967d5c15ec77c36365ad22ca2e82dfac8c2163be34cd6eacd04ec",
    "desktop/crates/romm-download-core/src/path.rs": "13b72abd788db684f4ad552b8b17f9c6053eb5c27713328600a84b5494f00183",
    "desktop/crates/romm-download-core/src/finalize.rs": "5988c73be259bb2f85fda288a906f1458032073bbe281235888f29f83bcbda28",
}

if __name__ == "__main__":
    unittest.main()
