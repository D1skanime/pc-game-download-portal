#!/usr/bin/env python3
"""Fail-closed isolated manual/scheduled incremental scan acceptance."""

import argparse

import phase34

BRANCH = "codex/phase-35-incremental-windows-scans"
ORIGIN = "https://github.com/D1skanime/pc-game-download-portal.git"


def git_value(*args):
    # Fixed Git argv is run only after the canonical host/root preflight.
    return phase34.subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, cwd=phase34.REPO
    ).stdout.strip()


def preflight():
    phase34.host_preflight()
    if git_value("branch", "--show-current") != BRANCH:
        raise RuntimeError("unexpected execution branch")
    if git_value("remote", "get-url", "origin") != ORIGIN:
        raise RuntimeError("unexpected execution origin")
    project = (phase34.REPO / ".planning/PROJECT.md").read_text()
    state = (phase34.REPO / ".planning/STATE.md").read_text()
    if "RomM PC Library" not in project or "35" not in state:
        raise RuntimeError("planning identity mismatch")


def validate_receipt(receipt):
    cleanup = receipt.get("cleanup", {})
    if (
        cleanup.get("clean") is not True
        or cleanup.get("snapshot_removed") is not True
        or cleanup.get("source_unchanged") is not True
        or any(cleanup.get("remaining", {}).values())
    ):
        raise RuntimeError("incomplete cleanup receipt")
    if (
        receipt.get("passed") is not True
        or receipt.get("observed_worker") is not True
        or receipt.get("source_unchanged") is not True
        or not {"cold", "warm-manual", "warm-scheduled"}.issubset(
            receipt.get("stages", [])
        )
    ):
        raise RuntimeError("incomplete connected receipt")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dialect", choices=("mariadb", "postgresql"), required=True)
    parser.add_argument(
        "--scenario", choices=("incremental", "authority"), required=True
    )
    args = parser.parse_args()
    preflight()
    raise RuntimeError("connected scenario implementation pending: " + args.scenario)


if __name__ == "__main__":
    main()
