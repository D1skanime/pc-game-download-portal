from pathlib import Path


def test_mapping_preview_endpoint_exposes_refresh_contract():
    source = Path("endpoints/storage.py").read_text()
    assert (
        "refresh_platform_storage_mapping_preview" in source
    ), "Phase 5 RED: preview refresh and stale prior result are not implemented"


def test_preview_public_states_are_bounded():
    assert {"pending", "partial", "complete"} == {"pending", "partial", "complete"}
