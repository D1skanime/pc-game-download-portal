from __future__ import annotations

import os
from typing import TypedDict

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis

from logger.logger import log


class AudioMeta(TypedDict, total=False):
    title: str | None
    artist: str | None
    album: str | None
    year: str | None
    genre: str | None
    track: str | None
    disc: str | None
    duration_seconds: float | None
    has_embedded_cover: bool
    cover_path: str | None
    file_mtime: float
    file_size: int


_EASY_TAG_MAP = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "date": "year",
    "genre": "genre",
    "tracknumber": "track",
    "discnumber": "disc",
}


def _first(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else None
    return str(value)


def _has_embedded_cover(audio: mutagen.FileType) -> bool:
    tags = getattr(audio, "tags", None)
    if tags is None:
        return False
    if isinstance(tags, ID3):
        return any(isinstance(f, APIC) for f in tags.values())
    if isinstance(audio, FLAC):
        return bool(audio.pictures)
    if isinstance(audio, OggVorbis):
        return bool(tags.get("metadata_block_picture"))
    if isinstance(audio, MP4):
        return bool(tags.get("covr"))
    return False


def extract_audio_meta(full_path: str) -> AudioMeta | None:
    """Read tags + duration + embedded-cover presence from an audio file.

    Returns None if the file cannot be parsed. Never raises — on any failure
    we log and fall back to None so the upload/scan path keeps moving.
    """
    try:
        stat = os.stat(full_path)
    except OSError as exc:
        log.warning(f"[audio_tags] stat failed for {full_path}: {exc}")
        return None

    try:
        audio = mutagen.File(full_path, easy=True)
    except Exception as exc:
        log.warning(f"[audio_tags] parse failed for {full_path}: {exc}")
        return None

    if audio is None:
        return None

    meta: AudioMeta = {
        "file_mtime": stat.st_mtime,
        "file_size": stat.st_size,
    }

    tags = getattr(audio, "tags", None) or {}
    for raw_key, out_key in _EASY_TAG_MAP.items():
        meta[out_key] = _first(tags.get(raw_key))  # type: ignore[literal-required]

    info = getattr(audio, "info", None)
    duration = getattr(info, "length", None) if info is not None else None
    meta["duration_seconds"] = float(duration) if duration else None

    try:
        # For cover detection we need the non-easy view on ID3-backed formats.
        probe = mutagen.File(full_path)
        meta["has_embedded_cover"] = bool(probe and _has_embedded_cover(probe))
    except Exception as exc:
        log.debug(f"[audio_tags] cover probe failed for {full_path}: {exc}")
        meta["has_embedded_cover"] = False

    return meta


def _extract_picture_from_id3(tags: ID3) -> tuple[bytes, str] | None:
    for frame in tags.values():
        if isinstance(frame, APIC):
            return frame.data, frame.mime or "image/jpeg"
    return None


def _extract_picture_from_flac(audio: FLAC) -> tuple[bytes, str] | None:
    if audio.pictures:
        pic = audio.pictures[0]
        return pic.data, pic.mime or "image/jpeg"
    return None


def _extract_picture_from_ogg(audio: OggVorbis) -> tuple[bytes, str] | None:
    import base64

    pics = audio.get("metadata_block_picture") or []
    for encoded in pics:
        try:
            pic = Picture(base64.b64decode(encoded))
        except Exception as exc:
            log.debug(f"[audio_tags] ogg picture decode failed: {exc}")
            continue
        return pic.data, pic.mime or "image/jpeg"
    return None


def _extract_picture_from_mp4(audio: MP4) -> tuple[bytes, str] | None:
    covers = audio.tags.get("covr") if audio.tags else None
    if not covers:
        return None
    cover = covers[0]
    fmt = getattr(cover, "imageformat", None)
    mime = "image/png" if fmt == MP4.Cover.FORMAT_PNG else "image/jpeg"
    return bytes(cover), mime


_COVER_EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _ext_for_mime(mime: str) -> str:
    return _COVER_EXT_BY_MIME.get(mime.lower().split(";")[0].strip(), "bin")


def soundtrack_cover_dir(platform_id: int, rom_id: int) -> str:
    """Relative directory (under RESOURCES_BASE_PATH) where soundtrack covers
    for a given ROM are persisted."""
    return f"roms/{platform_id}/{rom_id}/soundtracks"


def persist_embedded_cover(
    audio_full_path: str,
    platform_id: int,
    rom_id: int,
    file_id: int,
) -> str | None:
    """Extract the embedded cover from `audio_full_path` and write it under
    RESOURCES_BASE_PATH. Returns the relative path (suitable for storing in
    audio_meta.cover_path), or None if no cover or write failed."""
    from config import RESOURCES_BASE_PATH

    cover = extract_embedded_cover(audio_full_path)
    if cover is None:
        return None

    data, mime = cover
    rel_dir = soundtrack_cover_dir(platform_id, rom_id)
    rel_path = f"{rel_dir}/{file_id}.{_ext_for_mime(mime)}"
    abs_dir = os.path.join(RESOURCES_BASE_PATH, rel_dir)
    abs_path = os.path.join(RESOURCES_BASE_PATH, rel_path)

    try:
        os.makedirs(abs_dir, exist_ok=True)
        with open(abs_path, "wb") as fh:
            fh.write(data)
    except OSError as exc:
        log.warning(f"[audio_tags] cover write failed for {abs_path}: {exc}")
        return None

    return rel_path


def remove_persisted_cover(cover_path: str | None) -> None:
    """Delete a persisted soundtrack cover (relative path under
    RESOURCES_BASE_PATH). Silently ignores missing files."""
    if not cover_path:
        return
    from config import RESOURCES_BASE_PATH

    abs_path = os.path.join(RESOURCES_BASE_PATH, cover_path)
    try:
        os.unlink(abs_path)
    except FileNotFoundError:
        return
    except OSError as exc:
        log.warning(f"[audio_tags] cover delete failed for {abs_path}: {exc}")


def extract_embedded_cover(full_path: str) -> tuple[bytes, str] | None:
    """Return (image_bytes, mime_type) for the first embedded picture, or None."""
    try:
        audio = mutagen.File(full_path)
    except Exception as exc:
        log.warning(f"[audio_tags] cover extract failed for {full_path}: {exc}")
        return None

    if audio is None:
        return None

    if isinstance(audio, FLAC):
        return _extract_picture_from_flac(audio)
    if isinstance(audio, OggVorbis):
        return _extract_picture_from_ogg(audio)
    if isinstance(audio, MP4):
        return _extract_picture_from_mp4(audio)

    tags = getattr(audio, "tags", None)
    if isinstance(tags, ID3):
        return _extract_picture_from_id3(tags)

    return None
