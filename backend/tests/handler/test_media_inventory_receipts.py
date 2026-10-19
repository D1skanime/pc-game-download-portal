"""Receipt byte budgets and schema compatibility use actual owned recovery."""

import pytest
from tests.handler.media_download_helpers import (
    owned_resource_files as owned_resource_files,
)
from tests.handler.media_recovery_helpers import drain_until
from tests.handler.test_media_inventory import assert_bounded_receipts
from tests.handler.test_media_recovery_validation import orphan, replace_receipt, stop
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_media_publication import read
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_inventory import ScanMediaInventory
from handler.filesystem.scan_media_publication import MAX_MANIFEST_BYTES
from handler.filesystem.scan_media_recovery import reconcile_manifest


@pytest.mark.asyncio
async def test_long_output_paths_roll_receipts_before_byte_limit(
    attempt, rom, admin_user
):
    directory = rom.fs_resources_path + "/" + "/".join(["segment" * 12] * 10)
    with bind_scan_write_context(context(attempt)):
        with ScanMediaInventory(
            rom.id, rom.platform_id, fs_resource_handler.storage, output_limit=150
        ) as unit:
            paths = []
            for i in range(150):
                output = unit.prepare(f"{directory}/{i}.png")
                output.file.write(b"complete bytes")
                unit.finish(output)
                paths.append(output.path)
            assert len(unit.batches) >= 3
            assert all(len(part.outputs) < 128 for part in unit.batches)
            unit.publish_and_associate(
                lambda session: db_rom_handler.update_rom(
                    rom.id, {"path_screenshots": paths}, session=session
                )
            )
    assert db_rom_handler.get_rom(rom.id).path_screenshots == paths
    assert all(read(path) == b"complete bytes" for path in paths)
    assert assert_bounded_receipts(attempt) >= 3
    stop(attempt, admin_user)
    root = fs_resource_handler.validate_path(
        f".scan-media-staging/{attempt.id}/{attempt.attempt_id}"
    )
    await drain_until(lambda: not root.exists())
    assert all(read(path) == b"complete bytes" for path in paths)


def test_legacy_schema_one_receipt_still_recovers_exact_output(
    attempt, rom, admin_user
):
    unit, output = orphan(attempt, rom)
    replace_receipt(unit, lambda document: document.update(schema=1, expected_prior=[]))
    stop(attempt, admin_user)
    assert reconcile_manifest(unit.storage, unit.manifest_directory)
    assert not fs_resource_handler.validate_path(output.path).exists()


@pytest.mark.parametrize(
    "prior",
    [
        {"count": True, "sha256": "a" * 64},
        {"count": -1, "sha256": "a" * 64},
        {"count": 1, "sha256": 7},
        {"count": 1, "sha256": "a" * 63},
        {"count": 1, "sha256": "a" * 64, "foreign": []},
    ],
)
def test_schema_two_fingerprint_cannot_bypass_evidence_validation(
    attempt, rom, admin_user, prior
):
    unit, output = orphan(attempt, rom)
    receipt, original = replace_receipt(
        unit, lambda document: document.update(schema=2, expected_prior=prior)
    )
    assert len(original) < MAX_MANIFEST_BYTES
    stop(attempt, admin_user)
    with pytest.raises(ValueError, match="scan_media_manifest"):
        reconcile_manifest(unit.storage, unit.manifest_directory)
    assert receipt.read_bytes() == original
    assert read(output.path) == b"stopped orphan"
