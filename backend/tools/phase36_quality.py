"""Final serial frontend quality, using the existing guarded quality owner."""

from phase35_browser_quality import execute_quality

__all__ = ["execute_quality"]


RVZ_SKIPS = {
    "tests/utils/test_rvz_hasher.py::test_real_gamecube_rvz_matches_retroachievements_hash": "mock GameCube RVZ not present",
    "tests/utils/test_rvz_hasher.py::test_real_wii_rvz_matches_retroachievements_hash": "mock Wii RVZ not present",
}


ROOT_PERMISSION_NODE = "tests/handler/filesystem/test_roms_handler.py::TestExtractCHDHash::test_extract_chd_hash_permission_error"
ROOT_PERMISSION_REASON = "root bypasses file permission bits"
ROOT_ENVIRONMENT = {"runner_config_user": "", "pytest_exec_user": "default"}


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
            nodeid == ROOT_PERMISSION_NODE
            and row.get("reason") == ROOT_PERMISSION_REASON
            and row.get("environment") == ROOT_ENVIRONMENT
            and nodeid not in seen
        ):
            seen.add(nodeid)
            continue
        if (
            nodeid not in RVZ_SKIPS
            or row.get("reason") != RVZ_SKIPS[nodeid]
            or nodeid in seen
        ):
            raise RuntimeError("unregistered or duplicate backend skip")
        seen.add(nodeid)
    if payload["skipped"] > payload["tests"]:
        raise RuntimeError("backend skip count exceeds tests")


def pytest_terminal(path):
    """Read the exact completed command's terminal outcome counters."""
    import re

    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000:
        raise RuntimeError("missing or unsafe pytest command log")
    text = re.sub(r"\x1b\[[0-9;]*m", "", path.read_text())
    summaries = re.findall(r"^=+\s*(.*?)\s+in\s+[0-9.]+s.*?=+$", text, re.MULTILINE)
    if len(summaries) != 1:
        raise RuntimeError("missing unique completed pytest summary")
    summary = summaries[0]
    if any(
        word in summary
        for word in ("failed", "error", "xpassed", "deselected", "rerun")
    ):
        raise RuntimeError("unsuccessful or narrowed pytest summary")

    def counter(label):
        matches = re.findall(r"(?:^|, )(\d+) " + label + r"(?:,|$)", summary)
        if len(matches) > 1:
            raise RuntimeError("duplicate pytest outcome counter")
        return int(matches[0]) if matches else 0

    return {
        "passed": counter("passed"),
        "skipped": counter("skipped"),
        "subtests_passed": counter("subtests passed"),
    }


def backend_xml(path, selected, output=None):
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
    counts = dict.fromkeys(
        ("tests", "failures", "errors", "skipped", "junit_tests", "subtests_passed"), 0
    )
    terminal = pytest_terminal(output) if output is not None else None
    if len(suites) != 1:
        raise RuntimeError("unexpected multiple pytest XML suites")
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
        if any(
            suite.get(key) != str(actual[key])
            for key in ("failures", "errors", "skipped")
        ):
            raise RuntimeError("backend XML count mismatch")
        try:
            declared = int(suite.get("tests", "-1"))
        except ValueError as error:
            raise RuntimeError("invalid backend XML test count") from error
        subtests = terminal["subtests_passed"] if terminal is not None else 0
        if declared != actual["tests"] + subtests:
            raise RuntimeError("backend XML test/subtest count mismatch")
        if terminal is not None and (
            terminal["passed"]
            != actual["tests"]
            - actual["skipped"]
            - actual["failures"]
            - actual["errors"]
            or terminal["skipped"] != actual["skipped"]
        ):
            raise RuntimeError("pytest terminal differs from actual XML")
        counts["subtests_passed"] = subtests
        counts["junit_tests"] = declared
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


def root_skip_environment(commands, folder, artifacts, prefix):
    """Bind the inherited root-only skip to inspected runner and exec defaults."""
    from phase36_receipts import child, read

    pytest = [row["command"] for row in commands if "pytest" in row.get("command", [])]
    if (
        len(pytest) != 1
        or "exec" not in pytest[0]
        or any(
            arg in {"--user", "-u"} or arg.startswith("--user=") for arg in pytest[0]
        )
    ):
        raise RuntimeError("root permission skip lacks default exec-user evidence")
    users = []
    for row in commands:
        argv = row.get("command", [])
        if argv[:2] != ["docker", "inspect"] and argv[:3] != [
            "docker",
            "container",
            "inspect",
        ]:
            continue
        log = row.get("log")
        if not isinstance(log, str) or prefix + "/" + log not in artifacts:
            raise RuntimeError("unindexed runner inspection")
        inspection = read(child(folder, log))
        if not isinstance(inspection, list):
            raise RuntimeError("invalid runner inspection")
        for inspected in inspection:
            if str(inspected.get("Name", "")).endswith("-runner-1"):
                users.append(inspected.get("Config", {}).get("User"))
    if not users or any(user != "" for user in users):
        raise RuntimeError("root permission skip lacks inspected root runner")
    return ROOT_ENVIRONMENT.copy()


def shard_source_delta(tested, baseline, number, selected, recorded):
    """Keep reviewed seed-group source changes explicit and bounded."""
    reviewed_tools = {
        1: {
            "tools/tests/test_phase33_uat.py",
            "tools/tests/test_phase35_incremental_scan_probe.py",
        },
        2: {
            "tools/tests/test_phase34_evidence.py",
            "tools/tests/test_phase36_description_probe.py",
        },
    }
    allowed = (
        {
            "backend/tools/phase36_quality.py",
            "backend/tools/tests/test_phase36_receipts.py",
        }
        if number in reviewed_tools
        and {name for name in selected if name.startswith("tools/")}
        == reviewed_tools[number]
        else set()
    )
    fixture = "backend/tests/endpoints/test_storage_policy_denials.py"
    if allowed and fixture.removeprefix("backend/") not in selected:
        allowed.add(fixture)
    before, after = tested.get("files", {}), baseline.get("files", {})
    delta = [
        {
            "file": name,
            "tested": before.get(name),
            "current": after.get(name),
            "reason": (
                "unselected_unimported_storage_policy_fixture_alignment"
                if name == fixture
                else "evidence_gate_only_outside_reviewed_shard_imports"
            ),
        }
        for name in sorted(set(before) | set(after))
        if before.get(name) != after.get(name)
    ]
    if any(row["file"] not in allowed for row in delta) or recorded != delta:
        raise RuntimeError("relevant or unexplained backend shard source delta")


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
    total = dict.fromkeys(
        ("tests", "failures", "errors", "skipped", "junit_tests", "subtests_passed"), 0
    )
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
        tested = read(folder / "code-before.json")
        sources(tested, None)
        shard_source_delta(
            tested,
            baseline,
            number,
            selected,
            payload.get("shard_source_deltas", {}).get(name, []),
        )
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
        execution = next(row for row in commands if row["command"] == executions[0])
        log = execution.get("log")
        if not isinstance(log, str) or name + "/" + log not in artifacts:
            raise RuntimeError("missing indexed pytest command log")
        actual = backend_xml(folder / "backend.xml", selected, child(folder, log))
        if any(row["nodeid"] == ROOT_PERMISSION_NODE for row in actual["skip_details"]):
            environment = root_skip_environment(commands, folder, artifacts, name)
            for row in actual["skip_details"]:
                if row["nodeid"] == ROOT_PERMISSION_NODE:
                    row["environment"] = environment
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
