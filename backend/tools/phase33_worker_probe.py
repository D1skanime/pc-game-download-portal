#!/usr/bin/env python3
"""Fast real-HTTP and RQ worker probe for a fresh mapped SNES fixture."""

import argparse
import json
import os
import shutil
import time
import uuid
from pathlib import Path

import phase34
from phase33_collection_fixture import authority
from phase33_uat import PHASE, prepare
from phase34_faults import start_application


def inside():
    authority()
    import httpx

    from handler.auth.constants import Scope

    with httpx.Client(base_url="http://127.0.0.1:3344", timeout=20) as client:
        response = client.get("/api/heartbeat")
        response.raise_for_status()
        client.headers["x-csrftoken"] = client.cookies["romm_csrftoken"]
        result = client.post(
            "/api/users",
            json={
                "username": "phase33-admin",
                "email": "phase33@example.test",
                "password": os.environ["PHASE34_RUN_TOKEN"],
                "role": "admin",
            },
        )
        result.raise_for_status()
        result = client.post(
            "/api/token",
            data={
                "grant_type": "password",
                "username": "phase33-admin",
                "password": os.environ["PHASE34_RUN_TOKEN"],
                "scope": " ".join(scope.value for scope in Scope),
            },
        )
        result.raise_for_status()
        client.headers["Authorization"] = "Bearer " + result.json()["access_token"]
        result = client.post(
            "/api/setup/folders/assign",
            json={
                "assignments": [
                    {"folder_name": "pc", "platform_slug": "win"},
                    {"folder_name": "My Games", "platform_slug": "snes"},
                ]
            },
        )
        result.raise_for_status()
        if result.json()["ready"] is not True:
            raise RuntimeError("fresh mapped fixture is not ready")
        result = client.get("/api/platforms")
        result.raise_for_status()
        snes = next(
            platform for platform in result.json() if platform["slug"] == "snes"
        )
        result = client.post(
            "/api/scan-operations",
            json={
                "request_key": str(uuid.uuid4()),
                "platforms": [snes["id"]],
                "apis": [],
                "type": "quick",
            },
        )
        result.raise_for_status()
        operation_id = result.json()["id"]
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            response = client.get("/api/scan-operations/" + operation_id)
            response.raise_for_status()
            snapshot = response.json()
            if snapshot["state"] in {"completed", "failed", "cancelled", "interrupted"}:
                Path("/phase34/evidence/worker-probe.json").write_text(
                    json.dumps(snapshot, indent=2)
                )
                print("REAL_WORKER_PROBE", snapshot["state"], snapshot["scan_stats"])
                if snapshot["state"] != "completed":
                    raise RuntimeError(
                        "real worker failed: " + str(snapshot.get("cause_code"))
                    )
                return
            time.sleep(0.2)
        raise RuntimeError("real worker probe completion deadline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    if args.inside:
        inside()
        return
    phase34.host_preflight()
    phase34.prepare = prepare
    phase34.COMPOSE = PHASE / "33-uat-compose.yml"
    run = phase34.Run()
    run.env["P33_GAMES"] = str(run.root / "fixture/Games")
    error = None
    try:
        run.start()
        if run.manifest is None:
            raise RuntimeError("verified target manifest is missing")
        sql = run.manifest["sql"]["id"]
        run.command(
            [
                "docker",
                "exec",
                "-e",
                "MYSQL_PWD=" + run.token,
                sql,
                "mariadb",
                "-uroot",
                "-e",
                "SET GLOBAL innodb_lock_wait_timeout=3",
            ]
        )
        start_application(run)
        run.exec(
            ["uv", "run", "python", "tools/phase33_worker_probe.py", "--inside"],
            timeout=150,
        )
    except BaseException as exc:
        error = exc
    finally:
        run.close()
        destination = PHASE / "evidence" / ("worker-" + run.project)
        shutil.copytree(run.evidence, destination)
        print("WORKER_PROBE_EVIDENCE", destination, flush=True)
    if error:
        raise error


if __name__ == "__main__":
    main()
