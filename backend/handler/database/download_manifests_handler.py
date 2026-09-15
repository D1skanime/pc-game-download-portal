from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from config import DOWNLOAD_MANIFEST_TTL_SECONDS
from decorators.database import begin_session
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
        self, rom: Rom, member: RomComponentManifestMember
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

        rom = session.scalar(select(Rom).where(Rom.id == rom_id).with_for_update())
        if rom is None:
            raise ValueError("manifest ROM is unavailable")

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
                    )
                )
                .order_by(RomComponentManifestMember.id)
                .with_for_update()
            )
        )
        members_by_component: dict[int, list[RomComponentManifestMember]] = {
            component.id: [] for component in components
        }
        for member in member_rows:
            members_by_component[member.component_id].append(member)
        if any(not members_by_component[component.id] for component in components):
            raise ValueError("manifest components need source members")

        captured: list[
            tuple[
                RomComponent, RomComponentManifestMember, DownloadManifestMemberEvidence
            ]
        ] = []
        for component in components:
            for member in members_by_component[component.id]:
                if (
                    member.size_bytes < 0
                    or len(member.sha256) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in member.sha256
                    )
                ):
                    raise ValueError("manifest member hash evidence is unavailable")
                captured.append(
                    (
                        component,
                        member,
                        self.filesystem_handler.capture_download_manifest_member(
                            rom, member
                        ),
                    )
                )

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
        for component, member, evidence in captured:
            selected_components[component.id].members.append(
                DownloadManifestMember(
                    manifest_member=member,
                    destination=evidence.destination,
                    size_bytes=evidence.size_bytes,
                    sha256=evidence.sha256,
                    snapshot=evidence.snapshot,
                    mtime_ns=evidence.mtime_ns,
                    device=evidence.device,
                    inode=evidence.inode,
                )
            )
        session.add(manifest)
        session.flush()
        session.refresh(manifest)
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
