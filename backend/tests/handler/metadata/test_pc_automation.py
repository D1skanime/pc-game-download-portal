from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from handler.metadata import pc_automation as pc_automation_module
from handler.metadata.pc_automation import (
    AutomationDecision,
    PcAutomationHandler,
)


def _rom(**overrides):
    values = {
        "id": 41,
        "fs_name": "Cyberpunk2077",
        "fs_name_no_ext": "Cyberpunk2077",
        "platform_slug": "win",
        "updated_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "steam_id": None,
        "steam_metadata": {},
        "manual_metadata": {},
        "components": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_parent_uses_one_validated_steam_result_and_targets_the_parent():
    rom = _rom()
    matcher = Mock()
    matcher.fetch_unique_steam_match = AsyncMock(
        return_value={
            "steam_id": 1091500,
            "name": "Cyberpunk 2077",
            "summary": "Deutsche Steam-Beschreibung",
            "steam_metadata": {"language": "de"},
        }
    )
    apply_parent = AsyncMock(return_value=True)
    handler = PcAutomationHandler(
        match_handler=matcher,
        apply_parent=apply_parent,
        queue_handler=Mock(),
    )

    result = await handler.process_parent(rom)

    assert result.decision is AutomationDecision.APPLIED
    assert result.normalized_query == "Cyberpunk 2077"
    matcher.fetch_unique_steam_match.assert_awaited_once_with(rom, "Cyberpunk 2077")
    apply_parent.assert_awaited_once_with(
        rom, matcher.fetch_unique_steam_match.return_value
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("steam_match", [None, {"steam_id": 0}])
async def test_parent_without_one_validated_steam_result_is_pending_without_apply(
    steam_match,
):
    rom = _rom(name="Manual title", summary="Keep me")
    matcher = Mock(fetch_unique_steam_match=AsyncMock(return_value=steam_match))
    queue = Mock(upsert_pending=Mock())
    apply_parent = AsyncMock()
    handler = PcAutomationHandler(
        match_handler=matcher, apply_parent=apply_parent, queue_handler=queue
    )

    result = await handler.process_parent(rom)

    assert result.decision is AutomationDecision.PENDING
    assert result.reason == "no_unique_steam_match"
    apply_parent.assert_not_awaited()
    queue.upsert_pending.assert_called_once()
    assert rom.name == "Manual title"
    assert rom.summary == "Keep me"


@pytest.mark.asyncio
async def test_dlc_requires_parent_listed_unique_relation_before_apply():
    component = SimpleNamespace(
        id=7,
        kind="dlc",
        updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        component_metadata=None,
    )
    rom = _rom(steam_id=1091500)
    matcher = Mock(
        fetch_parent_listed_steam_dlc=AsyncMock(
            return_value={
                "steam_id": 2138330,
                "name": "Cyberpunk 2077: Phantom Liberty",
                "steam_metadata": {"type": "dlc", "fullgame": {"appid": 1091500}},
            }
        )
    )
    apply_component = AsyncMock(return_value=True)
    handler = PcAutomationHandler(
        match_handler=matcher,
        apply_component=apply_component,
        queue_handler=Mock(),
    )

    result = await handler.process_component(rom, component)

    assert result.decision is AutomationDecision.APPLIED
    apply_component.assert_awaited_once_with(
        rom, component, matcher.fetch_parent_listed_steam_dlc.return_value
    )


@pytest.mark.asyncio
async def test_component_apply_retains_existing_steam_text_variants(mocker):
    metadata = SimpleNamespace(
        name="Phantom Liberty",
        summary="English description",
        steam_metadata={
            "text_variants": {
                "en": {
                    "name": "Phantom Liberty",
                    "summary": "English description",
                    "source_language": "english",
                }
            }
        },
        provider_metadata={"igdb_metadata": {"id": 77}},
    )
    component = SimpleNamespace(
        id=7,
        updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        component_metadata=metadata,
    )
    apply = mocker.patch.object(
        pc_automation_module.db_rom_handler,
        "apply_pc_component_metadata_candidate",
        return_value=component,
    )

    applied = await PcAutomationHandler()._apply_component(
        _rom(id=41),
        component,
        {
            "steam_id": 2138330,
            "steam_metadata": {
                "text_variants": {
                    "de": {
                        "name": "Phantom Liberty",
                        "summary": "Deutsche Beschreibung",
                        "source_language": "german",
                    }
                }
            },
        },
    )

    assert applied is True
    assert apply.call_args.args[-1]["steam_metadata"]["text_variants"] == {
        "de": {
            "name": "Phantom Liberty",
            "summary": "Deutsche Beschreibung",
            "source_language": "german",
        },
        "en": {
            "name": "Phantom Liberty",
            "summary": "English description",
            "source_language": "english",
        },
    }


@pytest.mark.asyncio
async def test_provider_failure_queues_one_retryable_item_without_overwriting_protected_data():
    rom = _rom(manual_metadata={"name": "Manual"}, name="Manual")
    matcher = Mock(fetch_unique_steam_match=AsyncMock(side_effect=TimeoutError()))
    queue = Mock(upsert_pending=Mock())
    handler = PcAutomationHandler(match_handler=matcher, queue_handler=queue)

    result = await handler.process_parent(rom)

    assert result.decision is AutomationDecision.RETRYABLE_FAILURE
    assert result.reason == "provider_failure"
    queue.upsert_pending.assert_called_once()
    assert rom.name == "Manual"
