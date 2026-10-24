"""Fresh-clone and same-owned-volume production image compatibility proof."""

import json
import re
import shutil
import tempfile
from pathlib import Path

import ci_target
from ci_target import CIRun
from phase34_faults import build_browser, owned_volume, remove_image, wait_http
from phase34_portainer import stack_config
from phase35_browser import browser_config
from phase38_authority import PHASE, ROOT, protected

BASE = "251edcc5d493b3166eab61053bb8f6614ffc3d2a"
PREPARE_SNAPSHOT = ci_target.prepare_ci_snapshot


def validate_volume(item, token, name):
    if (
        name != "pgdp34-" + token + "_owned"
        or item.get("Name") != name
        or item.get("Labels", {}).get("org.pgdp.phase34.run") != token
        or item.get("Labels", {}).get("com.docker.compose.project") != "pgdp34-" + token
    ):
        raise RuntimeError("owned volume identity mismatch")
    return name


def capacity():
    import os

    docker_root = Path("/var/lib/docker")
    if shutil.disk_usage(docker_root).free < 10 * 1024**3:
        raise RuntimeError(
            "production proof requires 10 GiB available on Docker filesystem"
        )
    if shutil.disk_usage(tempfile.gettempdir()).free < 2 * 1024**3:
        raise RuntimeError(
            "production proof requires 2 GiB available on temporary filesystem"
        )
    available = next(
        line
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    if int(available.split()[1]) < 4 * 1024**2:
        raise RuntimeError("production proof requires 4 GiB available RAM")
    return os.uname().sysname


def fresh(identity):
    """Invoke the existing clean-worktree verifier from an owned committed clone."""
    work = Path(tempfile.mkdtemp(prefix="za-38-08-fresh-"))
    run = CIRun("mariadb")
    receipt = {"identity": identity, "gate": "install", "passed": False}
    try:
        clone = work / "source"
        run.command(
            [
                "git",
                "clone",
                "--no-local",
                "--branch",
                identity["branch"],
                str(ROOT),
                str(clone),
            ],
            timeout=120,
        )
        if (
            run.command(["git", "rev-parse", "HEAD"], cwd=clone).stdout.strip()
            != identity["source"]
        ):
            raise RuntimeError("fresh clone source mismatch")
        run.command(
            ["bash", "scripts/verify-pgdp-fresh-stack.sh"], cwd=clone, timeout=2400
        )
        summaries = list(
            (
                clone
                / ".planning/phases/38-zockarchive-product-and-repository-rebranding/evidence/install"
            ).glob("*/summary.md")
        )
        if len(summaries) != 1:
            raise RuntimeError("fresh proof summary missing")
        text = summaries[0].read_text()
        match = re.search(r"Disposable Compose project: (pgdp-proof-[0-9-]+)", text)
        digest = re.search(r"Image digest: (sha256:[a-f0-9]{64})", text)
        if (
            not match
            or not digest
            or "Result: 0" not in text
            or "Cleanup: passed" not in text
        ):
            raise RuntimeError("fresh proof incomplete")
        image = "pc-game-download-portal:" + match[1]
        item = run.inspect("image", image)
        if item["Id"] != digest[1]:
            raise RuntimeError("fresh image cleanup identity mismatch")
        run.command(["docker", "image", "rm", image])
        receipt["passed"] = True
        receipt["source_image"] = digest[1]
        (run.evidence / "fresh-summary.md").write_text(text)
    finally:
        for summary in (
            work
            / "source/.planning/phases/38-zockarchive-product-and-repository-rebranding/evidence/install"
        ).glob("*/summary.md"):
            text = summary.read_text()
            (run.evidence / "fresh-summary.md").write_text(text)
            project_match = re.search(
                r"Disposable Compose project: (pgdp-proof-[0-9-]+)", text
            )
            image_match = re.search(r"Image digest: (sha256:[a-f0-9]{64})", text)
            if project_match and image_match:
                tag = "pc-game-download-portal:" + project_match[1]
                inspected = run.command(
                    ["docker", "image", "inspect", tag], check=False
                )
                if inspected.returncode == 0:
                    if json.loads(inspected.stdout)[0]["Id"] != image_match[1]:
                        raise RuntimeError("fresh cleanup image identity mismatch")
                    run.command(["docker", "image", "rm", tag])
        destination = PHASE / "evidence/install" / work.name
        destination.mkdir(parents=True, exist_ok=True)
        if (run.evidence / "fresh-summary.md").exists():
            shutil.copy2(run.evidence / "fresh-summary.md", destination)
        (destination / "result.json").write_text(json.dumps(receipt, indent=2))
        if (
            work.parent == Path(tempfile.gettempdir())
            and work.name.startswith("za-38-08-fresh-")
            and not work.is_symlink()
        ):
            shutil.rmtree(work)
        print("PHASE38_INSTALL_EVIDENCE", destination, flush=True)
    return receipt


def build(run, source, tag):
    image = run.project + ":" + tag
    run.command(
        [
            "docker",
            "build",
            "--file",
            str(source / "docker/Dockerfile"),
            "--target",
            "full-image",
            "--label",
            "org.pgdp.phase34.run=" + run.token,
            "--tag",
            image,
            str(source),
        ],
        timeout=2400,
    )
    return image


def prepare_upgrade(root, repo):
    games, source = PREPARE_SNAPSHOT(root, repo)
    cartridge = bytearray(32768)
    cartridge[0x100:0x103] = bytes([0xC3, 0, 1])
    cartridge[0x134:0x139] = b"OWNED"
    checksum = 0
    for value in cartridge[0x134:0x14D]:
        checksum = (checksum - value - 1) & 255
    cartridge[0x14D] = checksum
    (games / "GB GameBoy/owned.gb").write_bytes(cartridge)
    return games, source


def upgrade(identity):
    run = CIRun("mariadb")
    images = []
    receipt = {"identity": identity, "gate": "upgrade", "passed": False}
    try:
        browser_image = build_browser(run)
        images.append(browser_image)
        run.image = browser_image
        ci_target.prepare_ci_snapshot = prepare_upgrade
        try:
            run.start()
        finally:
            ci_target.prepare_ci_snapshot = PREPARE_SNAPSHOT
        receipt["source_code_sha256"] = json.loads(
            (run.evidence / "code-before.json").read_text()
        )["sha256"]
        volume = owned_volume(run)
        validate_volume(run.inspect("volume", volume), run.token, volume)
        receipt["resources"] = {
            "sql": run.manifest["sql"]["id"],
            "redis": run.manifest["redis"]["id"],
            "owned_volume": volume,
            "sql_storage": "same isolated container tmpfs",
        }
        receipt["images"] = []
        old = run.root / "old-source"
        old.mkdir()
        archive = run.root / "base.tar"
        run.command(["git", "archive", "--output", str(archive), BASE], cwd=ROOT)
        run.command(["tar", "-xf", str(archive), "-C", str(old)])
        archive.unlink()
        for source, tag, action in (
            (old, "base", "seed"),
            (run.root / "checkout", "current", "verify"),
        ):
            image = build(run, source, tag)
            images.append(image)
            receipt["images"].append(
                {
                    "source": BASE if tag == "base" else identity["source"],
                    "tag": tag,
                    "id": run.inspect("image", image)["Id"],
                }
            )
            config = stack_config(run, image)
            for service in config["services"].values():
                service["volumes"].extend(
                    [
                        str(run.control) + ":/phase34/control:ro",
                        str(run.evidence) + ":/phase34/evidence",
                    ]
                )
            config_path = run.control / "upgrade.compose.json"
            config_path.write_text(json.dumps(config))
            config_path.chmod(0o600)
            run.command(
                [
                    "docker",
                    "compose",
                    "--env-file",
                    "/dev/null",
                    "-p",
                    run.project,
                    "-f",
                    str(config_path),
                    "up",
                    "-d",
                    "--no-deps",
                    "api",
                    "worker",
                ],
                timeout=180,
            )
            wait_http(
                run, "http://phase34-production-app:8080/api/heartbeat", seconds=120
            )
            api = run.command(
                [
                    "docker",
                    "compose",
                    "-p",
                    run.project,
                    "-f",
                    str(config_path),
                    "ps",
                    "-q",
                    "api",
                ]
            ).stdout.strip()
            # The data helper runs with the application's exact image and generated environment.
            script = ROOT / "backend/tools/phase38_install_data.py"
            run.command(
                [
                    "docker",
                    "cp",
                    str(script),
                    api + ":/phase34/owned/phase38_install_data.py",
                ]
            )
            run.command(
                [
                    "docker",
                    "exec",
                    "-w",
                    "/backend",
                    api,
                    "python",
                    "/phase34/owned/phase38_install_data.py",
                    action,
                ],
                timeout=120,
            )
            validate_volume(run.inspect("volume", volume), run.token, volume)
        before = json.loads((run.evidence / "upgrade-seed.json").read_text())
        after = json.loads((run.evidence / "upgrade-verify.json").read_text())
        if before != after:
            raise RuntimeError("populated compatibility state changed")
        config = browser_config()
        config["testMatch"] = "zockarchive-player.spec.ts"
        config["use"]["baseURL"] = "http://phase34-production-app:8080"
        config["use"]["trace"] = "off"
        (run.root / "checkout/frontend/playwright.phase38-player.config.ts").write_text(
            "export default " + json.dumps(config) + ";\n"
        )
        run.exec(
            [
                "npx",
                "--no-install",
                "playwright",
                "test",
                "--config",
                "playwright.phase38-player.config.ts",
            ],
            frontend=True,
            timeout=240,
            extra={
                "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
                "PHASE34_BASE_URL": "http://phase34-production-app:8080",
                "PHASE34_TEST_PASSWORD": run.token,
                "PHASE34_TEST_USERNAME": "phase38-admin",
                "PHASE34_EVIDENCE_DIR": "/phase34/evidence",
            },
        )
        receipt["preserved"] = after
        receipt["passed"] = True
    finally:
        for container in run.owned("container"):
            item = run.inspect("container", container)
            if item["Config"]["Labels"].get("com.docker.compose.service") in (
                "api",
                "worker",
            ):
                run.command(["docker", "logs", "--tail", "120", container], check=False)
        try:
            run.close()
            for image in images:
                remove_image(run, image)
        finally:
            old = run.root / "old-source"
            if old.is_dir() and not old.is_symlink() and old.parent == run.root:
                shutil.rmtree(old)
            destination = PHASE / "evidence/upgrade" / run.project
            destination.mkdir(parents=True, exist_ok=True)
            for path in run.evidence.iterdir():
                if path.is_file() and path.name != "code-before.json":
                    shutil.copy2(path, destination / path.name)
            cleanup = run.evidence / "cleanup.json"
            receipt["cleanup"] = (
                json.loads(cleanup.read_text()) if cleanup.exists() else None
            )
            (destination / "result.json").write_text(json.dumps(receipt, indent=2))
            print("PHASE38_UPGRADE_EVIDENCE", destination, flush=True)
    return receipt


def execute(gate, dialect, identity):
    if dialect != "mariadb" or gate not in ("install", "upgrade"):
        raise RuntimeError("installation profiles require MariaDB")
    before = protected()
    capacity()
    result = fresh(identity) if gate == "install" else upgrade(identity)
    if protected() != before:
        raise RuntimeError("protected work changed")
    return result
