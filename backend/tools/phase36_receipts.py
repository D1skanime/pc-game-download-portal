"""Fail-closed digest and scenario validation for explicit Phase36 evidence."""

import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import Path

DIALECTS = ("mariadb", "postgresql")
GATES = {
    (kind, dialect)
    for kind in ("browser", "descriptions", "authority", "backend")
    for dialect in DIALECTS
} | {("quality", "mariadb"), ("security", "static")}
BROWSER_CHECKS = {
    "legacy_empty",
    "actual_worker_refetch",
    "manual_protection",
    "actual_editor_save",
    "durable_manual",
    "component",
    "dirty_locale",
    "background_refresh",
    "clear_exact",
    "conflict409",
    "error_retention",
    "read_only",
    "authorization",
    "safe_markup",
    "safe_provider_markup",
    "source_language",
    "no_view_transport",
    "trigger_focus",
    "mouse",
    "keyboard",
    "touch",
    "gamepad_bridge",
    "targets",
    "contrast",
    "overflow",
    "admin_language",
    "personal_no_global_write",
    "config_failure",
    "config_cas",
    "accepted_snapshot",
    "scheduled_language",
    "game_refresh",
    "manual_scan",
}
INTERACTIVE = {
    "interactive-" + provider + locale
    for provider in ("steam", "ss")
    for locale in ("de", "fr", "en")
}
DESCRIPTION_STAGES = (
    {
        "repair-de",
        "repair-rest-de",
        "cooldown-de",
        "repair-fr",
        "repair-en",
        "restart-cooldown",
        "ss-disabled-selection",
        "ss-fault",
        "ss-restart-backoff",
        "warm-manual",
        "warm-scheduled",
        "new-igdb",
        "game-refresh-steam",
        "game-refresh-ss",
    }
    | INTERACTIVE
    | {
        "manual-mode-" + mode
        for mode in ("update", "unmatched", "complete", "hashes", "new_platforms")
    }
)
SECURITY = {"T-36-14", "T-36-15", "T-36-16"}
SHA = re.compile(r"[a-f0-9]{64}")
TRACE_LINE_BYTES = 32_000_000
TRACE_MEMBER_BYTES = 128_000_000
TRACE_ARCHIVE_BYTES = 256_000_000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000:
        raise RuntimeError("missing, unsafe or oversized evidence")
    try:
        return json.loads(path.read_text())
    except (ValueError, UnicodeError) as error:
        raise RuntimeError("invalid evidence JSON") from error


def child(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise RuntimeError("evidence path must be relative")
    path = root / name
    if ".." in Path(name).parts or any(
        parent.is_symlink() for parent in (path, *path.parents)
    ):
        raise RuntimeError("evidence traversal or symlink")
    if not path.resolve().is_relative_to(root.resolve()):
        raise RuntimeError("evidence escapes retained root")
    return path


def clean(cleanup):
    if not all(
        cleanup.get(key) is True
        for key in ("clean", "snapshot_removed", "source_unchanged")
    ):
        raise RuntimeError("partial cleanup")
    if set(cleanup.get("remaining", {})) != {"container", "network", "volume"}:
        raise RuntimeError("missing resource cleanup inventory")
    if any(cleanup["remaining"].values()):
        raise RuntimeError("resources remain")
    actual = cleanup.get("exact_resources", {})
    if set(actual) != {"container", "network", "volume"} or not all(
        isinstance(value, list) and value for value in actual.values()
    ):
        raise RuntimeError("missing actual resource ownership")


def sources(manifest, current):
    files = manifest.get("files", {})
    if not files or not all(
        isinstance(name, str) and SHA.fullmatch(value) for name, value in files.items()
    ):
        raise RuntimeError("invalid source hashes")
    if current is not None and manifest != current:
        raise RuntimeError("stale frozen source manifest")


def dependency_files(kind, current):
    """Declare scenario file scopes independently from receipt-provided lists."""
    if kind not in {pair[0] for pair in GATES}:
        raise RuntimeError("unknown dependency scenario")
    if kind == "backend":
        from phase36_quality import ci_source_files

        return ci_source_files()
    protected = current.get("protected_untracked", {})
    if any(current["files"].get(name) != value for name, value in protected.items()):
        raise RuntimeError("protected source hash mismatch")
    selected = {}
    for name, value in current["files"].items():
        if name in protected:
            continue
        backend = name.startswith("backend/") and not name.startswith(
            ("backend/tests/", "backend/tools/")
        )
        frontend = name.startswith("frontend/src/") and not name.endswith(
            (".test.ts", ".spec.ts", ".stories.ts")
        )
        infrastructure = (
            name.startswith("docker/")
            or name in {"pyproject.toml", "uv.lock"}
            or (
                name.startswith("frontend/")
                and "/" not in name.removeprefix("frontend/")
            )
        )
        helper = name.startswith("backend/tools/phase")
        if kind in {"browser", "descriptions", "authority"} and name in {
            "backend/tools/phase36_receipts.py",
            "backend/tools/phase36_quality.py",
        }:
            helper = False
        extra = (
            kind == "security"
            or (kind == "backend" and name.startswith("backend/"))
            or (kind == "quality" and name.startswith("frontend/"))
            or (kind == "browser" and name.startswith("frontend/e2e/"))
        )
        if backend or frontend or infrastructure or helper or extra:
            selected[name] = value
    if not selected:
        raise RuntimeError("empty scenario source dependencies")
    return selected


def source_dependencies(entry, tested, current):
    sources(tested, None)
    if current is None:
        return
    kind = entry["kind"]
    record = entry.get("dependencies", {})
    if record.get("scenario") != kind:
        raise RuntimeError("source dependency scenario mismatch")
    required = dependency_files(kind, current)
    if kind == "backend" and tested["files"] != required:
        raise RuntimeError("backend source differs from independent CI inventory")
    if record.get("files") != required:
        raise RuntimeError("removed, stale or mis-scoped source dependency")
    if any(tested["files"].get(name) != value for name, value in required.items()):
        raise RuntimeError("relevant tested source differs from current source")
    delta = []
    for name in sorted(set(tested["files"]) | set(current["files"])):
        before, after = tested["files"].get(name), current["files"].get(name)
        if before == after:
            continue
        reason = (
            "protected_untracked"
            if name in current.get("protected_untracked", {})
            else (
                "ci_tracked_support"
                if kind == "backend" and name in required
                else "outside_scenario"
            )
        )
        delta.append(
            {"file": name, "tested": before, "current": after, "reason": reason}
        )
    if record.get("snapshot_delta") != delta:
        raise RuntimeError("unexplained full snapshot source delta")


def browser(payload, artifacts):
    checks = payload.get("checks", {})
    if any(checks.get(key) is not True for key in BROWSER_CHECKS):
        raise RuntimeError("missing connected browser scenario")
    if set(payload.get("interactive", [])) != INTERACTIVE:
        raise RuntimeError("missing provider/locale browser entrypoint")
    matrix = payload.get("matrix", {})
    expected = {
        str(width) + "-" + theme
        for width in (320, 600, 960, 1280, 1920, 3840)
        for theme in ("dark", "light")
    }
    rows = matrix.get("captures", [])
    if not expected.issubset({row["case"] for row in rows}):
        raise RuntimeError("missing responsive/theme matrix")
    if not {"de_DE", "zh_CN", "zoom200", "reduced-motion"}.issubset(
        {row["case"] for row in rows}
    ):
        raise RuntimeError("missing accessibility matrix")
    for row in rows:
        if artifacts.get(row["file"]) != row["sha256"]:
            raise RuntimeError("missing or tampered screenshot")
    if payload.get("controlledPresentation") is not True:
        raise RuntimeError("presentation provenance missing")
    if payload.get("physicalController") not in ("verified", "unverified"):
        raise RuntimeError("physical controller status missing")


def quality(payload):
    checks = payload.get("checks", [])
    npm = {tuple(row["command"]) for row in checks}
    expected: set[tuple[str, ...]] = {
        ("npm", "run", name)
        for name in ("generate", "typecheck", "test", "build", "v2:maintainability")
    }
    expected |= {
        ("python3", "src/locales/" + name)
        for name in ("check_i18n_locales.py", "check_i18n_sorted.py")
    }
    if not expected.issubset(npm) or any(row.get("exit") != 0 for row in checks):
        raise RuntimeError("incomplete frontend quality")


def validate_entry(entry, root, current):
    pair = entry.get("kind"), entry.get("dialect")
    if pair not in GATES:
        raise RuntimeError("unknown gate or dialect")
    evidence = child(root, entry.get("evidence"))
    artifacts = entry.get("artifacts", {})
    required = {"result.json", "cleanup.json", "commands.json", "code-before.json"}
    if not required.issubset(artifacts):
        raise RuntimeError("missing required artifact")
    for name, expected in artifacts.items():
        path = child(evidence, name)
        if (
            not SHA.fullmatch(expected)
            or not path.is_file()
            or digest(path) != expected
        ):
            raise RuntimeError("missing or tampered artifact")
    payload = read(evidence / "result.json")
    if payload.get("phase") != 36 or payload.get("passed") is not True:
        raise RuntimeError("failed or historical receipt")
    if (payload.get("kind"), payload.get("dialect")) != pair:
        raise RuntimeError("receipt gate/dialect mismatch")
    source_dependencies(entry, read(evidence / "code-before.json"), current)
    clean(read(evidence / "cleanup.json"))
    commands = read(evidence / "commands.json")
    if not commands or any(row.get("exit") != 0 for row in commands):
        raise RuntimeError("failed command")
    kind = pair[0]
    if kind == "browser":
        browser(payload["browser"], artifacts)
    elif kind in {"descriptions", "authority"}:
        from phase36_description_probe import validate_receipt

        validate_receipt(payload)
        if kind == "descriptions" and not DESCRIPTION_STAGES.issubset(
            payload["description_stages"]
        ):
            raise RuntimeError("partial connected description run")
    elif kind == "quality":
        quality(payload)
    elif kind == "backend":
        from phase36_quality import validate_backend_shards, validate_backend_summary

        validate_backend_summary(payload)
        validate_backend_shards(payload, evidence, artifacts)
    elif kind == "security":
        if payload.get("threats") != dict.fromkeys(SECURITY, "resolved"):
            raise RuntimeError("missing security barrier")
    return pair


def validate_index(index, root, *, current=None):
    if index.get("phase") != 36 or not index.get("entries"):
        raise RuntimeError("missing Phase36 final index")
    sources(index.get("source_hashes", {}), current)
    found = []
    for entry in index["entries"]:
        found.append(validate_entry(entry, Path(root), current))
    if set(found) != GATES or len(found) != len(GATES):
        raise RuntimeError("missing or duplicate final gate")
    return index


def assert_receipts(path):
    from phase34 import REPO
    from phase35_browser_receipts import current_sources

    if not path:
        raise RuntimeError("explicit receipt index required")
    target = Path(path).resolve()
    phase = (
        REPO
        / ".planning/phases/36-localized-provider-descriptions-without-legacy-summary"
    )
    if target.parent != phase or target.name != "36-final-receipts.json":
        raise RuntimeError("unexpected Phase36 receipt index")
    index = read(target)
    current_sources(index["source_hashes"])
    import subprocess  # nosec B404, fixed read-only index enumeration

    # trunk-ignore(bandit/B603): Fixed Git argv inside the verified repository.
    untracked = subprocess.check_output(  # nosec B603,B607
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "backend",
            "frontend",
        ],
        cwd=REPO,
        text=True,
    ).split("\0")
    expected = {
        name: value
        for name, value in index["source_hashes"]["files"].items()
        if name in untracked
    }
    if index["source_hashes"].get("protected_untracked", {}) != expected:
        raise RuntimeError("protected untracked inventory differs from Git")
    validate_index(index, phase, current=index["source_hashes"])
    print("PASS complete Phase36 exact-source final evidence")


def sanitize(evidence, token):
    """Remove disposable credentials from text and Playwright archive members."""
    from phase34_fixtures import redact_output

    sensitive = {
        "authorization",
        "cookie",
        "set-cookie",
        "x-csrftoken",
        "romm_csrftoken",
        "romm_session",
    }

    def scrub(value):
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, dict):
            result = {key: scrub(item) for key, item in value.items()}
            if str(value.get("name", "")).lower() in sensitive and "value" in result:
                result["value"] = "[redacted]"
            for key in result:
                if key.lower() in sensitive or key.lower() in {
                    "access_token",
                    "refresh_token",
                    "password",
                }:
                    result[key] = "[redacted]"
            return result
        if isinstance(value, str):
            return redact_output(value, token)
        return value

    def payload(data):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            if token.encode() in data:
                raise RuntimeError("credential in binary artifact") from error
            return data
        lines = []
        for line in text.splitlines(keepends=True):
            try:
                line = json.dumps(scrub(json.loads(line))) + (
                    "\n" if line.endswith("\n") else ""
                )
            except ValueError:
                line = redact_output(line, token)
            lines.append(line)
        return "".join(lines).encode()

    for path in Path(evidence).rglob("*"):
        if path.is_symlink():
            raise RuntimeError("unsafe retained artifact symlink")
        if not path.is_file():
            continue
        if path.suffix != ".zip":
            path.write_bytes(payload(path.read_bytes()))
            continue
        output = io.BytesIO()
        total = 0
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(output, "w") as target:
            entries = source.infolist()
            if len(entries) > 100_000:
                raise RuntimeError("too many trace archive members")
            for entry in entries:
                name = entry.filename
                if (
                    entry.file_size > TRACE_MEMBER_BYTES
                    or Path(name).is_absolute()
                    or "\\" in name
                    or ":" in name.split("/")[0]
                    or ".." in Path(name).parts
                    or stat.S_ISLNK(entry.external_attr >> 16)
                ):
                    raise RuntimeError("unsafe trace archive member")
                total += entry.file_size
                if total > TRACE_ARCHIVE_BYTES:
                    raise RuntimeError("trace archive total exceeds limit")
                count = 0
                expected_size = entry.file_size
                with source.open(entry) as incoming, target.open(
                    entry, "w"
                ) as outgoing:
                    if name.endswith((".network", ".trace", ".stacks")):
                        while True:
                            line = incoming.readline(TRACE_LINE_BYTES + 1)
                            if not line:
                                break
                            if len(line) > TRACE_LINE_BYTES:
                                raise RuntimeError("trace JSONL record exceeds limit")
                            count += len(line)
                            if count > TRACE_MEMBER_BYTES:
                                raise RuntimeError("trace member exceeds limit")
                            try:
                                value = json.loads(line.decode("utf-8"))
                            except (ValueError, UnicodeError) as error:
                                raise RuntimeError(
                                    "invalid trace JSONL record"
                                ) from error
                            outgoing.write((json.dumps(scrub(value)) + "\n").encode())
                    else:
                        data = incoming.read(TRACE_MEMBER_BYTES + 1)
                        count = len(data)
                        if count > TRACE_MEMBER_BYTES:
                            raise RuntimeError("trace member exceeds limit")
                        outgoing.write(payload(data))
                if count != expected_size:
                    raise RuntimeError("trace member byte count mismatch")
        path.write_bytes(output.getvalue())
