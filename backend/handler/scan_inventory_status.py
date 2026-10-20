"""Game inventory units and concrete provider units share one aggregation owner."""

from collections.abc import Iterable

from decorators.database import begin_session

_BUCKETS = ("unchanged", "changed", "refresh_required", "incomplete")


def aggregate_inventory(games: Iterable[dict], observations: Iterable[dict]):
    """Games are full identities; provider counts are cumulative per identity/provider."""
    unique = {game["key"]: game for game in games}
    providers = {(item["key"], item["provider"]): item for item in observations}
    counts = {"inventory_" + state: 0 for state in _BUCKETS}
    unresolved = set()
    existing = set()
    for key, game in unique.items():
        counts["inventory_" + game["inventory_state"]] += 1
        if game.get("identified_windows") is False:
            unresolved.add(key)
        if game.get("existing_game") is True:
            existing.add(key)
    retry_games = set()
    requests = 0
    cache_hits = 0
    cache_observed = False
    for (key, _), observation in providers.items():
        value = observation.get("requests")
        if type(value) is int and 0 <= value <= 2147483647:
            requests += value
        if observation.get("invoked") is True and key in existing:
            retry_games.add(key)
        if type(observation.get("cached")) is bool:
            cache_observed = True
            cache_hits += int(observation["cached"])
    counts.update(
        inventory_checked=sum(counts.values()),
        unresolved_games=len(unresolved),
        metadata_retry_games=len(retry_games),
        provider_requests=requests,
    )
    if cache_observed:
        counts["metadata_cache_hits"] = cache_hits
    return counts


def provider_facts(observation):
    """A completed wrapper without observations is never request evidence."""
    from endpoints.responses.scan_operations import ScanProviderFacts

    if observation is None:
        return None
    requests = observation.get("requests")
    invoked = observation.get("invoked")
    cached = observation.get("cached")
    state = "no_request"
    if requests:
        outcome = observation.get("outcome")
        state = outcome if outcome in {"matched", "no_match", "failed"} else "requested"
    elif cached is True:
        state = "cached"
    return ScanProviderFacts(
        state=state, invoked=invoked, requests=requests, cached=cached
    )


def inventory_counts(session, operation):
    """SQL aggregates remain global without loading an unbounded result list."""
    from sqlalchemy import case, func, or_, select
    from sqlalchemy.orm import aliased

    from models.scan_operation import ScanOperationItem

    item = ScanOperationItem
    current = (
        item.operation_id == operation.id,
        item.attempt_id == operation.attempt_id,
    )
    facts = item.checkpoint["inventory_status"]
    buckets = [
        func.sum(case((facts["inventory_state"].as_string() == state, 1), else_=0))
        for state in _BUCKETS
    ]
    result = session.execute(
        select(
            *buckets,
            func.sum(
                case((facts["identified_windows"].as_boolean().is_(False), 1), else_=0)
            ),
        ).where(*current, item.provider == "")
    ).one()
    observation = item.checkpoint["provider_observation"]
    requests, cached, observed = session.execute(
        select(
            func.sum(observation["requests"].as_integer()),
            func.sum(case((observation["cached"].as_boolean().is_(True), 1), else_=0)),
            func.count(observation["requests"].as_integer()),
        ).where(*current)
    ).one()
    if not any(result[:4]) and not observed:
        return {}
    counts = {
        "inventory_" + state: int(value or 0)
        for state, value in zip(_BUCKETS, result[:4], strict=True)
    }
    game = aliased(item)
    retries = session.scalar(
        select(func.count(func.distinct(game.target_key)))
        .select_from(game)
        .join(
            item,
            (item.operation_id == game.operation_id)
            & (item.attempt_id == game.attempt_id)
            & (item.mapping_id == game.mapping_id)
            & (item.expected_revision == game.expected_revision)
            & (item.relative_path == game.relative_path)
            & (
                item.checkpoint["rom_id"].as_integer()
                == game.checkpoint["rom_id"].as_integer()
            ),
        )
        .where(
            game.operation_id == operation.id,
            game.attempt_id == operation.attempt_id,
            game.provider == "",
            or_(item.provider != "", item.id == game.id),
            game.checkpoint["inventory_status"]["existing_game"].as_boolean().is_(True),
            observation["invoked"].as_boolean().is_(True),
        )
    )
    counts.update(
        inventory_checked=sum(counts.values()),
        unresolved_games=int(result[4] or 0),
        metadata_retry_games=int(retries or 0),
        provider_requests=int(requests or 0),
    )
    if observed:
        counts["metadata_cache_hits"] = int(cached or 0)
    return counts


def item_facts(item):
    from endpoints.responses.scan_operations import (
        ScanInventoryFacts,
        ScanOperationItemResult,
    )

    result = ScanOperationItemResult.model_validate(item)
    status = item.checkpoint.get("inventory_status")
    inventory = (
        ScanInventoryFacts.model_validate(status) if status is not None else None
    )
    return result.model_copy(
        update={
            "inventory": inventory,
            "provider_execution": provider_facts(
                item.checkpoint.get("provider_observation")
            ),
        }
    )


def record_inventory_status(binding, **facts):
    """Persist through the existing transaction and full inventory binding owner."""
    from handler.filesystem.owned_writer_domain import owned_writer_domain

    with owned_writer_domain():
        return _record_inventory_status(binding, **facts)


@begin_session
def _record_inventory_status(
    binding, *, session=None, provider_observation=None, **facts
):
    from sqlalchemy import select

    from endpoints.responses.scan_operations import ScanInventoryFacts
    from handler.database.scan_inventory_state import _digest, _enlist
    from handler.database.scan_operation_lifecycle import observe_execution
    from handler.database.scan_write_fence import checked_scan_write
    from models.scan_operation import ScanOperationItem

    provider_facts(provider_observation)
    validated = ScanInventoryFacts(rom_id=binding.rom_id, **facts)
    status = validated.model_dump(mode="json")
    with checked_scan_write(session) as operation:
        _enlist(session, binding, operation)
        key = "inventory-" + _digest(binding.fields())
        item = session.scalar(
            select(ScanOperationItem).where(
                ScanOperationItem.operation_id == operation.id,
                ScanOperationItem.target_key == key,
                ScanOperationItem.provider == "",
            )
        )
        evidence = {"inventory_binding": binding.fields()}
        if item is not None and item.source_evidence != evidence:
            raise ValueError("inventory_identity_collision")
        checkpoint = {"rom_id": binding.rom_id, "inventory_status": status}
        if provider_observation is None and item is not None:
            provider_observation = item.checkpoint.get("provider_observation")
        if provider_observation is not None:
            checkpoint["provider_observation"] = provider_observation
        values = dict(
            target_key=key,
            mapping_id=binding.mapping_id,
            expected_revision=binding.mapping_revision,
            relative_path=binding.game_relative_path,
            provider="",
            outcome="skipped",
            attempt_id=operation.attempt_id,
            checkpoint=checkpoint,
            source_evidence=evidence,
        )
        if item is None:
            item = ScanOperationItem(operation_id=operation.id, **values)
            session.add(item)
        else:
            for name, value in values.items():
                setattr(item, name, value)
        session.flush()
        observe_execution(
            session,
            operation,
            {
                "scan_stats": operation.scan_stats
                | inventory_counts(session, operation),
            },
        )
        return item_facts(item)


def retry_facts(binding, identified):
    from handler.database.scan_inventory_state import _digest
    from handler.scan_metadata_retry_policy import assess_retry
    from handler.scan_retry_execution import (
        baseline_completed_at,
        current_retry_coordinator,
    )

    coordinator = current_retry_coordinator()
    if coordinator is None or identified:
        return {}
    if _digest(binding.fields()) in coordinator.attention_games:
        return {"retry_state": "configuration_blocked", "retry_eligible": False}
    candidates = coordinator.selection or coordinator.candidates
    assessments = []
    for candidate in candidates:
        identity = candidate.identity
        if identity.binding != binding:
            continue
        state = coordinator.states.get(identity.key)
        assessment = candidate.assessment
        if state is not None and assessment.reason != "budget_deferred":
            assessment = assess_retry(
                identity,
                state,
                baseline_adopted_at=baseline_completed_at(binding),
                clock=coordinator.clock,
            )
        assessments.append(assessment)
    if not assessments:
        return {}
    chosen = min(
        assessments,
        key=lambda item: (
            not item.eligible,
            item.reason == "configuration_blocked",
            item.due_at.isoformat() if item.due_at else "",
        ),
    )
    return {
        "retry_eligible": chosen.eligible,
        "retry_state": chosen.reason,
        "next_eligible_at": chosen.due_at,
    }


async def emit_inventory_status(manager, quick, rom, *, existing_game):
    from endpoints.responses.rom import SimpleRomSchema
    from handler.database.scan_write_fence import current_scan_write_context
    from handler.scan_inventory_contracts import InventoryAssessment, QuickScanDecision
    from handler.windows_quick_policy import is_identified_windows

    if (
        current_scan_write_context() is None
        or quick is None
        or getattr(quick, "binding", None) is None
    ):
        return
    assessment = quick.assessment
    if assessment is None:
        state = {
            QuickScanDecision.REUSE: "unchanged",
            QuickScanDecision.METADATA_ONLY: "unchanged",
            QuickScanDecision.REFRESH: "refresh_required",
            QuickScanDecision.INCOMPLETE: "incomplete",
        }[quick.decision]
        assessment = InventoryAssessment(state, quick.before.reason)  # type: ignore[arg-type]
    identified = is_identified_windows(rom)
    item = record_inventory_status(
        quick.binding,
        inventory_state=assessment.state,
        inventory_reason=assessment.reason or None,
        identified_windows=identified,
        existing_game=existing_game,
        provider_observation=getattr(quick, "automation_observation", None),
        **retry_facts(quick.binding, identified),
    )
    from handler.database import db_rom_handler

    hydrated = db_rom_handler.get_rom(rom.id)
    if hydrated is None or hydrated.incarnation_token != rom.incarnation_token:
        from handler.database.scan_write_fence import ScanWriteRejected

        raise ScanWriteRejected("inventory_rom_changed")
    payload = SimpleRomSchema.from_orm_with_factory(hydrated).model_dump(
        exclude={
            "created_at",
            "updated_at",
            "rom_user",
            "last_modified",
            "files",
            "sibling_roms",
        }
    )
    payload.update(
        is_identifying=False,
        is_unidentified=not identified,
        inventory=item.inventory.model_dump(mode="json"),
    )
    await manager.emit("scan:scanning_rom", payload)


async def emit_retry_status(coordinator, *, game=None):
    from endpoints.sockets.scan import _get_socket_manager
    from handler.database import db_rom_handler
    from handler.scan_operation_worker import active_scan_worker

    if not active_scan_worker():
        return
    for identity, work in coordinator.work.items():
        if game is not None and identity != game:
            continue
        rom = db_rom_handler.get_rom(work.rom_id)
        if rom is not None:
            await emit_inventory_status(
                _get_socket_manager(), work.quick, rom, existing_game=True
            )
