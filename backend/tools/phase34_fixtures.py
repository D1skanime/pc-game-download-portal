"""Synthetic source fixtures and isolated validation commands."""

import hashlib
import json
import shutil
from pathlib import Path

SQL_IMAGES = {
    "mariadb": "mariadb:10.11",
    "mysql": "mysql:8.4",
    "postgresql": "postgres:15",
}
BASELINE = "0138_rom_metadata_facet_roles_view"
LIFECYCLE = "src/v2/composables/useScanLifecycle/index.test.ts"
JOB_IDENTITY = "tests/endpoints/sockets/test_scan_job_identity.py"


def redact_output(output, token):
    import re

    output = output.replace(token, "[run-token]")
    output = re.sub(
        r"eyJ[A-Za-z0-9_.-]+",
        "[redacted-jwt]",
        output,
    )
    return re.sub(r"(?i)Bearer\s+[A-Za-z0-9_.-]+", "Bearer [redacted]", output)


def redact_evidence(evidence, token):
    from tempfile import NamedTemporaryFile

    for path in evidence.iterdir():
        if path.is_file() and not path.is_symlink() and path.suffix in {".log", ".xml"}:
            output = path.read_text()
            redacted = redact_output(output, token)
            if output != redacted:
                with NamedTemporaryFile(
                    mode="w", dir=evidence, delete=False
                ) as temporary:
                    temporary.write(redacted)
                    replacement = Path(temporary.name)
                replacement.replace(path)


def restore_generated_owner(run, resources):
    import os

    if not run.runner or run.manifest is None:
        return
    for identity in resources["container"]:
        if run.inspect("container", identity)["Id"] == run.runner:
            script = (
                "import os\n"
                "from pathlib import Path\n"
                "for root in [Path('/app/frontend/src/__generated__'),Path('/app/frontend/dist')]:\n"
                " if not root.exists() or root.is_symlink(): continue\n"
                " for directory,_,files in os.walk(root,followlinks=False):\n"
                "  os.chown(directory,"
                + str(os.getuid())
                + ","
                + str(os.getgid())
                + ",follow_symlinks=False)\n"
                "  for name in files:\n"
                "   os.chown(Path(directory)/name,"
                + str(os.getuid())
                + ","
                + str(os.getgid())
                + ",follow_symlinks=False)\n"
            )
            run.exec(["uv", "run", "python", "-c", script])
            return


def source_manifest(root):
    return [
        {
            "path": p.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "size": p.stat().st_size,
            "mtime_ns": p.stat().st_mtime_ns,
        }
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]


def code_manifest(snapshot):
    """Fingerprint copied code only, never source-library or environment bytes."""
    files = {}
    for path in sorted(snapshot.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(snapshot)
        if any(
            part in {"node_modules", "__pycache__", ".pytest_cache", "dist"}
            for part in relative.parts
        ):
            continue
        if path.name == ".env" or path.name.startswith(".env."):
            continue
        files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    encoded = json.dumps(files, sort_keys=True).encode()
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "files": files}


def prepare_media(games):
    import struct
    import zlib

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    image = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + bytes([40, 50, 60]) * 16) * 16))
        + chunk(b"IEND", b"")
    )
    directory = games / "PC/soundtracks"
    directory.mkdir()
    (directory / "cover.png").write_bytes(image)
    # STREAMINFO and PICTURE follow RFC 9639 sections 8.2 and 8.8.
    streaminfo = struct.pack(">HH", 4096, 4096) + bytes(6)
    streaminfo += ((44100 << 44) | (1 << 41) | (15 << 36)).to_bytes(8, "big") + bytes(
        16
    )
    picture = struct.pack(">II", 3, 9) + b"image/png"
    picture += struct.pack(">IIIIII", 0, 16, 16, 24, 0, len(image)) + image
    (directory / "track.flac").write_bytes(
        b"fLaC"
        + b"\0\0\0\x22"
        + streaminfo
        + b"\x86"
        + len(picture).to_bytes(3, "big")
        + picture
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 0 /Kids [] >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += str(index).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 3\n0000000000 65535 f \n" + b"".join(
        f"{offset:010d} 00000 n \n".encode() for offset in offsets
    )
    pdf += (
        b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )
    (directory / "manual.pdf").write_bytes(pdf)


def prepare(root, repo):
    games = root / "Games"
    games.mkdir()
    for platform in (
        "PC",
        "Nintendo Switch",
        "PlayStation 2",
        "SNES Super Nintendo",
        "GB GameBoy",
        "GBA GameBoy Advance",
        "Nintendo 64",
        "PSP",
    ):
        folder = games / platform
        folder.mkdir()
        (folder / "Phase34-Synthetic.bin").write_bytes(b"phase34 synthetic fixture\n")
    prepare_media(games)
    snapshot = root / "checkout"
    snapshot.mkdir()
    for folder in ("backend", "frontend", "docker"):
        if folder == "docker" and not (repo / folder).is_dir():
            continue
        shutil.copytree(
            repo / folder,
            snapshot / folder,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                "node_modules",
                ".venv",
                "__pycache__",
                ".pytest_cache",
                ".env",
                ".env.*",
                "pgdp_test",
                "Media",
                "dist",
                "test-results",
            ),
        )
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(repo / name, snapshot / name)
    return games, snapshot


def cleanup_snapshot(root, project):
    import re
    import tempfile

    snapshot = root / "checkout"
    if not snapshot.exists():
        return
    if (
        not re.fullmatch(r"pgdp34-[a-f0-9]{32}", project)
        or root.parent.resolve() != Path(tempfile.gettempdir()).resolve()
        or not root.name.startswith(project + "-")
        or root.is_symlink()
        or snapshot.is_symlink()
        or snapshot.resolve() != root.resolve() / "checkout"
    ):
        raise RuntimeError("snapshot cleanup containment failed")
    shutil.rmtree(snapshot)


def backend_command(args, name="backend"):
    return [
        "uv",
        "run",
        "pytest",
        "-c",
        "/app/backend/pytest.ini",
        "-o",
        "cache_dir=/phase34/owned/pytest-cache",
        "--junitxml=/phase34/evidence/" + name + ".xml",
        *args,
    ]


def frontend_command(args, name="frontend"):
    return [
        "npm",
        "run",
        "test",
        "--",
        "--run",
        *args,
        "--reporter=default",
        "--reporter=junit",
        "--outputFile=/phase34/evidence/" + name + ".xml",
    ]


def schema_commands():
    # A failed direction stops the chain. No SQLite substitution is possible.
    guard = [
        "uv",
        "run",
        "python",
        "-c",
        "from tools.phase34_target_guard import validate_target; validate_target()",
    ]
    return [
        guard,
        ["uv", "run", "alembic", "upgrade", "head"],
        ["uv", "run", "alembic", "downgrade", BASELINE],
        ["uv", "run", "alembic", "upgrade", "head"],
        [
            "uv",
            "run",
            "python",
            "-c",
            "from tools.phase34_fixtures import schema_parity; schema_parity()",
        ],
    ]


def schema_parity():
    from tools.phase34_target_guard import validate_target

    validate_target()
    from sqlalchemy import (
        Column,
        ForeignKey,
        Integer,
        MetaData,
        Table,
        UniqueConstraint,
        create_engine,
        inspect,
        select,
    )
    from sqlalchemy.exc import IntegrityError

    from config.config_manager import ConfigManager

    url = ConfigManager.get_db_engine()
    validate_target(resolved_url=url)
    engine = create_engine(url)
    metadata = MetaData()
    parent = Table(
        "phase34_parity_parent",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("slot", Integer, nullable=False),
        UniqueConstraint("slot"),
    )
    child = Table(
        "phase34_parity_child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey(parent.c.id), nullable=False),
    )
    with engine.begin() as conn:
        assert (
            "platforms" in inspect(conn).get_table_names()
        ), "migrations did not create catalog"
        metadata.create_all(conn)
        conn.execute(parent.insert().values(id=1, slot=1))
        conn.execute(child.insert().values(id=1, parent_id=1))
        assert conn.execute(select(parent.c.id).with_for_update()).scalar_one() == 1
    for statement in (
        parent.insert().values(id=2, slot=1),
        child.insert().values(id=2, parent_id=99),
    ):
        try:
            with engine.begin() as conn:
                conn.execute(statement)
        except IntegrityError:
            pass
        else:
            raise AssertionError("missing uniqueness or foreign-key enforcement")
    with engine.begin() as conn:
        conn.execute(child.delete())
        conn.execute(parent.update().values(slot=2))
        assert conn.execute(select(parent.c.slot)).scalar_one() == 2
        conn.execute(parent.delete())
        metadata.drop_all(conn)
    from tools.phase34_operation_schema import check_operations

    check_operations(engine)
    print("PASS schema constraints, lock statement and CRUD:", engine.dialect.name)


def expected_red(path, expected_names):
    from xml.etree import ElementTree  # nosec B405, bounded local runner evidence

    payload = path.read_bytes()
    if len(payload) > 10_000_000 or b"<!DOCTYPE" in payload or b"<!ENTITY" in payload:
        raise RuntimeError("RED rejected: unsafe XML evidence")
    root = ElementTree.fromstring(payload)  # nosec B314, declarations rejected above
    cases = list(root.iter("testcase"))
    errors = list(root.iter("error"))
    failures = {
        case.attrib["name"]: case.find("failure")
        for case in cases
        if case.find("failure") is not None
    }
    if errors or not cases or set(failures) != set(expected_names):
        raise RuntimeError(
            "RED rejected: unexpected failures, collection or infrastructure errors"
        )
    for name, marker in expected_names.items():
        failure = failures[name]
        assert failure is not None
        if marker not in (failure.attrib.get("message", "") + (failure.text or "")):
            raise RuntimeError("RED rejected: wrong assertion for " + name)
    print("PASS expected behavioral RED:", ", ".join(sorted(failures)))
    return {"cases": len(cases), "failures": sorted(failures)}


def interpolation_matches(reference, actual):
    import re

    expected = re.findall(r"\{[^{}]+\}", reference)
    translated = re.findall(r"\{[^{}]+\}", actual)
    if "|" in reference or "|" in actual:
        # Different languages have different plural categories.
        return set(expected) == set(translated)
    return sorted(expected) == sorted(translated)


def locale_check(scope, locales):
    namespace = "setup" if scope == "setup-locales" else "scan"
    base = Path("/app/frontend/src/locales")
    requested = locales.split(",")
    if not requested or len(requested) != len(set(requested)):
        raise RuntimeError("invalid locale batch")

    def flat(value, prefix=""):
        result: dict[str, str] = {}
        for key, item in value.items():
            name = prefix + key
            result.update(
                flat(item, name + ".") if isinstance(item, dict) else {name: item}
            )
        return result

    import re

    reference = flat(json.loads((base / "en_US" / (namespace + ".json")).read_text()))
    for locale in requested:
        if not re.fullmatch(r"[a-z]{2}_[A-Z]{2}", locale):
            raise RuntimeError("invalid locale")
        data = json.loads((base / locale / (namespace + ".json")).read_text())
        actual = flat(data)
        assert actual.keys() == reference.keys(), "locale key parity: " + locale
        for key, value in actual.items():
            assert interpolation_matches(reference[key], value), key

        def sorted_keys(obj, code=locale):
            assert list(obj) == sorted(obj), "unsorted locale: " + code
            for value in obj.values():
                if isinstance(value, dict):
                    sorted_keys(value)

        sorted_keys(data)
    print("PASS scoped locale parity/interpolation/order:", locales)


def locale_probe(run, namespace):
    """Generate a mounted locale check only in the disposable source snapshot."""
    path = "src/v2/locales/phase34-" + namespace + ".test.ts"
    target = run.root / "checkout/frontend" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        'import { mount } from "@vue/test-utils";\n'
        'import { defineComponent, h } from "vue";\n'
        'import { createI18n, useI18n } from "vue-i18n";\n'
        'import { readFileSync } from "node:fs";\n'
        'import { expect, test } from "vitest";\n'
        "const ns = " + json.dumps(namespace) + ";\n"
        'const locales = process.env.PGDP_TEST_LOCALES!.split(",");\n'
        'function flat(value: Record<string, unknown>, prefix = ""): Record<string, string> {\n'
        " return Object.fromEntries(Object.entries(value).flatMap(([key, item]) =>\n"
        '  typeof item === "object" ? Object.entries(flat(item as Record<string, unknown>, prefix + key + ".")) : [[prefix + key, item as string]]));\n'
        "}\n"
        'for (const locale of locales) test("mounted recovery messages " + locale, () => {\n'
        ' const data = JSON.parse(readFileSync("src/locales/" + locale + "/" + ns + ".json", "utf8"));\n'
        " const i18n = createI18n({legacy:false, locale, fallbackLocale:false, messages:{[locale]:{[ns]:data}}});\n"
        " const messages = flat(data);\n"
        ' const View = defineComponent({ setup() { const {t} = useI18n(); return () => h("div", Object.entries(messages).map(([key, value]) => {\n'
        '  const params = Object.fromEntries([...value.matchAll(/\\{([^{}]+)\\}/g)].map(match => [match[1], "1"]));\n'
        '  return h("p", t(ns + "." + key, params));\n'
        " })); }});\n"
        " const wrapper = mount(View, {global:{plugins:[i18n]}});\n"
        ' expect(wrapper.findAll("p").length).toBe(Object.keys(messages).length);\n'
        ' for (const node of wrapper.findAll("p")) { expect(node.text().trim()).not.toBe(""); expect(node.text()).not.toMatch(new RegExp("^" + ns + "\\\\.")); }\n'
        " wrapper.unmount();\n"
        "});\n"
    )
    return path


def quality(run, args, repo):
    if args.scope:
        if not args.locales:
            raise RuntimeError("--scope requires --locales")
        run.exec(
            [
                "uv",
                "run",
                "python",
                "/app/backend/tools/phase34_fixtures.py",
                "locales",
                args.scope,
                args.locales,
            ]
        )
        namespace = "setup" if args.scope == "setup-locales" else "scan"
        path = locale_probe(run, namespace)
        run.exec(
            frontend_command(
                [
                    path,
                    (
                        "src/v2/views/Auth/Setup.test.ts"
                        if namespace == "setup"
                        else "src/v2/views/Scan.test.ts"
                    ),
                ]
            ),
            frontend=True,
            extra={"PGDP_TEST_LOCALES": args.locales},
        )
        return
    # Export API in the same disposable network and container loopback namespace.
    run.exec(
        [
            "sh",
            "-c",
            "uv run uvicorn main:app --host 127.0.0.1 --port 3344 >/phase34/evidence/schema-server.log 2>&1 &",
        ]
    )
    run.exec(
        [
            "uv",
            "run",
            "python",
            "-c",
            "import time, urllib.request\nfor i in range(20):\n try:\n  urllib.request.urlopen('http://127.0.0.1:3344/openapi.json', timeout=2); break\n except OSError: time.sleep(1)\nelse: raise RuntimeError('isolated schema export unavailable')",
        ]
    )
    for command in (
        ["npm", "run", "generate"],
        ["npm", "run", "typecheck"],
        frontend_command([]),
        ["npm", "run", "build"],
        ["python3", "src/locales/check_i18n_locales.py"],
        ["python3", "src/locales/check_i18n_sorted.py"],
        ["npm", "run", "v2:maintainability"],
    ):
        run.exec(command, frontend=True, timeout=300)
    changed = run.command(
        ["git", "diff", "--name-only", "HEAD"], cwd=repo
    ).stdout.splitlines()
    scoped = [path for path in changed if path.startswith(("backend/", "frontend/"))]
    if not scoped:
        scoped = [
            "backend/tools/phase34.py",
            "backend/tools/phase34_target_guard.py",
            "backend/tools/phase34_fixtures.py",
        ]
    # Small batches avoid analyzer errors on large mixed source lists.
    for offset in range(0, len(scoped), 4):
        run.command(
            [
                "/home/d1sk/.local/bin/trunk",
                "check",
                "--no-fix",
                "--jobs",
                "1",
                *scoped[offset : offset + 4],
            ],
            cwd=repo,
            timeout=300,
        )


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["parity"]:
        schema_parity()
    elif len(sys.argv) == 4 and sys.argv[1] == "locales":
        locale_check(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit("unknown fixture check")
