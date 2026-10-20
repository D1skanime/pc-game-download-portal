import pytest
from tests.conftest import session

from handler.database.download_archive_sets_handler import DBDownloadArchiveSetsHandler
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


def _component(rom_id: int, suffix: str) -> RomComponent:
    return RomComponent(
        rom_id=rom_id,
        relative_path=f"component-{suffix}",
        kind=RomComponentKind.BASE,
        manifest_members=[
            RomComponentManifestMember(
                relative_path=f"component-{suffix}/content.bin",
                size_bytes=10,
                sha256="a" * 64,
            )
        ],
    )


def test_handler_creates_replaces_and_imports_exact_members(admin_user, rom):
    first, second = _component(rom.id, "first"), _component(rom.id, "second")
    with session.begin() as db:
        db.add_all([first, second])
    handler = DBDownloadArchiveSetsHandler()
    created = handler.create(
        rom.id,
        "whole-game",
        [
            {
                "component_id": first.id,
                "manifest_member_id": first.manifest_members[0].id,
                "required": True,
            }
        ],
    )
    assert [(member.position, member.required) for member in created.members] == [
        (0, True)
    ]
    replaced = handler.replace(
        rom.id,
        created.id,
        "whole-game",
        [
            {
                "component_id": second.id,
                "manifest_member_id": second.manifest_members[0].id,
                "required": False,
            }
        ],
    )
    assert replaced.members[0].component_id == second.id
    assert replaced.members[0].required is False
    imported = handler.import_sets(
        rom.id,
        [
            (
                "updates",
                [
                    {
                        "component_id": first.id,
                        "manifest_member_id": first.manifest_members[0].id,
                        "required": True,
                    }
                ],
            )
        ],
    )
    assert [archive_set.name for archive_set in imported] == ["updates"]


def test_handler_rejects_duplicate_foreign_and_mismatched_members(admin_user, rom):
    component = _component(rom.id, "valid")
    with session.begin() as db:
        db.add(component)
    handler = DBDownloadArchiveSetsHandler()
    member = component.manifest_members[0]
    payload = {
        "component_id": component.id,
        "manifest_member_id": member.id,
        "required": True,
    }
    with pytest.raises(ValueError):
        handler.create(rom.id, "bad", [payload, payload])
    with pytest.raises(ValueError):
        handler.create(rom.id, "bad", [{**payload, "component_id": 999999}])


def test_handler_replaces_existing_identities_in_new_positions(admin_user, rom):
    first, second = _component(rom.id, "first"), _component(rom.id, "second")
    with session.begin() as db:
        db.add_all([first, second])
    handler = DBDownloadArchiveSetsHandler()
    members = [
        {
            "component_id": component.id,
            "manifest_member_id": component.manifest_members[0].id,
            "required": True,
        }
        for component in (first, second)
    ]
    created = handler.create(rom.id, "whole-game", members)
    replacement = [{**member, "required": False} for member in reversed(members)]
    handler.replace(rom.id, created.id, "reordered", replacement)

    [persisted] = handler.list_for_rom(rom.id)
    assert persisted.name == "reordered"
    assert [
        (
            member.component_id,
            member.manifest_member_id,
            member.position,
            member.required,
        )
        for member in persisted.members
    ] == [
        (member["component_id"], member["manifest_member_id"], position, False)
        for position, member in enumerate(replacement)
    ]
