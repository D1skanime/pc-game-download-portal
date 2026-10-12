"""Lossless migration of legacy PC saves and states into ROM resources."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from handler.database import db_save_handler, db_state_handler
from handler.database.base_handler import sync_session
from handler.filesystem import fs_asset_handler, fs_resource_handler
from logger.logger import log
from models.assets import Save, State
from tasks.tasks import Task, TaskType, update_job_meta
from utils.context import initialize_context


@dataclass
class PCSaveMigrationStats:
    scanned: int = 0
    migrated: int = 0
    skipped: int = 0
    failed: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "migrated": self.migrated,
            "skipped": self.skipped,
            "failed": self.failed,
        }


def _sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _canonical_directory(asset: Save | State) -> str:
    if isinstance(asset, Save):
        return fs_resource_handler.get_pc_save_path(asset.rom, asset.emulator)
    return fs_resource_handler.get_pc_state_path(asset.rom, asset.emulator)


def _canonical_path(asset: Save | State) -> str:
    return f"{_canonical_directory(asset)}/{asset.file_name}"


def _migrate_one(asset: Save | State) -> bool:
    if asset.rom is None:
        return False

    source_path = fs_asset_handler.validate_path(asset.full_path)
    canonical_relative = _canonical_path(asset)
    canonical_path = fs_resource_handler.validate_path(canonical_relative)
    if asset.file_path == _canonical_directory(asset) and canonical_path.is_file():
        return False

    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    source_hash, source_size = _sha256_and_size(source_path)

    if canonical_path.exists():
        if not canonical_path.is_file():
            raise IsADirectoryError(canonical_path)
        target_hash, target_size = _sha256_and_size(canonical_path)
        if (target_hash, target_size) != (source_hash, source_size):
            raise ValueError(
                f"canonical bytes differ for {asset.__class__.__name__} {asset.id}"
            )
        data = {"file_path": _canonical_directory(asset)}
        if isinstance(asset, Save):
            db_save_handler.update_save(asset.id, data)
        else:
            db_state_handler.update_state(asset.id, data)
        return True

    temporary_path: Path | None = None
    try:
        fd, temporary_name = tempfile.mkstemp(
            dir=str(canonical_path.parent),
            prefix=f".{asset.__class__.__name__.lower()}-migration-",
        )
        os.close(fd)
        temporary_path = Path(temporary_name)
        with source_path.open("rb") as source, temporary_path.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())

        copied_hash, copied_size = _sha256_and_size(temporary_path)
        if (copied_hash, copied_size) != (source_hash, source_size):
            raise ValueError(
                f"copied bytes differ for {asset.__class__.__name__} {asset.id}"
            )

        os.replace(temporary_path, canonical_path)
        temporary_path = None
        data = {"file_path": _canonical_directory(asset)}
        if isinstance(asset, Save):
            db_save_handler.update_save(asset.id, data)
        else:
            db_state_handler.update_state(asset.id, data)
        return True
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class PCSaveMigrationTask(Task):
    def __init__(self) -> None:
        super().__init__(
            title="Migrate PC save and state files",
            description="Promote legacy PC saves and states into ROM-owned resources",
            task_type=TaskType.GENERIC,
            enabled=True,
            manual_run=True,
        )

    @initialize_context()
    async def run(self) -> dict[str, int]:
        stats = PCSaveMigrationStats()
        with sync_session() as session:
            assets = list(
                session.scalars(
                    select(Save)
                    .options(joinedload(Save.rom))
                    .where(Save.rom_id.is_not(None))
                ).all()
            )
            assets.extend(
                session.scalars(
                    select(State)
                    .options(joinedload(State.rom))
                    .where(State.rom_id.is_not(None))
                ).all()
            )

        for asset in assets:
            stats.scanned += 1
            try:
                if _migrate_one(asset):
                    stats.migrated += 1
                else:
                    stats.skipped += 1
            except Exception:
                stats.failed += 1
                log.exception(
                    "PC save/state migration failed for %s %s",
                    type(asset).__name__,
                    asset.id,
                )
            if stats.scanned % 100 == 0:
                update_job_meta({"pc_save_migration": stats.to_dict()})

        update_job_meta({"pc_save_migration": stats.to_dict()})
        return stats.to_dict()


pc_save_migration_task = PCSaveMigrationTask()
