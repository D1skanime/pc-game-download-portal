#!/usr/bin/env python3
"""Run real isolated SQL/Redis/worker/browser and nginx boundary scenarios."""

import argparse
import json
import re
from subprocess import SubprocessError  # nosec B404, runner exceptions only

from phase34 import REPO, Run, host_preflight
from phase34_evidence import retain_run
from phase34_fixtures import backend_command

INTEGRATION = "tests/integration/test_scan_operation_faults.py"
BROWSER_CONFIG = "playwright.phase34.config.ts"


def build_production(run):
    image = run.project + ":production"
    run.command(
        [
            "docker",
            "build",
            "--file",
            str(run.root / "checkout/docker/Dockerfile"),
            "--target",
            "slim-image",
            "--label",
            "org.pgdp.phase34.run=" + run.token,
            "--tag",
            image,
            str(run.root / "checkout"),
        ],
        timeout=1800,
    )
    return image


def build_browser(run):
    image = run.project + ":browser"
    alias = run.project + ":base"
    existing = run.command(["docker", "image", "ls", "--quiet", alias])
    if existing.stdout.strip():
        raise RuntimeError("generated browser base alias already exists")
    original = run.command(["docker", "image", "inspect", "pgdp-pgdp-dev:latest"])
    base_id = json.loads(original.stdout)[0]["Id"]
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", base_id):
        raise RuntimeError("invalid local browser base image identity")
    run.command(["docker", "image", "tag", base_id, alias])
    try:
        run.command(
            [
                "docker",
                "build",
                "--file",
                str(REPO / "backend/tools/phase34-browser.Dockerfile"),
                "--build-arg",
                "BASE_IMAGE=" + alias,
                "--label",
                "org.pgdp.phase34.run=" + run.token,
                "--tag",
                image,
                str(run.control),
            ],
            timeout=1200,
        )
    finally:
        tagged = run.command(["docker", "image", "inspect", alias])
        if json.loads(tagged.stdout)[0]["Id"] != base_id:
            raise RuntimeError("browser base alias cleanup identity mismatch")
        run.command(["docker", "image", "rm", alias])
    return image


def owned_volume(run):
    item = run.inspect("container", run.runner)
    for mount in item["Mounts"]:
        if mount.get("Destination") == "/phase34/owned":
            name = mount.get("Name")
            if not name:
                raise RuntimeError("missing owned volume identity")
            volume = run.inspect("volume", name)
            if volume.get("Labels", {}).get("org.pgdp.phase34.run") != run.token:
                raise RuntimeError("owned volume label mismatch")
            return name
    raise RuntimeError("no generated owned volume")


def remove_image(run, image):
    info = run.command(["docker", "image", "inspect", image], check=False)
    if info.returncode:
        return
    item = json.loads(info.stdout)[0]
    if item["Config"].get("Labels", {}).get("org.pgdp.phase34.run") != run.token:
        raise RuntimeError("test image cleanup ownership mismatch")
    run.command(["docker", "image", "rm", image])


def start_process(run, name, argv, *, frontend=False, extra=None):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", name):
        raise RuntimeError("invalid process receipt name")
    script = (
        "import os,subprocess\n"
        "from pathlib import Path\n"
        "from tools.phase34_target_guard import validate_target\n"
        "validate_target()\n"
        f"argv={argv!r}\n"
        f"name={name!r}\n"
        "base=Path('/phase34/evidence')\n"
        "with (base/(name+'.log')).open('ab') as output:\n"
        " p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=output,"
        "stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,"
        "cwd='/app/frontend' if name=='vite' else '/app/backend')\n"
        "(base/(name+'.pid')).write_text(str(p.pid))\n"
        "print('started '+name)\n"
    )
    run.exec(
        ["uv", "run", "python", "-c", script],
        frontend=frontend,
        extra=extra,
    )


def wait_http(run, url, *, seconds=30):
    script = (
        "import time,urllib.request\n"
        f"deadline=time.monotonic()+{seconds!r}\n"
        f"url={url!r}\n"
        "while time.monotonic()<deadline:\n"
        " try:\n"
        "  with urllib.request.urlopen(url,timeout=2) as response:\n"
        "   assert response.status==200\n"
        "   print('HTTP ready'); break\n"
        " except (OSError,AssertionError): time.sleep(0.2)\n"
        "else: raise RuntimeError('isolated HTTP readiness deadline')\n"
    )
    run.exec(["uv", "run", "python", "-c", script], timeout=seconds + 5)


def start_application(run):
    run.exec(["uv", "run", "alembic", "upgrade", "head"])
    run.exec(["uv", "run", "python", "startup.py"], timeout=90)
    start_process(
        run,
        "api",
        ["uv", "run", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "3344"],
        extra={"DEV_PORT": "3344", "ENABLE_SCHEDULED_RESCAN": "false"},
    )
    wait_http(run, "http://127.0.0.1:3344/api/heartbeat")
    redis_url = "redis://:" + run.token + "@" + run.env["REDIS_HOST"] + ":6379/0"
    start_process(
        run,
        "worker",
        [
            "uv",
            "run",
            "rq",
            "worker",
            "--path",
            "/app/backend",
            "--worker-class",
            "handler.rq_worker.RomMWorker",
            "--logging_level",
            "INFO",
            "high",
            "default",
            "low",
        ],
        extra={"RQ_REDIS_URL": redis_url},
    )
    # Start Vite directly; npm predev must not rewrite a source snapshot.
    start_process(
        run,
        "vite",
        [
            "/app/frontend/node_modules/.bin/vite",
            "--host",
            "127.0.0.1",
            "--port",
            "3345",
            "--strictPort",
        ],
        extra={"DEV_PORT": "3344", "DEV_HTTPS": "false"},
    )
    wait_http(run, "http://127.0.0.1:3345/")


def browser_cases(run, *, base_url="http://127.0.0.1:3345", production=False):
    command = [
        "npx",
        "--no-install",
        "playwright",
        "test",
        "--config",
        BROWSER_CONFIG,
        "--workers=1",
    ]
    if production:
        command.extend(["e2e/setup-recovery.spec.ts", "e2e/scan-lifecycle.spec.ts"])
    extra = {
        "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
        "PHASE34_BASE_URL": base_url,
        "PHASE34_TEST_PASSWORD": run.token,
        "PHASE34_TEST_USERNAME": "phase34-admin",
        "PHASE34_EVIDENCE_DIR": "/phase34/evidence",
    }
    run.exec(command, frontend=True, extra=extra, timeout=600)


def nginx_boundary(run, image):
    volume = owned_volume(run)
    config = (REPO / "docker/nginx/templates/default.conf.template").read_text()
    for key, value in {
        "DEV_PORT": "5000",
        "ROMM_PORT": "8080",
        "ROMM_BASE_PATH": "/phase34/owned",
        "IPV6_LISTEN": "",
        "NGINX_ACCESS_LOG": "access_log off;",
    }.items():
        config = config.replace(chr(36) + "{" + key + "}", value)
    config_path = run.control / "nginx-default.conf"
    config_path.write_text(config)
    run.exec(
        [
            "uv",
            "run",
            "python",
            "-c",
            "from pathlib import Path; "
            "site=Path('/phase34/owned/assets/romm'); "
            "site.mkdir(parents=True,exist_ok=True); "
            "(site/'resources').symlink_to('/phase34/owned/resources',target_is_directory=True)",
        ]
    )
    start_process(
        run,
        "http-stream",
        backend_command(
            [
                INTEGRATION
                + "::test_real_streaming_capabilities_expose_only_committed_bytes",
                "-q",
            ],
            name="http-stream",
        ),
        extra={"PHASE34_HTTP_BARRIER": "1"},
    )
    run.exec(
        [
            "uv",
            "run",
            "python",
            "-c",
            "from pathlib import Path; import time; "
            "ready=Path('/phase34/evidence/http-stream-ready'); "
            "deadline=time.monotonic()+30\n"
            "while not ready.exists():\n"
            " if time.monotonic()>deadline: raise RuntimeError('stream barrier deadline')\n"
            " time.sleep(0.02)",
        ],
        timeout=35,
    )
    fixture = json.loads((run.evidence / "http-files.json").read_text())
    positive_url = (
        "http://phase34-http:8080/assets/romm/resources/" + fixture["positive"][0]
    )
    name = run.project + "-nginx"
    run.command(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "org.pgdp.phase34.run=" + run.token,
            "--label",
            "com.docker.compose.project=" + run.project,
            "--label",
            "com.docker.compose.service=nginx-proof",
            "--network",
            run.project + "_isolated",
            "--network-alias",
            "phase34-http",
            "--mount",
            "type=volume,source=" + volume + ",target=/var/www/html,readonly",
            "--mount",
            "type=volume,source=" + volume + ",target=/phase34/owned,readonly",
            "--mount",
            "type=bind,source="
            + str(config_path)
            + ",target=/etc/nginx/conf.d/default.conf,readonly",
            "--entrypoint",
            "nginx",
            image,
            "-g",
            "daemon off;",
        ]
    )
    run.command(["docker", "exec", name, "nginx", "-t"])
    effective = run.command(["docker", "exec", name, "nginx", "-T"])
    (run.evidence / "nginx-effective.conf").write_text(effective.stdout)
    wait_http(run, positive_url)
    run.exec(
        ["uv", "run", "python", "/app/backend/tools/phase34_http_probe.py"],
        timeout=60,
    )
    run.exec(
        [
            "uv",
            "run",
            "python",
            "-c",
            "import json,os,signal,time; from pathlib import Path; "
            "fixture=json.loads(Path('/phase34/evidence/http-files.json').read_text()); "
            "pid=fixture['worker_pid']; "
            "environment=Path(f'/proc/{pid}/environ').read_bytes().split(bytes([0])); "
            "assert ('PHASE34_RUN_TOKEN='+os.environ['PHASE34_RUN_TOKEN']).encode() in environment; "
            "os.kill(pid,signal.SIGKILL); deadline=time.monotonic()+5\n"
            "while Path(f'/proc/{pid}').exists():\n"
            " if time.monotonic()>deadline: raise RuntimeError('owned worker exit deadline')\n"
            " time.sleep(0.02)\n"
            "Path('/phase34/evidence/http-worker-exit.json').write_text(json.dumps({'pid':pid,'confirmed_exit':True}))",
        ],
        timeout=10,
    )
    run.exec(
        [
            "uv",
            "run",
            "python",
            "/app/backend/tools/phase34_http_probe.py",
            "--after-crash",
        ],
        timeout=60,
    )
    # Existing retained files remain denied after nginx restarts.
    run.command(["docker", "restart", name])
    wait_http(run, positive_url)
    run.exec(
        [
            "uv",
            "run",
            "python",
            "/app/backend/tools/phase34_http_probe.py",
            "--after-restart",
        ],
        timeout=60,
    )


def close_recorded(run, gate, succeeded, detail=None, image=None):
    try:
        run.close()
        for item in image if isinstance(image, list) else [image]:
            if item is not None:
                remove_image(run, item)
    finally:
        cleanup = run.evidence / "cleanup.json"
        if cleanup.exists():
            retain_run(run, gate, succeeded, detail)


def run_faults():
    run = Run()
    image = None
    succeeded = False
    try:
        run.start()
        run.exec(
            backend_command(
                [INTEGRATION, "tests/integration/test_scan_output_faults.py", "-q"]
            ),
            timeout=300,
        )
        image = build_production(run)
        nginx_boundary(run, image)
        succeeded = True
    finally:
        close_recorded(run, "faults", succeeded, image=image)


def run_browser():
    run = Run()
    image = None
    succeeded = False
    try:
        image = build_browser(run)
        run.image = image
        run.start()
        start_application(run)
        browser_cases(run)
        succeeded = True
    finally:
        close_recorded(run, "browser", succeeded, image=image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["lifecycle"], required=True)
    parser.parse_args()
    host_preflight()
    # Each leg gets its own fresh SQL/Redis/filesystem identity.
    failures = []
    for name, action in (("service faults", run_faults), ("browser", run_browser)):
        try:
            action()
        except (RuntimeError, OSError, SubprocessError) as exc:
            failures.append(name + ": " + str(exc))
    if failures:
        raise RuntimeError("; ".join(failures))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, SubprocessError) as error:
        print("FAILED: " + str(error))
        raise SystemExit(1) from error
