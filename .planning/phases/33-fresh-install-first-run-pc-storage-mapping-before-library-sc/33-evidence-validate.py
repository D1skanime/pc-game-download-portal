"""Validate executed browser, exact source mount, manifests, and owned cleanup."""

import argparse
import json
import os
import pathlib
import re
import subprocess  # nosec B404, fixed Docker inspection argv
import tempfile


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def validate_rendered(path, suffix, target, state=None):
    data = load(path)
    mounts = [m for s in data["services"].values() for m in s.get("volumes", [])]
    matches = [m for m in mounts if m.get("target") == target]
    if not len(matches) == 1:
        raise RuntimeError("exactly one library mount required")
    mount = matches[0]
    if not (mount.get("type") == "bind" and mount.get("read_only") is True):
        raise RuntimeError("acceptance evidence check failed")
    if not mount["source"].endswith(suffix):
        raise RuntimeError("acceptance evidence check failed")
    if state:
        if (
            not pathlib.Path(mount["source"]).is_absolute()
            or os.path.normpath(mount["source"]) != state["uat_root"] + "/fixture/Games"
        ):
            raise RuntimeError("effective compose source differs from owned fixture")
    aliases = [m for m in mounts if m.get("target") == "/phase34/owned/library"]
    if (
        len(aliases) != 1
        or aliases[0].get("type") != "bind"
        or aliases[0]["source"] != mount["source"]
        or aliases[0].get("read_only") is not True
    ):
        raise RuntimeError(
            "guarded library alias must bind the identical read-only fixture"
        )
    if not all(
        (
            not s.get("container_name") and (not s.get("ports"))
            for s in data["services"].values()
        )
    ):
        raise RuntimeError("acceptance evidence check failed")


def validate_daemon_mounts(evidence, state):
    token = state["compose_project"].removeprefix("pgdp34-")
    expected = (state["uat_root"] + "/fixture/Games").replace(token, "[run-token]")
    project = state["compose_project"].replace(token, "[run-token]")
    for path in sorted(evidence.glob("*.log")):
        try:
            payload = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        for item in payload if isinstance(payload, list) else [payload]:
            if not isinstance(item, dict):
                continue
            labels = item.get("Config", {}).get("Labels", {}) or {}
            if labels.get("com.docker.compose.project") != project:
                continue
            mounts = [
                mount
                for mount in item.get("Mounts", [])
                if mount.get("Destination")
                in {"/app/romm/library", "/phase34/owned/library"}
            ]
            if (
                len(mounts) == 2
                and all(
                    mount.get("Type") == "bind"
                    and mount.get("Source") == expected
                    and mount.get("RW") is False
                    and mount.get("Mode") == "ro"
                    for mount in mounts
                )
                and len({mount["Destination"] for mount in mounts}) == 2
            ):
                return
    raise RuntimeError(
        "authoritative exact read-only Docker library mounts are missing"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=pathlib.Path)
    parser.add_argument("--rendered-compose", type=pathlib.Path)
    parser.add_argument("--require-source-suffix", default="/fixture/Games")
    parser.add_argument("--require-target", default="/app/romm/library")
    parser.add_argument("--require-read-only", action="store_true")
    parser.add_argument("--assert-cleanup", action="store_true")
    args = parser.parse_args()
    if not args.state:
        validate_rendered(
            args.rendered_compose, args.require_source_suffix, args.require_target
        )
        return 0
    state = load(args.state)
    project = state["compose_project"]
    if not re.fullmatch("pgdp34-[a-f0-9]{32}", project):
        raise RuntimeError("acceptance evidence check failed")
    if not pathlib.Path(state["uat_root"]).parent == pathlib.Path(
        tempfile.gettempdir()
    ):
        raise RuntimeError("acceptance evidence check failed")
    if not pathlib.Path(state["uat_root"]).name.startswith(project + "-"):
        raise RuntimeError("acceptance evidence check failed")
    if not state["disposable_volume"] == project + "_owned":
        raise RuntimeError("acceptance evidence check failed")
    validate_rendered(
        state["rendered_compose"],
        args.require_source_suffix,
        args.require_target,
        state,
    )
    evidence = pathlib.Path(state["evidence_dir"])
    if (
        not state["browser_exit"]
        == state["backend_exit"]
        == state["frontend_exit"]
        == 0
    ):
        raise RuntimeError("acceptance evidence check failed")
    before, after = (load(evidence / "before.json"), load(evidence / "after.json"))
    if not before:
        raise RuntimeError("source fixture manifest is empty")
    segments = load(evidence / "fixture-segments.json")
    if len(segments) != 2:
        raise RuntimeError("normal/scheduled fixture additions must be explicit")
    expected_before = before
    for segment in segments:
        if (
            load(evidence / segment["before"]) != expected_before
            or load(evidence / segment["after"]) != expected_before
        ):
            raise RuntimeError("application changed Games between fixture additions")
        next_before = load(evidence / segment["next_before"])
        previous = {row["path"]: row for row in expected_before}
        current = {row["path"]: row for row in next_before}
        added = set(current) - set(previous)
        if len(added) != 2 or any(
            not path.startswith(segment["added_fixture"] + "/") for path in added
        ):
            raise RuntimeError("fixture addition differs from its named new game")
        if any(current.get(path) != row for path, row in previous.items()):
            raise RuntimeError("fixture addition modified an existing game file")
        expected_before = next_before
    if expected_before != after:
        raise RuntimeError("application changed Games after final fixture addition")
    if not (
        any(("My Games/" in str(x) for x in before))
        and any(("pc/" in str(x) for x in before))
    ):
        raise RuntimeError("acceptance evidence check failed")
    browser = load(evidence / "browser.json")
    if not browser["status"] == "PASS":
        raise RuntimeError("acceptance evidence check failed")
    discovery = browser["discovery"]
    folders = {folder["name"]: folder for folder in discovery["folders"]}
    if (
        set(folders) != {"pc", "My Games"}
        or folders["pc"]["suggested_platform"] != "win"
        or folders["My Games"]["association"] != "unknown"
    ):
        raise RuntimeError("direct known/unknown discovery response is not proven")
    assignment = browser["assignment"]
    if assignment["ready"] is not True or {
        mapping["folder_name"] for mapping in assignment["mappings"]
    } != {"pc", "My Games"}:
        raise RuntimeError("saved ready mappings are not proven")
    responses = browser["receipts"]
    if not any(
        response["method"] == "POST"
        and response["path"] == "/api/setup/folders/assign"
        and response["status"] == 200
        and response["body"].get("ready") is True
        for response in responses
    ):
        raise RuntimeError("actual successful assignment response is missing")
    if any(response["method"] != "GET" for response in browser["post_setup_receipts"]):
        raise RuntimeError("post-setup readiness performed a mutation")
    required = {
        "discovery",
        "inline_assignment",
        "ready",
        "reload",
        "get_only",
        "scan_completed",
        "mapped_reads",
        "explicit_child_scope",
        "parent_retired",
        "safe_owned_cleanup",
        "known_child_preserved",
        "normal_discovers_children",
        "scheduled_discovers_children",
        "theme_dark",
        "theme_light",
        "layout_320",
        "layout_desktop",
        "mouse",
        "keyboard",
        "touch",
        "touch_target",
        "progress_counts",
    }
    if not all((browser["checks"].get(key) is True for key in required)):
        raise RuntimeError("acceptance evidence check failed")
    if browser["gamepad"]["status"] not in {"PASS", "BLOCKED"}:
        raise RuntimeError("acceptance evidence check failed")
    if not browser["gamepad"].get("reason"):
        raise RuntimeError("acceptance evidence check failed")
    for name in browser["screenshots"]:
        if not pathlib.Path(name).name == name:
            raise RuntimeError("acceptance evidence check failed")
        if not (evidence / name).stat().st_size > 1000:
            raise RuntimeError("acceptance evidence check failed")
    if not list((evidence / "browser-results").rglob("trace.zip")):
        raise RuntimeError("acceptance evidence check failed")
    if args.assert_cleanup:
        validate_daemon_mounts(evidence, state)
        if not (state["teardown_exit"] == 0 and state["uat_root_removed"]):
            raise RuntimeError("acceptance evidence check failed")
        if not not pathlib.Path(state["uat_root"]).exists():
            raise RuntimeError("acceptance evidence check failed")
        cleanup = load(evidence / "cleanup.json")
        if not (
            cleanup["clean"]
            and cleanup["snapshot_removed"]
            and cleanup["source_unchanged"]
        ):
            raise RuntimeError("acceptance evidence check failed")
        if not not any(cleanup["remaining"].values()):
            raise RuntimeError("acceptance evidence check failed")
        for kind in ("container", "volume", "network"):
            result = (
                subprocess.run(  # nosec B603,B607, validated generated project filter
                    [
                        "docker",
                        kind,
                        "ls",
                        "-q",
                        "--filter",
                        "label=com.docker.compose.project=" + project,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            )
            if not not result.stdout.strip():
                raise RuntimeError("disposable resources remain")
    print("Phase 33 executed evidence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
