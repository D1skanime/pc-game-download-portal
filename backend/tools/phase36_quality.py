"""Final serial frontend quality, using the existing guarded quality owner."""

from phase35_browser_quality import execute_quality

__all__ = ["execute_quality"]


RVZ_SKIPS = {
    "tests/utils/test_rvz_hasher.py::test_real_gamecube_rvz_matches_retroachievements_hash": "mock GameCube RVZ not present",
    "tests/utils/test_rvz_hasher.py::test_real_wii_rvz_matches_retroachievements_hash": "mock Wii RVZ not present",
}


def validate_backend_summary(payload):
    """Keep existing missing-fixture skips distinct from passing tests."""
    if payload.get("full_suite") is not True or payload.get("tests", 0) < 500:
        raise RuntimeError("missing full backend suite")
    for key in ("tests", "failures", "errors", "skipped"):
        if type(payload.get(key)) is not int or payload[key] < 0:
            raise RuntimeError("invalid backend test counts")
    if payload["failures"] or payload["errors"]:
        raise RuntimeError("backend suite has failures or errors")
    rows = payload.get("skip_details", [])
    if not isinstance(rows, list) or len(rows) != payload["skipped"]:
        raise RuntimeError("backend skip count mismatch")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("invalid backend skip record")
        nodeid = row.get("nodeid")
        if (
            nodeid not in RVZ_SKIPS
            or row.get("reason") != RVZ_SKIPS[nodeid]
            or nodeid in seen
        ):
            raise RuntimeError("unregistered or duplicate backend skip")
        seen.add(nodeid)
    if payload["skipped"] > payload["tests"]:
        raise RuntimeError("backend skip count exceeds tests")


def backend_xml(path, selected):
    """Read bounded JUnit records and bind every case to its selected module."""
    import xml.etree.ElementTree as ET  # nosec B405, declarations rejected below

    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000:
        raise RuntimeError("missing or unsafe backend XML")
    content = path.read_bytes()
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise RuntimeError("backend XML declarations are forbidden")
    try:
        root = ET.fromstring(content)  # nosec B314, bounded declaration-free XML
    except ET.ParseError as error:
        raise RuntimeError("invalid backend XML") from error
    suites = list(root.iter("testsuite"))
    if not suites:
        raise RuntimeError("missing backend XML suites")
    counts = dict.fromkeys(("tests", "failures", "errors", "skipped"), 0)
    skips = []
    seen = set()
    for suite in suites:
        cases = list(suite.findall("testcase"))
        actual = {
            "tests": len(cases),
            "failures": sum(case.find("failure") is not None for case in cases),
            "errors": sum(case.find("error") is not None for case in cases),
            "skipped": sum(case.find("skipped") is not None for case in cases),
        }
        if any(suite.get(key) != str(value) for key, value in actual.items()):
            raise RuntimeError("backend XML count mismatch")
        for key, value in actual.items():
            counts[key] += value
        for case in cases:
            classname = case.get("classname", "")
            modules = [
                name
                for name in selected
                if classname == name[:-3].replace("/", ".")
                or classname.startswith(name[:-3].replace("/", ".") + ".")
            ]
            if len(modules) != 1 or not case.get("name"):
                raise RuntimeError("backend XML case outside selected files")
            module = modules[0]
            suffix = classname[len(module[:-3].replace("/", ".")) :].strip(".")
            nodeid = "::".join(
                filter(None, (module, suffix.replace(".", "::"), case.get("name")))
            )
            if nodeid in seen:
                raise RuntimeError("duplicate backend XML case")
            seen.add(nodeid)
            skipped = case.find("skipped")
            if skipped is not None:
                skips.append({"nodeid": nodeid, "reason": skipped.get("message")})
    if not counts["tests"] or counts["failures"] or counts["errors"]:
        raise RuntimeError("empty or failed backend XML")
    return {**counts, "skip_details": skips}


def validate_backend_shards(payload, evidence, artifacts):
    """Require the supported eight-shard CI union and its actual retained proof."""
    import phase34
    from ci_target import SHARDS, shard_files, tracked_test_files
    from phase36_receipts import child, clean, read, sources

    names = payload.get("shards", [])
    if len(names) != SHARDS or len(set(names)) != SHARDS:
        raise RuntimeError("missing or duplicate backend shards")
    expected = tracked_test_files(phase34.REPO)
    if not expected or len(set(expected)) != len(expected):
        raise RuntimeError("invalid backend file inventory")
    total = dict.fromkeys(("tests", "failures", "errors", "skipped"), 0)
    skips = []
    covered = []
    numbers = set()
    baseline = read(evidence / "code-before.json")
    required = {
        "backend.xml",
        "ci-result.json",
        "commands.json",
        "cleanup.json",
        "code-before.json",
        "shard-files.json",
    }
    for name in names:
        folder = child(evidence, name)
        if not {name + "/" + item for item in required}.issubset(artifacts):
            raise RuntimeError("unindexed backend shard artifact")
        metadata = read(folder / "shard-files.json")
        number = metadata.get("shard")
        if type(number) is not int or number in numbers or not 1 <= number <= SHARDS:
            raise RuntimeError("invalid backend shard number")
        numbers.add(number)
        selected = shard_files(expected, number)
        if metadata != {
            "shard": number,
            "shards": SHARDS,
            "all_files": expected,
            "selected_files": selected,
        }:
            raise RuntimeError("backend shard file union mismatch")
        covered.extend(selected)
        result = read(folder / "ci-result.json")
        if result != {
            "gate": "pytest",
            "dialect": payload.get("dialect"),
            "passed": True,
        }:
            raise RuntimeError("failed backend shard or wrong dialect")
        clean(read(folder / "cleanup.json"))
        sources(read(folder / "code-before.json"), baseline)
        commands = read(folder / "commands.json")
        if not commands or any(row.get("exit") != 0 for row in commands):
            raise RuntimeError("failed backend shard command")
        executions = [
            row["command"] for row in commands if "pytest" in row.get("command", [])
        ]
        if len(executions) != 1:
            raise RuntimeError("missing unique backend shard execution")
        args = executions[0][executions[0].index("pytest") + 1 :]
        if [
            arg for arg in args if arg.endswith(".py")
        ] != selected or "--junitxml=/phase34/evidence/backend.xml" not in args:
            raise RuntimeError("backend command did not execute selected files")
        if any(
            arg
            in {
                "-k",
                "-m",
                "--lf",
                "--ff",
                "--collect-only",
                "--ignore",
                "--deselect",
                "-x",
                "--maxfail",
            }
            or arg.startswith(("--ignore=", "--deselect=", "--maxfail="))
            for arg in args
        ):
            raise RuntimeError("backend command narrowed the complete shard")
        actual = backend_xml(folder / "backend.xml", selected)
        for key in total:
            total[key] += actual[key]
        skips.extend(actual["skip_details"])
    if sorted(covered) != expected or len(covered) != len(set(covered)):
        raise RuntimeError("incomplete or overlapping backend suite")
    if (
        any(payload.get(key) != value for key, value in total.items())
        or payload.get("skip_details") != skips
    ):
        raise RuntimeError("backend rollup differs from actual XML")
    validate_backend_summary({**total, "full_suite": True, "skip_details": skips})
