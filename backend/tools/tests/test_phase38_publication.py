"""Release destinations, attribution and fork isolation contracts."""

import json
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = "https://github.com/D1skanime/zockarchive"


def read(name):
    return (ROOT / name).read_text()


def isolated_release(text):
    return not any(
        token in text
        for token in (
            "trigger-docs-and-web",
            "DOCS_PAT",
            "/dispatches",
            "rommapp/",
        )
    )


def source_labels(text, count):
    return text.count("org.opencontainers.image.source=" + SOURCE) == count


def run_comment(text, tags):
    tail = text.split("      - name: Comment PR with image links", 1)[1]
    raw = tail.split("          script: |\n", 1)[1]
    script = "\n".join(line[12:] for line in raw.splitlines() if line.strip())
    harness = """
const context = {repo: {owner: 'fixture', repo: 'zockarchive'}};
const github = {rest: {issues: {updateComment: async (value) => {
  process.stdout.write(JSON.stringify(value));
}}}};
(async () => { SCRIPT })().catch(error => { console.error(error); process.exit(1); });
""".replace("SCRIPT", script).replace(
        "${{ steps.build-comment.outputs.comment-id }}", "17"
    )
    env = {key: value for key, value in os.environ.items() if key in ("PATH", "HOME")}
    env["IMAGE_TAGS"] = tags
    return json.loads(
        subprocess.check_output(["node", "-e", harness], env=env, text=True)
    )


class PublicationTests(unittest.TestCase):
    def test_release_cannot_mutate_upstream(self):
        text = read(".github/workflows/build.yml")
        self.assertTrue(isolated_release(text))
        self.assertNotIn("actions: write", text)

    def test_action_pins_are_exact_and_unchanged(self):
        pins = sorted(
            set(
                re.findall(
                    r"uses: ([^\s]+)",
                    read(".github/workflows/build.yml")
                    + read(".github/workflows/test-build.yml"),
                )
            )
        )
        self.assertEqual(pins, PINS)
        for pin in pins:
            self.assertRegex(pin, r"@[0-9a-f]{40}$")

    def test_release_aliases_remain_full_and_slim(self):
        text = read(".github/workflows/build.yml")
        self.assertEqual(text.count("name=d1skanime/pc-game-download-portal\n"), 2)
        self.assertEqual(
            text.count("name=ghcr.io/d1skanime/pc-game-download-portal\n"), 2
        )
        self.assertIn("suffix=-slim,onlatest=true", text)
        self.assertNotIn("name=d1skanime/zockarchive", text)
        self.assertNotIn("name=ghcr.io/d1skanime/zockarchive", text)

    def test_oci_metadata_describes_product_and_current_source(self):
        for name, count in (("build.yml", 2), ("test-build.yml", 1)):
            text = read(".github/workflows/" + name)
            self.assertTrue(source_labels(text, count), name)
            self.assertEqual(
                text.count('org.opencontainers.image.title="ZockArchive"'), count
            )
            self.assertIn("PC and console", text)
        self.assertIn(
            "labels: ${{ steps.meta.outputs.labels }}",
            read(".github/workflows/test-build.yml"),
        )

    def test_preview_selection_and_alias_contract(self):
        text = read(".github/workflows/test-build.yml")
        for value in (
            "github.event_name != 'workflow_dispatch'",
            "github.event.inputs.registry == 'ghcr'",
            "github.event.inputs.registry == 'dockerhub'",
            "github.event.inputs.registry == 'both'",
            "secrets.DOCKER_NAMESPACE || secrets.DOCKER_USERNAME",
            "ghcr.io/{0}/pc-game-download-portal-testing",
            "name={0}/pc-game-download-portal-testing",
            "IMAGE_TAGS: ${{ steps.meta.outputs.tags }}",
            "if: github.event_name == 'pull_request'",
        ):
            self.assertIn(value, text)

    def test_comment_uses_exact_enabled_registry_outputs(self):
        text = read(".github/workflows/test-build.yml")
        ghcr = "ghcr.io/fixture/pc-game-download-portal-testing:branch-name"
        dockerhub = "docker-fixture/pc-game-download-portal-testing:branch-name"
        for tags in (ghcr, dockerhub, ghcr + "\n" + dockerhub):
            with self.subTest(tags=tags):
                comment = run_comment(text, tags)
                self.assertEqual(comment["comment_id"], 17)
                for image in tags.splitlines():
                    self.assertIn(image, comment["body"])
                for image in {ghcr, dockerhub} - set(tags.splitlines()):
                    self.assertNotIn(image, comment["body"])
                self.assertIn(SOURCE, comment["body"])
                self.assertNotIn("undefined", comment["body"])

    def test_support_ownership_is_truthful(self):
        self.assertIn(
            "ZockArchive version", read(".github/ISSUE_TEMPLATE/bug_report.md")
        )
        self.assertNotIn("open_collective: romm", read(".github/FUNDING.yml"))
        self.assertIn("upstream", read(".github/FUNDING.yml"))
        self.assertIn("Upstream donation", read("README.md"))

    def test_negative_controls_reject_dispatch_and_stale_source(self):
        clean = read(".github/workflows/build.yml")
        for token in ("DOCS_PAT", "/dispatches", "rommapp/docs"):
            self.assertFalse(isolated_release(clean + "\n" + token))
        self.assertFalse(source_labels(clean.replace(SOURCE, SOURCE + "-wrong"), 2))


PINS = [
    "actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955",
    "actions/github-script@f28e40c7f34bde8b3046d885e986cb6290c5673b",
    "docker/build-push-action@263435318d21b8e681c14492fe198d362a7d2c83",
    "docker/login-action@184bdaa0721073962dff0199f1fb9940f07167d1",
    "docker/metadata-action@c1e51972afc2121e065aed6d45c65596fe445f3f",
    "docker/setup-buildx-action@e468171a9de216ec08956ac3ada2f0791b6bd435",
    "docker/setup-qemu-action@29109295f81e9208d7d86ff1c6c12d2833863392",
]
