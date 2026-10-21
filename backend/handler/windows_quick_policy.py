"""Pure advisory decisions for ordinary expanded Windows quick scans."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from handler.scan_inventory_contracts import (
    InventoryAssessment,
    InventoryEvidence,
    QuickScanDecision,
)

if TYPE_CHECKING:
    from handler.database.scan_inventory_state import InventoryBinding


def is_identified_windows(rom: Any) -> bool:
    if rom is None or rom.platform_slug != "win":
        return False
    steam_id = rom.steam_id
    return bool(rom.is_identified) or (type(steam_id) is int and steam_id > 0)


def decide_windows_quick(
    *,
    scan_type: str,
    platform_slug: str,
    current_binding: "InventoryBinding | None",
    baseline_binding: "InventoryBinding | None",
    current: InventoryEvidence,
    baseline: InventoryEvidence | None,
    identified: bool,
    collection_expanded: bool,
    rom_ids: Sequence[int] = (),
    selected_provider_work: bool = False,
    selected_media_work: bool = False,
    targeted_retry: bool = False,
    authority_current: bool = True,
) -> QuickScanDecision | None:
    """Return None when the existing scan predicate must retain control.

    Advice never authorizes writes; callers retain read-context and attempt fences.
    """
    if (
        scan_type != "quick"
        or platform_slug != "win"
        or rom_ids
        or selected_provider_work
        or selected_media_work
        or targeted_retry
        or not collection_expanded
    ):
        return None
    if not authority_current or current_binding is None:
        return QuickScanDecision.INCOMPLETE
    if baseline_binding != current_binding:
        baseline = None
    assessment = InventoryAssessment.compare(current, baseline)
    if assessment.state == "incomplete":
        return QuickScanDecision.INCOMPLETE
    if assessment.state != "unchanged":
        return QuickScanDecision.REFRESH
    return QuickScanDecision.REUSE if identified else QuickScanDecision.METADATA_ONLY
