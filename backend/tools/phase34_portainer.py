#!/usr/bin/env python3
"""Production-image fresh-install proof on an explicitly configured Portainer."""

import argparse
import http.client
import json
import os
import urllib.parse
from subprocess import SubprocessError  # nosec B404, runner exceptions only

from phase34 import Run, host_preflight
from phase34_faults import (
    browser_cases,
    build_browser,
    build_production,
    close_recorded,
    nginx_boundary,
    owned_volume,
    wait_http,
)

MAX_RESPONSE = 4 * 1024 * 1024


class Portainer:
    def __init__(self):
        self.url = os.environ.get("PHASE34_PORTAINER_URL", "").rstrip("/")
        self.key = os.environ.get("PHASE34_PORTAINER_API_KEY", "")
        identity = os.environ.get("PHASE34_PORTAINER_ENDPOINT_ID", "")
        parsed = urllib.parse.urlsplit(self.url)
        local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if (
            not self.key
            or not identity.isdecimal()
            or int(identity) < 1
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (parsed.scheme != "https" and not (parsed.scheme == "http" and local))
        ):
            raise RuntimeError(
                "explicit approved PHASE34_PORTAINER_URL/API_KEY/ENDPOINT_ID required; "
                "no endpoint or credential discovery is permitted"
            )
        self.endpoint = int(identity)

    def call(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        target = urllib.parse.urlsplit(self.url)
        connection_type = (
            http.client.HTTPSConnection
            if target.scheme == "https"
            else http.client.HTTPConnection
        )
        if target.hostname is None:
            raise RuntimeError("Portainer hostname missing")
        connection = connection_type(target.hostname, target.port, timeout=15)
        try:
            connection.request(
                method,
                target.path.rstrip("/") + path,
                body=body,
                headers={"X-API-Key": self.key, "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                raise RuntimeError("Portainer HTTP status " + str(response.status))
            data = response.read(MAX_RESPONSE + 1)
        finally:
            connection.close()
        if len(data) > MAX_RESPONSE:
            raise RuntimeError("oversized Portainer response")
        return json.loads(data) if data else None

    def verify_engine(self, run):
        remote = self.call("GET", f"/api/endpoints/{self.endpoint}/docker/info")
        local = run.command(["docker", "info", "--format", "{{.ID}}"]).stdout.strip()
        if not local or remote.get("ID") != local:
            raise RuntimeError(
                "Portainer Docker engine differs from guarded local engine"
            )

    def create(self, name, content):
        result = self.call(
            "POST",
            f"/api/stacks/create/standalone/string?endpointId={self.endpoint}",
            {"Name": name, "StackFileContent": content, "Env": []},
        )
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("Id"), int)
            or result.get("Name") != name
            or result.get("EndpointId") != self.endpoint
        ):
            raise RuntimeError("unconfirmed Portainer stack creation")
        return result["Id"]

    def delete(self, identity, name):
        row = self.call("GET", "/api/stacks/" + str(identity))
        if row.get("Name") != name or row.get("EndpointId") != self.endpoint:
            raise RuntimeError("Portainer stack cleanup identity mismatch")
        self.call(
            "DELETE",
            f"/api/stacks/{identity}?endpointId={self.endpoint}&external=false",
        )


def stack_config(run, image):
    volume = owned_volume(run)
    environment = {
        **run.env,
        "ROMM_AUTH_SECRET_KEY": run.token,
        "DEV_MODE": "false",
        "ROMM_PORT": "8080",
        "DEV_PORT": "5000",
        "IPV4_ONLY": "true",
        "PYTHONDONTWRITEBYTECODE": "1",
        "ENABLE_SCHEDULED_RESCAN": "false",
        "ENABLE_RESCAN_ON_FILESYSTEM_CHANGE": "false",
    }
    environment.update({key: str() for key in ("IGDB_CLIENT_ID", "IGDB_CLIENT_SECRET")})
    common = {
        "image": image,
        "labels": {"org.pgdp.phase34.run": run.token},
        "environment": environment,
        "volumes": [
            "owned:/phase34/owned",
            str(run.root / "Games") + ":/phase34/owned/library:ro",
        ],
        "networks": {"isolated": {}},
        "tmpfs": ["/romm", "/redis-data"],
    }
    api = {
        **common,
        "command": [
            "bash",
            "-ec",
            "cd /backend; alembic upgrade head; python startup.py; nginx; "
            "exec gunicorn main:app --worker-class uvicorn_worker.UvicornWorker "
            "--bind 127.0.0.1:5000 --workers 1 --timeout 300",
        ],
        "networks": {"isolated": {"aliases": ["phase34-production-app"]}},
    }
    worker = {
        **common,
        "working_dir": "/backend",
        "entrypoint": ["/src/.venv/bin/rq"],
        "command": [
            "worker",
            "--path",
            "/backend",
            "--worker-class",
            "handler.rq_worker.RomMWorker",
            "--name",
            run.project + "-separate-worker",
            "high",
            "default",
            "low",
        ],
        "environment": {
            **environment,
            "RQ_REDIS_URL": "redis://:"
            + run.token
            + "@"
            + run.env["REDIS_HOST"]
            + ":6379/0",
        },
    }
    return {
        "services": {"api": api, "worker": worker},
        "networks": {"isolated": {"external": True, "name": run.project + "_isolated"}},
        "volumes": {"owned": {"external": True, "name": volume}},
    }


def run_production():
    # Validate explicit connection before provisioning any fixture.
    portainer = Portainer()
    run = Run()
    image = None
    browser_image = None
    stack_id = None
    succeeded = False
    stack_name = run.project + "-production"
    try:
        browser_image = build_browser(run)
        run.image = browser_image
        run.start()
        portainer.verify_engine(run)
        image = build_production(run)
        config = stack_config(run, image)
        compose = json.dumps(config)
        secret_path = run.control / "portainer-stack.json"
        secret_path.write_text(compose)
        secret_path.chmod(0o600)
        stack_id = portainer.create(stack_name, compose)
        (run.evidence / "production-stack.json").write_text(
            json.dumps(
                {
                    "stack_id": stack_id,
                    "stack_name": stack_name,
                    "endpoint_id": portainer.endpoint,
                    "image": image,
                    "separate_worker": True,
                    "dev_mode": False,
                },
                indent=2,
            )
        )
        wait_http(run, "http://phase34-production-app:8080/api/heartbeat", seconds=50)
        browser_cases(
            run, base_url="http://phase34-production-app:8080", production=True
        )
        nginx_boundary(run, image)
        succeeded = True
    finally:
        if stack_id is not None:
            portainer.delete(stack_id, stack_name)
        close_recorded(
            run,
            "production",
            succeeded,
            image=[item for item in (image, browser_image) if item is not None],
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["portainer"], required=True)
    parser.add_argument("--suite", choices=["fresh-install"], required=True)
    parser.parse_args()
    host_preflight()
    run_production()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, SubprocessError) as error:
        print("FAILED: " + str(error))
        raise SystemExit(1) from error
