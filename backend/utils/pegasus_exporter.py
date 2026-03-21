from datetime import datetime

from fastapi import Request

from handler.database import db_platform_handler, db_rom_handler
from handler.filesystem import fs_platform_handler
from logger.logger import log
from models.rom import Rom


class PegasusExporter:
    """Export RomM collections to Pegasus Frontend metadata.pegasus.txt format"""

    def __init__(self, local_export: bool = False):
        self.local_export = local_export

    def _format_release_date(self, timestamp: int) -> str:
        """Format release date to YYYY-MM-DD format"""
        return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")

    def _format_rating(self, average_rating: float) -> str:
        """Format rating as percentage (0-100%). Input is on 0-10 scale."""
        return f"{int(average_rating * 10)}%"

    def _escape_multiline(self, text: str) -> str:
        """Indent continuation lines for multi-line values in Pegasus format"""
        lines = text.strip().splitlines()
        if len(lines) <= 1:
            return text.strip()
        # First line is on the same line as the key, subsequent lines are indented
        return (
            lines[0]
            + "\n"
            + "\n".join(f"  {line}" if line.strip() else "  ." for line in lines[1:])
        )

    def _create_game_entry(self, rom: Rom, request: Request | None) -> str:
        """Create a game entry for a ROM in Pegasus metadata format"""
        lines: list[str] = []

        # Game title (required)
        lines.append(f"game: {rom.name or rom.fs_name}")

        # File path
        if self.local_export:
            lines.append(f"file: {rom.fs_name}")
        else:
            if request is None:
                raise ValueError(
                    "Request object must be provided for non-local exports"
                )
            lines.append(
                f"file: {request.url_for('get_rom_content', id=rom.id, file_name=rom.fs_name)}"
            )

        # Sort title (use fs_name_no_tags if different from name)
        if rom.name and rom.fs_name_no_tags and rom.name != rom.fs_name_no_tags:
            lines.append(f"sort-by: {rom.fs_name_no_tags}")

        # Developers and publishers
        if rom.metadatum and rom.metadatum.companies:
            if len(rom.metadatum.companies) > 0:
                lines.append(f"developer: {rom.metadatum.companies[0]}")
            if len(rom.metadatum.companies) > 1:
                lines.append(f"publisher: {rom.metadatum.companies[1]}")

        # Genres
        if rom.metadatum and rom.metadatum.genres:
            for genre in rom.metadatum.genres:
                lines.append(f"genre: {genre}")

        # Tags (rom tags like region, language info)
        if rom.tags:
            for tag in rom.tags:
                lines.append(f"tag: {tag}")

        # Player count
        player_count = None
        if rom.gamelist_metadata and rom.gamelist_metadata.get("player_count"):
            player_count = rom.gamelist_metadata["player_count"]
        elif rom.metadatum and rom.metadatum.player_count:
            player_count = rom.metadatum.player_count
        if player_count:
            lines.append(f"players: {player_count}")

        # Summary / description
        if rom.summary:
            lines.append(f"description: {self._escape_multiline(rom.summary)}")

        # Release date
        if rom.metadatum and rom.metadatum.first_release_date is not None:
            lines.append(
                f"release: {self._format_release_date(rom.metadatum.first_release_date)}"
            )

        # Rating
        if rom.metadatum and rom.metadatum.average_rating is not None:
            lines.append(f"rating: {self._format_rating(rom.metadatum.average_rating)}")

        # RomM-specific extensions (x-* fields)
        if rom.regions:
            lines.append(f"x-region: {', '.join(rom.regions)}")

        if rom.languages:
            lines.append(f"x-language: {', '.join(rom.languages)}")

        if rom.gamelist_id:
            lines.append(f"x-romm-gamelist-id: {rom.gamelist_id}")

        return "\n".join(lines)

    def export_platform_to_pegasus(
        self, platform_id: int, request: Request | None
    ) -> str:
        """Export a platform's ROMs to metadata.pegasus.txt format

        Args:
            platform_id: Platform ID to export
            request: FastAPI request object for URL generation

        Returns:
            String content in Pegasus metadata format
        """
        platform = db_platform_handler.get_platform(platform_id)
        if not platform:
            raise ValueError(f"Platform with ID {platform_id} not found")

        roms = db_rom_handler.get_roms_scalar(platform_ids=[platform_id])

        lines: list[str] = []

        # Collection header
        lines.append(f"collection: {platform.custom_name or platform.name}")
        lines.append(f"shortname: {platform.slug}")
        lines.append("")

        # Game entries
        game_count = 0
        for rom in roms:
            if (
                rom
                and not rom.missing_from_fs
                and rom.fs_name
                not in (
                    "gamelist.xml",
                    "metadata.pegasus.txt",
                )
            ):
                if game_count > 0:
                    lines.append("")
                lines.append(self._create_game_entry(rom, request=request))
                game_count += 1

        log.info(f"Exported {game_count} ROMs for platform {platform.name}")
        return "\n".join(lines) + "\n"

    async def export_platform_to_file(
        self,
        platform_id: int,
        request: Request | None,
    ) -> bool:
        """Export platform ROMs to metadata.pegasus.txt file in the platform's directory

        Args:
            platform_id: Platform ID to export
            request: FastAPI request object for URL generation

        Returns:
            True if successful, False otherwise
        """
        try:
            platform = db_platform_handler.get_platform(platform_id)
            if not platform:
                log.error(f"Platform with ID {platform_id} not found")
                return False

            platform_fs_structure = fs_platform_handler.get_platform_fs_structure(
                platform.fs_slug
            )

            content = self.export_platform_to_pegasus(platform_id, request=request)
            await fs_platform_handler.write_file(
                content.encode("utf-8"),
                platform_fs_structure,
                "metadata.pegasus.txt",
            )

            log.info(
                f"Exported metadata.pegasus.txt to {platform_fs_structure}/metadata.pegasus.txt"
            )
            return True
        except Exception as e:
            log.error(
                f"Failed to export metadata.pegasus.txt for platform {platform_id}: {e}"
            )
            return False
