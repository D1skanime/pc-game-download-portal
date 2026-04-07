from datetime import datetime, timedelta, timezone
from typing import Literal, NotRequired, TypedDict

from handler.database import db_device_handler, db_play_session_handler, db_rom_handler
from logger.logger import log
from models.play_session import PlaySession
from models.rom import Rom
from utils.datetime import to_utc


class PlaySessionIngestResult(TypedDict):
    index: int
    status: Literal["created", "duplicate", "error"]
    id: NotRequired[int | None]
    detail: NotRequired[str | None]


class PlaySessionIngestSummary(TypedDict):
    results: list[PlaySessionIngestResult]
    created_count: int
    skipped_count: int


class PlaySessionEntry(TypedDict):
    rom_id: int | None
    save_slot: str | None
    start_time: datetime
    end_time: datetime
    duration_ms: int


def ingest_play_sessions(
    *,
    user_id: int,
    username: str,
    entries: list[PlaySessionEntry],
    device_id: str | None = None,
    sync_session_id: int | None = None,
    max_future_minutes: int = 5,
) -> PlaySessionIngestSummary:
    """Core play session ingestion logic shared by the standalone endpoint and sync complete."""
    now = datetime.now(timezone.utc)
    max_future = now + timedelta(minutes=max_future_minutes)

    # Resolve device
    resolved_device_id = None
    if device_id is not None:
        device = db_device_handler.get_device(device_id=device_id, user_id=user_id)
        if device is not None:
            resolved_device_id = device_id

    rom_cache: dict[int, Rom | None] = {}
    results: list[PlaySessionIngestResult] = []
    created_count = 0
    skipped_count = 0
    rom_user_updates: dict[int, datetime] = {}

    resolved: list[tuple[int, int | None]] = []
    candidate_keys: list[tuple[str | None, int | None, datetime]] = []
    skipped_indices: set[int] = set()

    for idx, item in enumerate(entries):
        if item["end_time"] > max_future:
            results.append(
                {
                    "index": idx,
                    "status": "error",
                    "detail": "end_time is too far in the future",
                }
            )
            skipped_count += 1
            skipped_indices.add(idx)
            resolved.append((idx, None))
            candidate_keys.append((None, None, item["start_time"]))
            continue

        rom_id = item.get("rom_id")
        resolved_rom_id = None
        if rom_id is not None:
            if rom_id not in rom_cache:
                rom_cache[rom_id] = db_rom_handler.get_rom(id=rom_id)
            rom = rom_cache[rom_id]
            if rom is not None:
                resolved_rom_id = rom_id

        resolved.append((idx, resolved_rom_id))
        candidate_keys.append(
            (resolved_device_id, resolved_rom_id, to_utc(item["start_time"]))
        )

    existing_keys = db_play_session_handler.find_existing(
        user_id=user_id,
        keys=[k for i, k in enumerate(candidate_keys) if i not in skipped_indices],
    )

    seen_keys: set[tuple[str | None, int | None, datetime]] = set()
    to_insert: list[tuple[int, int | None, PlaySession]] = []

    for (idx, resolved_rom_id), item in zip(resolved, entries, strict=False):
        if idx in skipped_indices:
            continue

        dedup_key = (resolved_device_id, resolved_rom_id, to_utc(item["start_time"]))
        if dedup_key in seen_keys or dedup_key in existing_keys:
            results.append({"index": idx, "status": "duplicate"})
            skipped_count += 1
            continue
        seen_keys.add(dedup_key)

        to_insert.append(
            (
                idx,
                resolved_rom_id,
                PlaySession(
                    user_id=user_id,
                    device_id=resolved_device_id,
                    rom_id=resolved_rom_id,
                    sync_session_id=sync_session_id,
                    save_slot=item.get("save_slot"),
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    duration_ms=item["duration_ms"],
                ),
            )
        )

    if to_insert:
        db_play_session_handler.add_sessions([ps for _, _, ps in to_insert])
        for idx, resolved_rom_id, ps in to_insert:
            results.append({"index": idx, "status": "created", "id": ps.id})
            created_count += 1
            if resolved_rom_id is not None:
                existing = rom_user_updates.get(resolved_rom_id)
                if existing is None or ps.end_time > existing:
                    rom_user_updates[resolved_rom_id] = ps.end_time

    for rom_id, latest_end_time in rom_user_updates.items():
        rom_user = db_rom_handler.get_rom_user(rom_id=rom_id, user_id=user_id)
        if not rom_user:
            rom_user = db_rom_handler.add_rom_user(rom_id=rom_id, user_id=user_id)

        update_data: dict = {}
        current_last_played = (
            to_utc(rom_user.last_played) if rom_user.last_played else None
        )
        if current_last_played is None or latest_end_time > current_last_played:
            update_data["last_played"] = latest_end_time
        if update_data:
            db_rom_handler.update_rom_user(rom_user.id, update_data)

    if resolved_device_id is not None:
        db_device_handler.update_last_seen(
            device_id=resolved_device_id, user_id=user_id
        )

    log.info(
        f"Ingested {created_count} play sessions for user {username}"
        f" ({skipped_count} skipped)"
    )

    return {
        "results": results,
        "created_count": created_count,
        "skipped_count": skipped_count,
    }
