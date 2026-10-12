#!/usr/bin/env python3
"""Reject local runtime artefacts, accidental secrets, and oversized tracked files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_TRACKED_FILE_BYTES = 10 * 1024 * 1024
FORBIDDEN_PREFIXES = (
    ".codex/",
    ".tmp/",
    ".github/resources/",
    "Docker/",
    "Games/",
    "RomM-phase",
)
ARCHIVE_ALLOWLIST_PREFIXES = (
    "backend/tests/tasks/fixtures/",
    "tests/fixtures/",
)
FORBIDDEN_MEDIA_SUFFIXES = {".mp3", ".mp4", ".mkv", ".7z", ".rar", ".iso"}
SECRET_FILE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SECRET_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"ghp_",
    b"github_pat_",
    b"sk-live-",
    b"xoxb-",
    b"AIza",
)


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [path for path in result.stdout.decode().split("\0") if path]


def is_allowed_archive(path: str) -> bool:
    return path.startswith(ARCHIVE_ALLOWLIST_PREFIXES)


def main() -> int:
    violations: list[str] = []
    for path in tracked_paths():
        normalized = path.replace("\\", "/")
        file_path = Path(path)
        if normalized.startswith(FORBIDDEN_PREFIXES):
            violations.append(f"forbidden tracked path: {path}")
        if (
            file_path.suffix.lower() in FORBIDDEN_MEDIA_SUFFIXES
            and not is_allowed_archive(normalized)
        ):
            violations.append(f"forbidden tracked media/archive: {path}")
        if file_path.name in {
            ".env",
            ".env.local",
            ".env.production",
            ".env.development",
        }:
            violations.append(f"tracked environment file: {path}")
        if file_path.suffix.lower() in SECRET_FILE_SUFFIXES:
            violations.append(f"tracked secret/key file: {path}")
        try:
            size = file_path.stat().st_size
        except FileNotFoundError:
            violations.append(f"tracked file missing from checkout: {path}")
            continue
        if size > MAX_TRACKED_FILE_BYTES:
            violations.append(
                f"tracked file exceeds {MAX_TRACKED_FILE_BYTES // (1024 * 1024)} MiB: "
                f"{path} ({size} bytes)"
            )
        if size <= 2 * 1024 * 1024:
            continue
        try:
            data = file_path.read_bytes()
        except OSError:
            continue
        for marker in SECRET_MARKERS:
            if marker in data:
                violations.append(f"possible secret marker in tracked file: {path}")
                break

    if violations:
        print("Repository hygiene check failed:")
        print("\n".join(f"- {item}" for item in violations))
        return 1
    print("Repository hygiene check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
