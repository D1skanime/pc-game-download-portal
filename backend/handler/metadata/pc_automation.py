"""Fail-closed automatic PC metadata decisions for mapped scans."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from handler.database import db_rom_handler
from handler.database.pc_automation_handler import DBPcAutomationHandler
from handler.metadata.pc_match_handler import (
    PcMetadataMatchHandler,
    pc_metadata_match_handler,
)
from handler.metadata.pc_steam_enrichment import (
    SteamPcEnrichmentRequest,
    resolve_steam_pc_enrichment,
)
from handler.metadata.steam_merge import normalize_steam
from handler.metadata.steam_owned_media import reconcile_steam_patch_media
from models.pc_automation import PcAutomationTargetKind


class AutomationDecision(enum.StrEnum):
    APPLIED = "applied"
    PENDING = "pending"
    SKIPPED = "skipped"
    RETRYABLE_FAILURE = "retryable_failure"


@dataclass(frozen=True, slots=True)
class AutomationResult:
    decision: AutomationDecision
    normalized_query: str
    reason: str


_WORD_BOUNDARY = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])"
)


def normalize_automation_query(value: str) -> str:
    """Make folder titles reviewable without weakening provider cardinality."""
    return " ".join(_WORD_BOUNDARY.sub(" ", value).replace("_", " ").split())


class PcAutomationHandler:
    """Apply only an already unique Steam decision, queue every other outcome."""

    def __init__(
        self,
        *,
        match_handler: PcMetadataMatchHandler = pc_metadata_match_handler,
        queue_handler: DBPcAutomationHandler | None = None,
        apply_parent: Callable[[Any, dict[str, Any]], Awaitable[bool]] | None = None,
        apply_component: (
            Callable[[Any, Any, dict[str, Any]], Awaitable[bool]] | None
        ) = None,
    ) -> None:
        self.match_handler = match_handler
        self.queue_handler = queue_handler or DBPcAutomationHandler()
        self._apply_parent_callback = apply_parent or self._apply_parent
        self._apply_component_callback = apply_component or self._apply_component

    async def process_parent(self, rom: Any) -> AutomationResult:
        query = normalize_automation_query(
            getattr(rom, "fs_name_no_ext", None) or getattr(rom, "fs_name", "")
        )
        if not query:
            return AutomationResult(AutomationDecision.SKIPPED, query, "empty_query")
        if getattr(rom, "manual_metadata", None):
            self._queue(rom, None, query, None, "protected_target")
            return AutomationResult(
                AutomationDecision.PENDING, query, "protected_target"
            )
        try:
            candidate = await self.match_handler.fetch_unique_steam_match(rom, query)
        except Exception:
            self._queue(rom, None, query, None, "provider_failure")
            return AutomationResult(
                AutomationDecision.RETRYABLE_FAILURE, query, "provider_failure"
            )
        if not self._valid_steam_parent(candidate):
            self._queue(rom, None, query, candidate, "no_unique_steam_match")
            return AutomationResult(
                AutomationDecision.PENDING, query, "no_unique_steam_match"
            )
        if await self._apply_parent_callback(rom, candidate):
            return AutomationResult(
                AutomationDecision.APPLIED, query, "unique_steam_match"
            )
        self._queue(rom, None, query, candidate, "stale_target")
        return AutomationResult(AutomationDecision.PENDING, query, "stale_target")

    async def process_component(self, rom: Any, component: Any) -> AutomationResult:
        query = normalize_automation_query(getattr(component, "relative_path", ""))
        if not self._positive_int(getattr(rom, "steam_id", None)):
            self._queue(rom, component, query, None, "untrusted_parent_steam")
            return AutomationResult(
                AutomationDecision.PENDING, query, "untrusted_parent_steam"
            )
        metadata = getattr(component, "component_metadata", None)
        if (
            metadata is not None
            and getattr(metadata, "metadata_source", None) == "manual"
        ):
            self._queue(rom, component, query, None, "protected_target")
            return AutomationResult(
                AutomationDecision.PENDING, query, "protected_target"
            )
        try:
            candidate = await self.match_handler.fetch_parent_listed_steam_dlc(
                rom, component
            )
        except Exception:
            self._queue(rom, component, query, None, "provider_failure")
            return AutomationResult(
                AutomationDecision.RETRYABLE_FAILURE, query, "provider_failure"
            )
        if not self._valid_steam_dlc(candidate, getattr(rom, "steam_id", None)):
            self._queue(rom, component, query, candidate, "no_unique_parent_listed_dlc")
            return AutomationResult(
                AutomationDecision.PENDING, query, "no_unique_parent_listed_dlc"
            )
        if await self._apply_component_callback(rom, component, candidate):
            return AutomationResult(
                AutomationDecision.APPLIED, query, "unique_parent_listed_dlc"
            )
        self._queue(rom, component, query, candidate, "stale_target")
        return AutomationResult(AutomationDecision.PENDING, query, "stale_target")

    def _queue(
        self, rom: Any, component: Any | None, query: str, candidate: Any, reason: str
    ) -> None:
        target = component or rom
        updated_at = getattr(target, "updated_at", None)
        if updated_at is None:
            return
        steam_id = candidate.get("steam_id") if isinstance(candidate, dict) else None
        self.queue_handler.upsert_pending(
            target_kind=(
                PcAutomationTargetKind.COMPONENT
                if component is not None
                else PcAutomationTargetKind.PARENT
            ),
            rom_id=rom.id,
            component_id=getattr(component, "id", None),
            expected_target_updated_at=updated_at,
            normalized_query=query or "unknown",
            candidate_fingerprint=f"steam:{steam_id or 'none'}:{reason}",
            candidate_title=(
                candidate.get("name") if isinstance(candidate, dict) else None
            ),
            provider="steam" if steam_id else None,
            provider_candidate_id=str(steam_id) if steam_id else None,
            reason=reason,
        )

    async def _apply_parent(self, rom: Any, candidate: dict[str, Any]) -> bool:
        steam_id = candidate["steam_id"]
        data = await resolve_steam_pc_enrichment(
            SteamPcEnrichmentRequest(
                scan_context="scheduled-automation",
                current={
                    "steam_id": getattr(rom, "steam_id", None),
                    "name": getattr(rom, "name", None),
                    "summary": getattr(rom, "summary", None),
                    "manual_metadata": getattr(rom, "manual_metadata", {}),
                    "steam_metadata": getattr(rom, "steam_metadata", {}),
                    "metadata": {},
                },
                platform_slug=rom.platform_slug,
                fs_name=rom.fs_name,
                metadata_sources=["steam"],
                explicit_steam_id=steam_id,
            )
        )
        if not data:
            return False
        media = data.pop("media", None)
        updated = db_rom_handler.apply_pc_metadata_candidate(
            rom.id, rom.updated_at, data
        )
        if updated is None:
            return False
        if isinstance(media, dict) and media:
            await reconcile_steam_patch_media(updated, {"media": media})
        return True

    async def _apply_component(
        self, rom: Any, component: Any, candidate: dict[str, Any]
    ) -> bool:
        metadata = getattr(component, "component_metadata", None)
        current = {
            "name": getattr(metadata, "name", None),
            "summary": getattr(metadata, "summary", None),
            "steam_metadata": (
                getattr(metadata, "provider_metadata", {}).get("steam_metadata")
                if metadata
                else None
            ),
            "metadata": {},
        }
        data = normalize_steam(candidate, current)
        if not data:
            return False
        return (
            db_rom_handler.apply_pc_component_metadata_candidate(
                rom.id, component.id, component.updated_at, "steam", data
            )
            is not None
        )

    @staticmethod
    def _positive_int(value: object) -> int | None:
        return (
            value
            if isinstance(value, int) and not isinstance(value, bool) and value > 0
            else None
        )

    @classmethod
    def _valid_steam_parent(cls, candidate: Any) -> bool:
        return (
            isinstance(candidate, dict)
            and cls._positive_int(candidate.get("steam_id")) is not None
        )

    @classmethod
    def _valid_steam_dlc(cls, candidate: Any, parent_id: object) -> bool:
        if not cls._valid_steam_parent(candidate):
            return False
        metadata = candidate.get("steam_metadata")
        fullgame = metadata.get("fullgame") if isinstance(metadata, dict) else None
        return (
            isinstance(metadata, dict)
            and metadata.get("type") == "dlc"
            and isinstance(fullgame, dict)
            and fullgame.get("appid") == parent_id
        )


pc_automation_handler = PcAutomationHandler()
