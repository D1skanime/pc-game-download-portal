from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from decorators.database import begin_session
from models.assets import Save, Screenshot, State
from models.base import utc_now
from models.catalog_lifecycle import (
    OwnedCleanupIntent,
    OwnedCleanupKind,
    OwnedCleanupState,
    RetainedCatalogIdentity,
)
from models.collection import CollectionRom
from models.play_session import PlaySession
from models.rom import (
    Rom,
    RomFacets,
    RomFile,
    RomMetadata,
    RomNote,
    RomUser,
)

CLEANUP_LEASE = timedelta(minutes=5)
CLEANUP_SAFE_ERROR = "Owned cleanup could not be completed"


@dataclass(frozen=True, slots=True)
class CatalogRemovalOutcome:
    rom_id: int
    retained_catalog_id: int
    retained_saves: int
    retained_states: int
    retained_play_sessions: int
    cleanup_pending: int


@dataclass(frozen=True, slots=True)
class ClaimedCleanupIntent:
    id: int
    version: int
    kind: str
    relative_path: str | None
    file_name: str | None


class CatalogLifecycleHandler:
    def _before_catalog_delete(
        self,
        *,
        session: Session,
        rom: Rom,
        retained: RetainedCatalogIdentity,
    ) -> None:
        """Test seam for transaction rollback evidence."""

    @staticmethod
    def _get_or_create_retained_identity(
        session: Session,
        rom: Rom,
        actor_user_id: int,
    ) -> RetainedCatalogIdentity:
        retained = session.scalar(
            select(RetainedCatalogIdentity)
            .where(
                or_(
                    RetainedCatalogIdentity.active_rom_id == rom.id,
                    RetainedCatalogIdentity.detached_rom_id == rom.id,
                )
            )
            .order_by(RetainedCatalogIdentity.id)
            .with_for_update()
        )
        if retained is None:
            retained = RetainedCatalogIdentity(
                platform_id=rom.platform_id,
                detached_rom_id=rom.id,
                active_rom_id=None,
                logical_path=rom.fs_path,
                file_name=rom.fs_name,
                crc_hash=rom.crc_hash,
                md5_hash=rom.md5_hash,
                sha1_hash=rom.sha1_hash,
                detached_by_user_id=actor_user_id,
            )
            session.add(retained)
            session.flush()
            return retained

        retained.detached_rom_id = rom.id
        retained.active_rom_id = None
        retained.logical_path = rom.fs_path
        retained.file_name = rom.fs_name
        retained.crc_hash = rom.crc_hash
        retained.md5_hash = rom.md5_hash
        retained.sha1_hash = rom.sha1_hash
        retained.detached_by_user_id = actor_user_id
        retained.detached_at = utc_now()
        retained.reconnected_at = None
        retained.version += 1
        session.flush()
        return retained

    @staticmethod
    def _add_cleanup_intents(
        session: Session,
        rom: Rom,
        retained: RetainedCatalogIdentity,
        actor_user_id: int,
        screenshots: list[Screenshot],
    ) -> int:
        intents = [
            OwnedCleanupIntent(
                retained_catalog_id=retained.id,
                kind=OwnedCleanupKind.RESOURCE,
                relative_path=rom.fs_resources_path,
                deduplication_key=f"catalog:{retained.id}:resource",
                actor_user_id=actor_user_id,
            )
        ]
        intents.extend(
            OwnedCleanupIntent(
                retained_catalog_id=retained.id,
                kind=OwnedCleanupKind.SCREENSHOT,
                resource_id=screenshot.id,
                relative_path=screenshot.file_path,
                file_name=screenshot.file_name,
                deduplication_key=(f"catalog:{retained.id}:screenshot:{screenshot.id}"),
                actor_user_id=actor_user_id,
            )
            for screenshot in screenshots
        )
        session.add_all(intents)
        session.flush()
        return len(intents)

    @begin_session
    def remove_from_catalog(
        self,
        rom_id: int,
        *,
        actor_user_id: int,
        session: Session = None,  # type: ignore[assignment]
    ) -> CatalogRemovalOutcome | None:
        rom = session.scalar(
            select(Rom).where(Rom.id == rom_id).with_for_update(of=Rom)
        )
        if rom is None:
            return None

        screenshots = list(
            session.scalars(
                select(Screenshot)
                .where(Screenshot.rom_id == rom_id)
                .order_by(Screenshot.id)
                .with_for_update()
            ).all()
        )
        retained = self._get_or_create_retained_identity(session, rom, actor_user_id)

        retained_saves = session.execute(
            update(Save)
            .where(Save.rom_id == rom_id)
            .values(rom_id=None, retained_catalog_id=retained.id)
        ).rowcount
        retained_states = session.execute(
            update(State)
            .where(State.rom_id == rom_id)
            .values(rom_id=None, retained_catalog_id=retained.id)
        ).rowcount
        retained_play_sessions = session.execute(
            update(PlaySession)
            .where(PlaySession.rom_id == rom_id)
            .values(rom_id=None, retained_catalog_id=retained.id)
        ).rowcount
        cleanup_pending = self._add_cleanup_intents(
            session, rom, retained, actor_user_id, screenshots
        )

        self._before_catalog_delete(session=session, rom=rom, retained=retained)

        session.execute(delete(CollectionRom).where(CollectionRom.rom_id == rom_id))
        for model in (
            RomNote,
            RomUser,
            Screenshot,
            RomFile,
            RomMetadata,
            RomFacets,
        ):
            session.execute(delete(model).where(model.rom_id == rom_id))
        session.execute(delete(Rom).where(Rom.id == rom_id))
        session.flush()

        return CatalogRemovalOutcome(
            rom_id=rom_id,
            retained_catalog_id=retained.id,
            retained_saves=retained_saves or 0,
            retained_states=retained_states or 0,
            retained_play_sessions=retained_play_sessions or 0,
            cleanup_pending=cleanup_pending,
        )

    @begin_session
    def claim_cleanup_intents(
        self,
        *,
        limit: int,
        session: Session = None,  # type: ignore[assignment]
    ) -> list[ClaimedCleanupIntent]:
        now = utc_now()
        rows = list(
            session.scalars(
                select(OwnedCleanupIntent)
                .where(
                    or_(
                        OwnedCleanupIntent.state.in_(
                            (
                                OwnedCleanupState.PENDING,
                                OwnedCleanupState.FAILED,
                            )
                        ),
                        (OwnedCleanupIntent.state == OwnedCleanupState.PROCESSING)
                        & (OwnedCleanupIntent.next_attempt_at <= now),
                    )
                )
                .order_by(OwnedCleanupIntent.id)
                .limit(limit)
                .with_for_update()
            ).all()
        )
        claimed = []
        for row in rows:
            row.state = OwnedCleanupState.PROCESSING
            row.version += 1
            row.attempt_count += 1
            row.safe_error = None
            row.next_attempt_at = now + CLEANUP_LEASE
            claimed.append(
                ClaimedCleanupIntent(
                    id=row.id,
                    version=row.version,
                    kind=row.kind,
                    relative_path=row.relative_path,
                    file_name=row.file_name,
                )
            )
        session.flush()
        return claimed

    @begin_session
    def complete_cleanup_intent(
        self,
        intent_id: int,
        *,
        expected_version: int,
        session: Session = None,  # type: ignore[assignment]
    ) -> bool:
        intent = session.scalar(
            select(OwnedCleanupIntent)
            .where(OwnedCleanupIntent.id == intent_id)
            .with_for_update()
        )
        if (
            intent is None
            or intent.version != expected_version
            or intent.state != OwnedCleanupState.PROCESSING
        ):
            return False
        intent.state = OwnedCleanupState.COMPLETED
        intent.version += 1
        intent.safe_error = None
        intent.next_attempt_at = None
        intent.completed_at = utc_now()
        session.flush()
        return True

    @begin_session
    def fail_cleanup_intent(
        self,
        intent_id: int,
        *,
        expected_version: int,
        session: Session = None,  # type: ignore[assignment]
    ) -> bool:
        intent = session.scalar(
            select(OwnedCleanupIntent)
            .where(OwnedCleanupIntent.id == intent_id)
            .with_for_update()
        )
        if (
            intent is None
            or intent.version != expected_version
            or intent.state != OwnedCleanupState.PROCESSING
        ):
            return False
        intent.state = OwnedCleanupState.FAILED
        intent.version += 1
        intent.safe_error = CLEANUP_SAFE_ERROR
        intent.next_attempt_at = None
        session.flush()
        return True

    @begin_session
    def count_pending_cleanup(
        self,
        *,
        session: Session = None,  # type: ignore[assignment]
    ) -> int:
        return int(
            session.scalar(
                select(func.count(OwnedCleanupIntent.id)).where(
                    OwnedCleanupIntent.state != OwnedCleanupState.COMPLETED
                )
            )
            or 0
        )
