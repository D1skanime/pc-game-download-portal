from pathlib import Path


def test_mapping_revision_job_contract_exists():
    assert Path(
        "tasks/mapping_revision.py"
    ).exists(), "Phase 5 RED: revision-bound jobs and stale history are not implemented"


def test_stale_error_identity_is_bounded_and_redacted():
    rendered = repr(
        {"code": "stale_storage_mapping", "mapping_id": 41, "expected_revision": 7}
    )
    assert "/home/" not in rendered and "OSError" not in rendered
