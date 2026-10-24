"""One complete backend test selection, partitioned by execution prerequisites."""

import fnmatch
from pathlib import PurePosixPath

HOST_TEST_FILES = (
    "tools/tests/test_phase38_metadata.py",
    "tools/tests/test_phase38_operator_docs.py",
    "tools/tests/test_phase38_publication.py",
    "tools/tests/test_phase38_verifiers.py",
)


def select_test_files(paths, patterns):
    return sorted(
        path.removeprefix("backend/")
        for path in paths
        if path.startswith("backend/")
        and any(fnmatch.fnmatchcase(PurePosixPath(path).name, p) for p in patterns)
    )


def classify_test_files(files):
    """Fail when configuration drops a required full-checkout contract suite."""
    if len(set(files)) != len(files) or not set(HOST_TEST_FILES).issubset(files):
        raise RuntimeError("incomplete or duplicate test profile selection")
    all_files = sorted(files)
    host = list(HOST_TEST_FILES)
    sql = [path for path in all_files if path not in HOST_TEST_FILES]
    if set(sql) & set(host) or sorted(sql + host) != all_files:
        raise RuntimeError("test profile partition mismatch")
    return {"all": all_files, "sql": sql, "host": host}
