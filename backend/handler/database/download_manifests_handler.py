from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from config import DOWNLOAD_MANIFEST_TTL_SECONDS
from decorators.database import begin_session
from models.download_archive_set import DownloadArchiveSet, DownloadArchiveSetMember
from models.download_manifest import (
    DownloadManifest,
    DownloadManifestComponent,
    DownloadManifestMember,
    DownloadManifestStatus,
)
from models.rom import Rom, RomComponent, RomComponentKind, RomComponentManifestMember
from utils.datetime import to_utc

from .base_handler import DBBaseHandler

if TYPE_CHECKING:
    from handler.filesystem.roms_handler import (
        DownloadManifestMemberEvidence,
    )


ELIGIBLE_COMPONENT_KINDS = frozenset(
    {
        RomComponentKind.BASE,
        RomComponentKind.UPDATE,
        RomComponentKind.DLC,
        RomComponentKind.EXTRA,
    }
)


class ManifestFilesystem(Protocol):
    def capture_download_manifest_member(
        self, rom: Rom, member: RomComponentManifestMember, public_id: str
    ) -> DownloadManifestMemberEvidence: ...

    def light_revalidate_download_manifest_member(
        self, rom: Rom, member: RomComponentManifestMember, evidence: object
    ) -> str: ...


class DBDownloadManifestsHandler(DBBaseHandler):
    """Create and evaluate path-free immutable download aggregates."""

    def __init__(self, filesystem_handler: ManifestFilesystem | None = None) -> None:
        self._filesystem_handler = filesystem_handler

    @property
    def filesystem_handler(self) -> ManifestFilesystem:
        if self._filesystem_handler is None:
            from handler.filesystem.roms_handler import FSRomsHandler

            self._filesystem_handler = FSRomsHandler()
        return self._filesystem_handler

    @begin_session
    def create_manifest(
        self,
        user_id: int,
        rom_id: int,
        component_ids: Sequence[int] | None,
        archive_set_id: int | None = None,
        selected_member_ids: Sequence[int] | None = None,
        session: Session = None,  # type: ignore
    ) -> DownloadManifest:
        if component_ids is not None:
            if not component_ids or any(
                not isinstance(component_id, int) or component_id <= 0
                for component_id in component_ids
            ):
                raise ValueError("invalid manifest component selection")
            if len(set(component_ids)) != len(component_ids):
                raise ValueError("duplicate manifest component selection")
        if archive_set_id is not None and (
            not isinstance(archive_set_id, int) or archive_set_id <= 0
        ):
            raise ValueError("invalid manifest archive set selection")
        if selected_member_ids is not None:
            if (
                not selected_member_ids
                or any(
                    not isinstance(member_id, int) or member_id <= 0
                    for member_id in selected_member_ids
                )
                or len(set(selected_member_ids)) != len(selected_member_ids)
            ):
                raise ValueError("invalid manifest member selection")
        if archive_set_id is not None and component_ids is not None:
            raise ValueError("manifest policy selection cannot include components")

        rom = session.scalar(select(Rom).where(Rom.id == rom_id).with_for_update())
        if rom is None:
            raise ValueError("manifest ROM is unavailable")

        policy_members: list[DownloadArchiveSetMember] | None = None
        if archive_set_id is not None:
            policy_members = list(
                session.scalars(
                    select(DownloadArchiveSetMember)
                    .where(
                        DownloadArchiveSetMember.archive_set_id == archive_set_id,
                    )
                    .order_by(DownloadArchiveSetMember.position)
                    .with_for_update()
                )
            )
            if not policy_members:
                raise ValueError("manifest archive set is unavailable")
            policy_rom_id = session.scalar(
                select(DownloadArchiveSet.id)
                .where(
                    DownloadArchiveSet.id == archive_set_id,
                    DownloadArchiveSet.rom_id == rom_id,
                )
                .with_for_update()
            )
            if policy_rom_id is None:
                raise ValueError("manifest archive set is unavailable")
            if selected_member_ids is None:
                raise ValueError("manifest archive set selection is required")
            selected_ids = set(selected_member_ids)
            required_ids = {
                member.manifest_member_id
                for member in policy_members
                if member.required
            }
            allowed_ids = {member.manifest_member_id for member in policy_members}
            if not required_ids.issubset(selected_ids) or not selected_ids.issubset(
                allowed_ids
            ):
                raise ValueError("manifest archive set selection is incomplete")
            selected_policy_members = [
                member
                for member in policy_members
                if member.manifest_member_id in selected_ids
            ]
            selected_component_ids = list(
                dict.fromkeys(member.component_id for member in selected_policy_members)
            )
            components = list(
                session.scalars(
                    select(RomComponent)
                    .where(
                        RomComponent.rom_id == rom_id,
                        RomComponent.id.in_(selected_component_ids),
                        RomComponent.kind.in_(ELIGIBLE_COMPONENT_KINDS),
                    )
                    .with_for_update()
                )
            )
            components_by_id = {component.id: component for component in components}
            if len(components_by_id) != len(set(selected_component_ids)):
                raise ValueError("manifest archive set components are unavailable")
            source_ids = [
                member.manifest_member_id for member in selected_policy_members
            ]
            member_rows = list(
                session.scalars(
                    select(RomComponentManifestMember)
                    .where(
                        RomComponentManifestMember.id.in_(source_ids),
                        RomComponentManifestMember.missing_from_fs.is_(False),
                    )
                    .with_for_update()
                )
            )
            members_by_id = {member.id: member for member in member_rows}
            if len(members_by_id) != len(source_ids) or any(
                members_by_id[member.manifest_member_id].component_id
                != member.component_id
                for member in selected_policy_members
            ):
                raise ValueError("manifest archive set members are unavailable")
            components = [
                components_by_id[component_id]
                for component_id in selected_component_ids
            ]
            member_rows = [
                members_by_id[member.manifest_member_id]
                for member in selected_policy_members
            ]
        else:
            statement = (
                select(RomComponent)
                .where(
                    RomComponent.rom_id == rom_id,
                    RomComponent.kind.in_(ELIGIBLE_COMPONENT_KINDS),
                )
                .order_by(RomComponent.id)
                .with_for_update()
            )
            if component_ids is not None:
                statement = statement.where(RomComponent.id.in_(component_ids))
            components = list(session.scalars(statement))
            if not components or (
                component_ids is not None and len(components) != len(component_ids)
            ):
                raise ValueError("manifest components are unavailable")

            member_rows = list(
                session.scalars(
                    select(RomComponentManifestMember)
                    .where(
                        RomComponentManifestMember.component_id.in_(
                            component.id for component in components
                        ),
                        RomComponentManifestMember.missing_from_fs.is_(False),
                    )
                    .order_by(RomComponentManifestMember.id)
                    .with_for_update()
                )
            )
            if selected_member_ids is not None:
                selected_ids = set(selected_member_ids)
                allowed_ids = {member.id for member in member_rows}
                if not selected_ids.issubset(allowed_ids):
                    raise ValueError("manifest member selection is unavailable")
                member_rows = [
                    member for member in member_rows if member.id in selected_ids
                ]
                components = [
                    component
                    for component in components
                    if any(
                        member.component_id == component.id for member in member_rows
                    )
                ]
                if not components:
                    raise ValueError("manifest member selection is empty")
        members_by_component: dict[int, list[RomComponentManifestMember]] = {
            component.id: [] for component in components
        }
        for member in member_rows:
            members_by_component[member.component_id].append(member)
        if archive_set_id is None and any(
            not members_by_component[component.id] for component in components
        ):
            raise ValueError("manifest components need source members")

        manifest = DownloadManifest(
            user_id=user_id,
            rom_id=rom.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=DOWNLOAD_MANIFEST_TTL_SECONDS),
        )
        selected_components = {
            component.id: DownloadManifestComponent(component=component)
            for component in components
        }
        manifest.components = list(selected_components.values())
        for component in components:
            selected_members = (
                members_by_component[component.id]
                if archive_set_id is None
                else [
                    member
                    for member in member_rows
                    if member.component_id == component.id
                ]
            )
            for member in selected_members:
                if (
                    member.size_bytes < 0
                    or len(member.sha256) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in member.sha256
                    )
                ):
                    raise ValueError("manifest member hash evidence is unavailable")
                pending_member = DownloadManifestMember(
                    public_id=str(uuid4()),
                    component_id=component.id,
                    manifest_member=member,
                )
                selected_components[component.id].members.append(pending_member)
                evidence = self.filesystem_handler.capture_download_manifest_member(
                    rom, member, pending_member.public_id
                )
                pending_member.destination = evidence.destination
                pending_member.size_bytes = evidence.size_bytes
                pending_member.sha256 = evidence.sha256
                pending_member.snapshot = evidence.snapshot
                pending_member.mtime_ns = evidence.mtime_ns
                pending_member.device = evidence.device
                pending_member.inode = evidence.inode
        session.add(manifest)
        session.flush()
        return manifest

    @begin_session
    def get_manifest(
        self,
        manifest_id: str,
        user_id: int,
        session: Session = None,  # type: ignore
    ) -> DownloadManifest | None:
        manifest = session.scalar(
            select(DownloadManifest)
            .options(
                selectinload(DownloadManifest.rom),
                selectinload(DownloadManifest.components)
                .joinedload(DownloadManifestComponent.component)
                .joinedload(RomComponent.rom),
                selectinload(DownloadManifest.components)
                .selectinload(DownloadManifestComponent.members)
                .joinedload(DownloadManifestMember.manifest_member),
            )
            .where(
                DownloadManifest.id == manifest_id,
                DownloadManifest.user_id == user_id,
            )
        )
        if manifest is None or manifest.status is not DownloadManifestStatus.VALID:
            return manifest
        if datetime.now(timezone.utc) >= to_utc(manifest.expires_at):
            manifest.status = DownloadManifestStatus.EXPIRED
            return manifest
        for component in manifest.components:
            for member in component.members:
                if (
                    self.filesystem_handler.light_revalidate_download_manifest_member(
                        component.component.rom, member.manifest_member, member
                    )
                    == "SOURCE_CHANGED"
                ):
                    manifest.status = DownloadManifestStatus.SOURCE_CHANGED
                    return manifest
        return manifest

    @begin_session
    def get_transfer_manifest_member(
        self,
        manifest_id: str,
        user_id: int,
        public_id: str,
        session: Session = None,  # type: ignore
    ) -> DownloadManifestMember | None:
        member = session.scalar(
            select(DownloadManifestMember)
            .join(DownloadManifestMember.component)
            .join(DownloadManifestComponent.manifest)
            .options(
                joinedload(DownloadManifestMember.manifest_member),
                joinedload(DownloadManifestMember.component)
                .joinedload(DownloadManifestComponent.component)
                .joinedload(RomComponent.rom),
                joinedload(DownloadManifestMember.component)
                .joinedload(DownloadManifestComponent.manifest)
                .joinedload(DownloadManifest.rom),
            )
            .where(
                DownloadManifest.id == manifest_id,
                DownloadManifest.user_id == user_id,
                DownloadManifestMember.public_id == public_id,
            )
        )
        if member is None:
            return None

        manifest = member.component.manifest
        if manifest.status is DownloadManifestStatus.VALID and datetime.now(
            timezone.utc
        ) >= to_utc(manifest.expires_at):
            manifest.status = DownloadManifestStatus.EXPIRED
        return member

    @begin_session
    def revoke_manifest(
        self,
        manifest_id: str,
        user_id: int,
        session: Session = None,  # type: ignore
    ) -> bool:
        result = session.execute(
            update(DownloadManifest)
            .where(
                DownloadManifest.id == manifest_id,
                DownloadManifest.user_id == user_id,
                DownloadManifest.status == DownloadManifestStatus.VALID,
            )
            .values(status=DownloadManifestStatus.REVOKED)
        )
        return result.rowcount == 1
