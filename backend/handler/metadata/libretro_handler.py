import hashlib
import os
import re
from typing import Final, NotRequired, TypedDict

from adapters.services.libretro_thumbnails import (
    LIBRETRO_THUMBNAIL_ROOT,
    LibretroThumbnailsService,
)
from adapters.services.libretro_thumbnails_types import LibretroArtType
from logger.logger import log

from .base_handler import MetadataHandler, UniversalPlatformSlug

# Mapping of RomM UniversalPlatformSlug values to libretro thumbnail
# directory names (https://thumbnails.libretro.com/).
LIBRETRO_PLATFORM_LIST: Final[dict[UniversalPlatformSlug, str]] = {
    UniversalPlatformSlug.ADVENTURE_VISION: "Entex - Adventure Vision",
    UniversalPlatformSlug.AMIGA: "Commodore - Amiga",
    UniversalPlatformSlug.AMIGA_CD32: "Commodore - Amiga",
    UniversalPlatformSlug.ACPC: "Amstrad - CPC",
    UniversalPlatformSlug.ATARI2600: "Atari - 2600",
    UniversalPlatformSlug.ATARI5200: "Atari - 5200",
    UniversalPlatformSlug.ATARI7800: "Atari - 7800",
    UniversalPlatformSlug.ATARI_ST: "Atari - ST",
    UniversalPlatformSlug.JAGUAR: "Atari - Jaguar",
    UniversalPlatformSlug.LYNX: "Atari - Lynx",
    UniversalPlatformSlug.WONDERSWAN: "Bandai - WonderSwan",
    UniversalPlatformSlug.WONDERSWAN_COLOR: "Bandai - WonderSwan Color",
    UniversalPlatformSlug.COLECOVISION: "Coleco - ColecoVision",
    UniversalPlatformSlug.C64: "Commodore - 64",
    UniversalPlatformSlug.VIC_20: "Commodore - VIC-20",
    UniversalPlatformSlug.DOS: "DOS",
    UniversalPlatformSlug.FAIRCHILD_CHANNEL_F: "Fairchild - Channel F",
    UniversalPlatformSlug.VECTREX: "GCE - Vectrex",
    UniversalPlatformSlug.ODYSSEY_2: "Magnavox - Odyssey2",
    UniversalPlatformSlug.INTELLIVISION: "Mattel - Intellivision",
    UniversalPlatformSlug.MSX: "Microsoft - MSX",
    UniversalPlatformSlug.MSX2: "Microsoft - MSX2",
    UniversalPlatformSlug.XBOX: "Microsoft - XBOX",
    UniversalPlatformSlug.PC_8800_SERIES: "NEC - PC Engine - TurboGrafx 16",
    UniversalPlatformSlug.PC_FX: "NEC - PC-FX",
    UniversalPlatformSlug.PC_9800_SERIES: "NEC - PC-98",
    UniversalPlatformSlug.SUPERGRAFX: "NEC - PC Engine SuperGrafx",
    UniversalPlatformSlug.TG16: "NEC - PC Engine - TurboGrafx 16",
    UniversalPlatformSlug.TURBOGRAFX_CD: "NEC - PC Engine CD - TurboGrafx-CD",
    UniversalPlatformSlug.FDS: "Nintendo - Family Computer Disk System",
    UniversalPlatformSlug.GB: "Nintendo - Game Boy",
    UniversalPlatformSlug.GBA: "Nintendo - Game Boy Advance",
    UniversalPlatformSlug.GBC: "Nintendo - Game Boy Color",
    UniversalPlatformSlug.NGC: "Nintendo - GameCube",
    UniversalPlatformSlug.N64: "Nintendo - Nintendo 64",
    UniversalPlatformSlug.N64DD: "Nintendo - Nintendo 64DD",
    UniversalPlatformSlug.N3DS: "Nintendo - Nintendo 3DS",
    UniversalPlatformSlug.NDS: "Nintendo - Nintendo DS",
    UniversalPlatformSlug.NES: "Nintendo - Nintendo Entertainment System",
    UniversalPlatformSlug.FAMICOM: "Nintendo - Nintendo Entertainment System",
    UniversalPlatformSlug.POKEMON_MINI: "Nintendo - Pokemon Mini",
    UniversalPlatformSlug.SATELLAVIEW: "Nintendo - Satellaview",
    UniversalPlatformSlug.SUFAMI_TURBO: "Nintendo - Sufami Turbo",
    UniversalPlatformSlug.SNES: "Nintendo - Super Nintendo Entertainment System",
    UniversalPlatformSlug.SFAM: "Nintendo - Super Nintendo Entertainment System",
    UniversalPlatformSlug.VIRTUALBOY: "Nintendo - Virtual Boy",
    UniversalPlatformSlug.WII: "Nintendo - Wii",
    UniversalPlatformSlug.WIIU: "Nintendo - Wii U",
    UniversalPlatformSlug.SCUMMVM: "ScummVM",
    UniversalPlatformSlug.SEGA32: "Sega - 32X",
    UniversalPlatformSlug.DC: "Sega - Dreamcast",
    UniversalPlatformSlug.GAMEGEAR: "Sega - Game Gear",
    UniversalPlatformSlug.GENESIS: "Sega - Mega Drive - Genesis",
    UniversalPlatformSlug.SEGACD: "Sega - Mega-CD - Sega CD",
    UniversalPlatformSlug.SMS: "Sega - Master System - Mark III",
    UniversalPlatformSlug.SG1000: "Sega - SG-1000",
    UniversalPlatformSlug.SATURN: "Sega - Saturn",
    UniversalPlatformSlug.X1: "Sharp - X1",
    UniversalPlatformSlug.SHARP_X68000: "Sharp - X68000",
    UniversalPlatformSlug.ZX81: "Sinclair - ZX 81",
    UniversalPlatformSlug.ZXS: "Sinclair - ZX Spectrum",
    UniversalPlatformSlug.NEOGEOAES: "SNK - Neo Geo",
    UniversalPlatformSlug.NEOGEOMVS: "SNK - Neo Geo",
    UniversalPlatformSlug.NEO_GEO_CD: "SNK - Neo Geo CD",
    UniversalPlatformSlug.NEO_GEO_POCKET: "SNK - Neo Geo Pocket",
    UniversalPlatformSlug.NEO_GEO_POCKET_COLOR: "SNK - Neo Geo Pocket Color",
    UniversalPlatformSlug.PSX: "Sony - PlayStation",
    UniversalPlatformSlug.PS2: "Sony - PlayStation 2",
    UniversalPlatformSlug.PSP: "Sony - PlayStation Portable",
    UniversalPlatformSlug.TIC_80: "TIC-80",
    UniversalPlatformSlug.TOMY_TUTOR: "Tomy - Tutor",
    UniversalPlatformSlug.SUPERVISION: "Watara - Supervision",
}


_PAREN_TAG_PATTERN = re.compile(r"\([^)]*\)")


class LibretroRom(TypedDict):
    libretro_id: str | None
    url_cover: NotRequired[str]
    name: NotRequired[str]


def _remove_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[0]


def _strip_paren_tags(s: str) -> str:
    """Remove parenthetical tags like (USA), (SGB Enhanced) from a filename."""
    return _PAREN_TAG_PATTERN.sub("", s).strip()


def libretro_id_for(filename: str) -> str:
    """Deterministic ID for a libretro art filename.

    SHA1 hex of the full filename (extension included). Stable across scans
    for the same matched art, fits in the `roms.libretro_id` column (40 chars
    in a varchar(64)).
    """
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()


class LibretroHandler(MetadataHandler):
    """Handler for libretro thumbnails (https://thumbnails.libretro.com).

    Artwork-only source, supplies box-art URLs but no game IDs, summaries,
    or metadata. Follows the same integration pattern as SGDBBaseHandler.
    """

    def __init__(self) -> None:
        self.service = LibretroThumbnailsService()
        self.min_similarity_score: Final = 0.8

    @classmethod
    def is_enabled(cls) -> bool:
        # Public server, no API key required. Always enabled.
        return True

    async def heartbeat(self) -> bool:
        try:
            return await self.service.head()
        except Exception as exc:
            log.error("Error checking libretro thumbnails: %s", exc)
            return False

    def _resolve_system(self, platform_slug: str) -> str | None:
        try:
            ups = UniversalPlatformSlug(platform_slug)
        except ValueError:
            return None
        return LIBRETRO_PLATFORM_LIST.get(ups)

    def _find_exact_match(self, target: str, listing: list[str]) -> str | None:
        """Case-insensitive exact match on filename (extension stripped)."""
        target_lower = target.lower()
        for filename in listing:
            if _remove_file_extension(filename).lower() == target_lower:
                return filename
        return None

    def _find_fuzzy_match(self, target: str, listing: list[str]) -> str | None:
        """Fuzzy fallback, strips parenthetical tags from both sides and uses
        JaroWinkler via MetadataHandler.find_best_match."""
        if not listing:
            return None
        query = _strip_paren_tags(target)
        # Build candidate list of tag-stripped names that map back to original filenames
        stripped_to_original: dict[str, str] = {}
        for filename in listing:
            stripped = _strip_paren_tags(_remove_file_extension(filename))
            # Keep the first occurrence, libretro typically has one canonical
            # entry per region; ties are acceptable since we fall back here.
            stripped_to_original.setdefault(stripped, filename)

        match, _score = self.find_best_match(
            query,
            list(stripped_to_original.keys()),
            min_similarity_score=self.min_similarity_score,
        )
        if not match:
            return None
        return stripped_to_original[match]

    def _find_matching_art(self, fs_name: str, listing: list[str]) -> str | None:
        # Libretro's filename convention replaces '&' with '_'.
        cleaned = fs_name.replace("&", "_")
        target = _remove_file_extension(cleaned)

        exact = self._find_exact_match(target, listing)
        if exact:
            return exact

        return self._find_fuzzy_match(target, listing)

    async def get_rom(self, fs_name: str, platform_slug: str) -> LibretroRom:
        """Find box art for a ROM on the libretro thumbnail server.

        Scan-time callers use the returned `url_cover`. `name` is deliberately
        omitted because libretro artwork filenames are not proper game names —
        letting them overwrite a real name from IGDB/Moby would be wrong.
        """
        system_name = self._resolve_system(platform_slug)
        if not system_name:
            return LibretroRom(libretro_id=None)

        listing = await self.service.fetch_listing(system_name, LibretroArtType.BOX_ART)
        if not listing:
            return LibretroRom(libretro_id=None)

        matched = self._find_matching_art(fs_name, listing)
        if not matched:
            return LibretroRom(libretro_id=None)

        url = LibretroThumbnailsService.build_art_url(
            system_name, LibretroArtType.BOX_ART, matched
        )
        return LibretroRom(
            libretro_id=libretro_id_for(matched),
            url_cover=url,
        )

    async def get_matched_roms_by_name(
        self, search_term: str, platform_slug: str, limit: int = 25
    ) -> list[LibretroRom]:
        """Return candidate libretro art matches for a search term.

        Used by the `/search/roms` endpoint. Returns all filenames whose
        tag-stripped title matches the search term on either an exact or
        fuzzy basis.
        """
        system_name = self._resolve_system(platform_slug)
        if not system_name:
            return []

        listing = await self.service.fetch_listing(system_name, LibretroArtType.BOX_ART)
        if not listing:
            return []

        normalized_query = self.normalize_search_term(
            search_term, remove_articles=False
        )
        matches: list[LibretroRom] = []
        seen: set[str] = set()

        # Collect all filenames whose normalized tag-stripped title matches the
        # normalized search term. The exposed `name` is the tag-stripped title
        # so merge-by-normalized-name lines up with IGDB/Moby/etc. The full
        # filename is preserved in `libretro_id` for traceability.
        for filename in listing:
            stripped = _strip_paren_tags(_remove_file_extension(filename))
            if not stripped:
                continue
            normalized_candidate = self.normalize_search_term(
                stripped, remove_articles=False
            )
            if normalized_candidate != normalized_query:
                continue
            if filename in seen:
                continue
            seen.add(filename)
            matches.append(
                LibretroRom(
                    libretro_id=libretro_id_for(filename),
                    url_cover=LibretroThumbnailsService.build_art_url(
                        system_name, LibretroArtType.BOX_ART, filename
                    ),
                    name=stripped,
                )
            )

        if matches:
            return matches[:limit]

        # No exact-title hits, fall back to a single fuzzy match.
        fuzzy = self._find_fuzzy_match(search_term, listing)
        if fuzzy:
            matches.append(
                LibretroRom(
                    libretro_id=libretro_id_for(fuzzy),
                    url_cover=LibretroThumbnailsService.build_art_url(
                        system_name, LibretroArtType.BOX_ART, fuzzy
                    ),
                    name=_strip_paren_tags(_remove_file_extension(fuzzy)),
                )
            )
        return matches[:limit]
