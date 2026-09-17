from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from decorators.database import begin_session
from models.download_archive_set import DownloadArchiveSet, DownloadArchiveSetMember
from models.rom import Rom, RomComponent, RomComponentManifestMember

from .base_handler import DBBaseHandler

MAX_ARCHIVE_SETS = 100
MAX_ARCHIVE_SET_MEMBERS = 100


class ArchiveSetMemberInput(TypedDict):
    component_id: int
    manifest_member_id: int
    required: bool


class DBDownloadArchiveSetsHandler(DBBaseHandler):
    """Persist explicit ROM-owned archive policies without source heuristics."""

    def _validate_members(
        self,
        session: Session,
        rom_id: int,
        members: Sequence[ArchiveSetMemberInput],
    ) -> list[DownloadArchiveSetMember]:
        if not members or len(members) > MAX_ARCHIVE_SET_MEMBERS:
            raise ValueError("archive set must contain between 1 and 100 members")
        identities = [
            (item["component_id"], item["manifest_member_id"]) for item in members
        ]
        if len(set(identities)) != len(identities):
            raise ValueError("archive set members must be unique")
        component_ids = {component_id for component_id, _ in identities}
        member_ids = {member_id for _, member_id in identities}
        components = {
            component.id: component
            for component in session.scalars(
                select(RomComponent)
                .where(
                    RomComponent.rom_id == rom_id, RomComponent.id.in_(component_ids)
                )
                .with_for_update()
            )
        }
        source_members = {
            member.id: member
            for member in session.scalars(
                select(RomComponentManifestMember)
                .where(RomComponentManifestMember.id.in_(member_ids))
                .with_for_update()
            )
        }
        if len(components) != len(component_ids) or len(source_members) != len(
            member_ids
        ):
            raise ValueError("archive set references unavailable ROM content")
        result: list[DownloadArchiveSetMember] = []
        for position, item in enumerate(members):
            component_id = item["component_id"]
            member_id = item["manifest_member_id"]
            source_member = source_members[member_id]
            if source_member.component_id != component_id:
                raise ValueError("archive set member does not belong to its component")
            result.append(
                DownloadArchiveSetMember(
                    component_id=component_id,
                    manifest_member_id=member_id,
                    position=position,
                    required=bool(item["required"]),
                )
            )
        return result

    @begin_session
    def list_for_rom(self, rom_id: int, session: Session = None):  # type: ignore
        return list(
            session.scalars(
                select(DownloadArchiveSet)
                .where(DownloadArchiveSet.rom_id == rom_id)
                .options(selectinload(DownloadArchiveSet.members))
                .order_by(DownloadArchiveSet.id)
            )
        )

    @begin_session
    def create(
        self,
        rom_id: int,
        name: str,
        members: Sequence[ArchiveSetMemberInput],
        session: Session = None,  # type: ignore
    ) -> DownloadArchiveSet:
        if not name or len(name) > 450 or not name.strip():
            raise ValueError("archive set name is invalid")
        rom = session.scalar(select(Rom).where(Rom.id == rom_id).with_for_update())
        if rom is None:
            raise ValueError("archive set ROM is unavailable")
        if session.scalar(
            select(DownloadArchiveSet.id).where(
                DownloadArchiveSet.rom_id == rom_id, DownloadArchiveSet.name == name
            )
        ):
            raise ValueError("archive set name already exists")
        archive_set = DownloadArchiveSet(rom_id=rom_id, name=name)
        archive_set.members = self._validate_members(session, rom_id, members)
        session.add(archive_set)
        session.flush()
        return archive_set

    @begin_session
    def replace(
        self,
        rom_id: int,
        archive_set_id: int,
        name: str,
        members: Sequence[ArchiveSetMemberInput],
        session: Session = None,  # type: ignore
    ) -> DownloadArchiveSet | None:
        archive_set = session.scalar(
            select(DownloadArchiveSet)
            .where(
                DownloadArchiveSet.id == archive_set_id,
                DownloadArchiveSet.rom_id == rom_id,
            )
            .with_for_update()
        )
        if archive_set is None:
            return None
        duplicate = session.scalar(
            select(DownloadArchiveSet.id).where(
                DownloadArchiveSet.rom_id == rom_id,
                DownloadArchiveSet.name == name,
                DownloadArchiveSet.id != archive_set_id,
            )
        )
        if duplicate:
            raise ValueError("archive set name already exists")
        archive_set.name = name
        archive_set.members = self._validate_members(session, rom_id, members)
        session.flush()
        return archive_set

    @begin_session
    def import_sets(
        self,
        rom_id: int,
        definitions: Sequence[tuple[str, Sequence[ArchiveSetMemberInput]]],
        session: Session = None,  # type: ignore
    ) -> list[DownloadArchiveSet]:
        if not definitions or len(definitions) > MAX_ARCHIVE_SETS:
            raise ValueError("archive set import is bounded")
        names = [name for name, _ in definitions]
        if len(names) != len(set(names)):
            raise ValueError("archive set names must be unique")
        if (
            session.scalar(select(Rom.id).where(Rom.id == rom_id).with_for_update())
            is None
        ):
            raise ValueError("archive set ROM is unavailable")
        existing = list(
            session.scalars(
                select(DownloadArchiveSet).where(DownloadArchiveSet.rom_id == rom_id)
            )
        )
        for archive_set in existing:
            if archive_set.name in names:
                session.delete(archive_set)
        result = []
        for name, members in definitions:
            archive_set = DownloadArchiveSet(rom_id=rom_id, name=name)
            archive_set.members = self._validate_members(session, rom_id, members)
            session.add(archive_set)
            result.append(archive_set)
        session.flush()
        return result
