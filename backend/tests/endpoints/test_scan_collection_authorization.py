"""Collection promotion requires the existing catalog deletion permission."""

from tests.endpoints.test_scan_operations import (
    BASE,
)
from tests.endpoints.test_scan_operations import mapped as mapped_fixture  # noqa: F401
from tests.endpoints.test_scan_operations import other_headers as other_headers_fixture
from tests.endpoints.test_scan_operations import (
    request_body,
)
from tests.handler.test_scan_collection_policy import (
    promotion_body as promotion_body_fixture,
)

promotion_body = promotion_body_fixture
mapped = mapped_fixture
other_headers = other_headers_fixture


def test_task_runner_without_catalog_delete_cannot_promote(
    client, other_headers, mapped
):
    body = request_body(
        mapped,
        apis=[],
        filesystem_scope_paths={"test_platform_slug": "soundtracks"},
        collection_promotion={
            "parent_rom_id": 1,
            "mapping_id": mapped.id,
            "expected_revision": mapped.version,
            "parent_relative_path": "Parent",
            "selected_child_relative_path": "Parent/soundtracks",
        },
    )
    response = client.post(BASE, headers=other_headers, json=body)
    assert response.status_code == 403


def test_task_runner_can_still_submit_generic_discovery(client, other_headers, mapped):
    response = client.post(
        BASE, headers=other_headers, json=request_body(mapped, apis=[])
    )
    assert response.status_code == 202


def test_revoked_catalog_delete_also_blocks_existing_promotion_replay(
    client, other_headers, viewer_user, promotion_body
):
    from handler.database import db_permission_handler
    from models.permission import PermAction, PermEntity

    db_permission_handler.replace_user_overrides(
        viewer_user.id,
        [
            (PermEntity.TASKS, PermAction.WRITE, True, False),
            (PermEntity.ROMS, PermAction.DELETE, True, False),
        ],
    )
    accepted = client.post(BASE, headers=other_headers, json=promotion_body)
    assert accepted.status_code == 202
    db_permission_handler.replace_user_overrides(
        viewer_user.id,
        [
            (PermEntity.TASKS, PermAction.WRITE, True, False),
        ],
    )
    replay = client.post(BASE, headers=other_headers, json=promotion_body)
    assert replay.status_code == 403
