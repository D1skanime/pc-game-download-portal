"""Description-purpose advice and dispatch under the operation retry owner."""

from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from itertools import islice

from sqlalchemy import String, cast, func, select

from config import (
    STEAM_API_COUNTRY,
    STEAM_API_FALLBACK_COUNTRY,
    STEAM_API_TEXT_LANGUAGES,
)
from config.scan_language import normalize_language
from decorators.database import begin_session
from handler.database.scan_inventory_state import _current, _digest, _find
from handler.metadata.description_completeness import assess_description_completeness
from handler.metadata.steam_descriptions import valid_app_id
from handler.metadata.steam_handler import STEAM_PLATFORMS
from handler.scan_metadata_retry_policy import (
    RetryCandidate,
    RetryIdentity,
    RetryState,
    assess_retry,
    observe_outcome,
)

MAX_DESCRIPTION_TARGETS_PER_GAME = 8
DESCRIPTION_PAGE_SIZE = 64


@dataclass(frozen=True)
class DescriptionTarget:
    component_id: int | None
    provider: str
    provider_id: int
    updated_at: datetime
    current: dict
    platform_slug: str
    fs_name: str


def snapshot_policy(policy):
    captured = deepcopy(policy)
    # Accepted requests own the language. Never consult mutable global priorities.
    captured["metadata_locale"] = (
        normalize_language(policy.get("metadata_locale")) or "en"
    )
    captured["description_languages"] = tuple(
        dict.fromkeys(
            locale
            for value in islice(
                policy.get("description_languages", STEAM_API_TEXT_LANGUAGES), 64
            )
            if (locale := normalize_language(value))
        )
    )
    captured["description_country"] = policy.get(
        "description_country", STEAM_API_COUNTRY
    )
    captured["description_fallback_country"] = policy.get(
        "description_fallback_country", STEAM_API_FALLBACK_COUNTRY
    )
    return captured


def target_from_rom(rom):
    provider = "steam" if rom.platform_slug in STEAM_PLATFORMS else "ss"
    provider_id = getattr(rom, provider + "_id", None)
    if not valid_app_id(provider_id):
        return None
    return DescriptionTarget(
        None,
        provider,
        provider_id,
        rom.updated_at,
        {
            provider + "_id": provider_id,
            provider
            + "_metadata": deepcopy(getattr(rom, provider + "_metadata", None)),
            "manual_metadata": deepcopy(rom.manual_metadata),
        },
        rom.platform_slug,
        rom.fs_name,
    )


def description_identity(coordinator, binding, target):
    target_key = (
        "parent" if target.component_id is None else f"component:{target.component_id}"
    )
    policy = coordinator.policy
    return RetryIdentity(
        binding,
        target.provider,
        f"descriptions:v1:{target.provider_id}:{target_key}",
        policy["metadata_locale"],
        _digest(
            [
                target.provider,
                target.provider in coordinator.sources(),
                policy["metadata_locale"],
                policy["description_languages"],
                policy["description_country"],
                policy["description_fallback_country"],
            ]
        ),
        purpose="description",
    )


def completeness(policy, target, current=None):
    return assess_description_completeness(
        target.current if current is None else current,
        policy["description_languages"],
        policy["metadata_locale"],
        provider=target.provider,
    )


@begin_session
def get_description_retry_state(identity, *, session=None):
    from models.scan_inventory import ScanMetadataRetry

    if not _current(session, identity.binding):
        return None
    row = _find(session, ScanMetadataRetry, identity.fields())
    return RetryState.from_record(identity, row) if row else None


@begin_session
def description_binding_current(binding, *, session=None):
    return _current(session, binding)


@begin_session
def get_description_component_page(rom, *, after=None, session=None):
    """Inspect a bounded page of existing validated component identities."""
    from models.rom import RomComponent, RomComponentMetadata
    from models.scan_inventory import ScanMetadataRetry

    attempted = (
        select(func.max(ScanMetadataRetry.last_invoked_at))
        .where(
            ScanMetadataRetry.rom_id == rom.id,
            ScanMetadataRetry.normalized_query
            == func.concat(
                "descriptions:v1:",
                cast(RomComponentMetadata.steam_id, String),
                ":component:",
                cast(RomComponent.id, String),
            ),
        )
        .correlate(RomComponent, RomComponentMetadata)
        .scalar_subquery()
    )
    stamp = func.coalesce(attempted, datetime(1970, 1, 1))
    query = (
        select(RomComponent, RomComponentMetadata, stamp.label("attempted"))
        .join(
            RomComponentMetadata, RomComponentMetadata.component_id == RomComponent.id
        )
        .where(RomComponent.rom_id == rom.id, RomComponentMetadata.steam_id > 0)
        .order_by(stamp, RomComponent.id)
        .limit(DESCRIPTION_PAGE_SIZE)
    )
    if after is not None:
        from sqlalchemy import and_, or_

        query = query.where(
            or_(stamp > after[0], and_(stamp == after[0], RomComponent.id > after[1]))
        )
    page = session.execute(query).all()
    targets = [
        DescriptionTarget(
            component.id,
            "steam",
            metadata.steam_id,
            component.updated_at,
            {
                "steam_id": metadata.steam_id,
                "steam_metadata": deepcopy(metadata.steam_metadata),
                "manual_metadata": deepcopy(metadata.manual_metadata),
            },
            rom.platform_slug,
            rom.fs_name,
        )
        for component, metadata, _ in page
    ]
    cursor = (page[-1].attempted, page[-1][0].id) if page else None
    return targets, cursor


def collect_descriptions(coordinator, quick, rom, command, *, targets=None):
    from handler.scan_retry_execution import RetryWork

    if quick.binding is None:
        return
    binding = quick.binding
    parent = target_from_rom(rom)
    due = []

    def offer(target):
        if target is None or completeness(coordinator.policy, target).complete:
            return
        identity = description_identity(coordinator, binding, target)
        state = get_description_retry_state(identity)
        advice = assess_retry(
            identity,
            state,
            baseline_adopted_at=None,
            clock=coordinator.clock,
            configured=target.provider in coordinator.sources(),
        )
        if advice.eligible:
            due.append((target, identity, state, advice))

    if targets is not None:
        for target in islice(targets, DESCRIPTION_PAGE_SIZE):
            offer(target)
    else:
        offer(parent)
        if rom.platform_slug in STEAM_PLATFORMS and "steam" in coordinator.sources():
            after = None
            while len(due) < MAX_DESCRIPTION_TARGETS_PER_GAME:
                page, after = get_description_component_page(rom, after=after)
                for target in page:
                    offer(target)
                    if len(due) >= MAX_DESCRIPTION_TARGETS_PER_GAME:
                        break
                if len(page) < DESCRIPTION_PAGE_SIZE:
                    break
    due.sort(
        key=lambda item: (
            item[0].component_id is not None,
            (
                item[2].last_invoked_at
                if item[2] and item[2].last_invoked_at
                else datetime.min
            ),
            item[0].component_id or 0,
        )
    )
    for target, identity, state, advice in due[:MAX_DESCRIPTION_TARGETS_PER_GAME]:
        coordinator.candidates.append(RetryCandidate(identity, advice))
        coordinator.states[identity.key] = state
        coordinator.description_targets[identity.key] = target
        coordinator.identities[
            (rom.id, target.provider, "description", target.component_id)
        ] = identity
        coordinator.work[identity.game_key] = RetryWork(quick, rom.id, command)


def description_outcome(
    identity, previous, observation, *, complete, clock, cause=None
):
    facts = dict(observation)
    requested = facts.get("requests", 0)
    if cause or facts.get("outcome") == "failed":
        outcome = "transient"
    elif facts.get("cached") and not requested:
        outcome = "cache_hit"
    elif not facts.get("invoked"):
        outcome = "not_invoked"
    else:
        outcome = "matched" if complete else "no_match"

    def timestamp(name):
        value = facts.get(name)
        return datetime.fromisoformat(value) if value else None

    now = clock()
    delay = facts.get("retry_after_seconds")
    state = observe_outcome(
        identity,
        previous,
        outcome=outcome,
        clock=clock,
        invoked_at=timestamp("invoked_at"),
        request_at=timestamp("request_at"),
        retry_after=now + timedelta(seconds=delay) if delay is not None else None,
    )
    # Empty/no-op attempts still defer repair, without inventing HTTP evidence.
    if (
        not complete
        and not requested
        and (
            state.next_eligible_at is None
            or state.next_eligible_at.replace(tzinfo=None) <= now.replace(tzinfo=None)
        )
    ):
        state = replace(
            state, next_eligible_at=now.replace(tzinfo=None) + timedelta(hours=24)
        )
    return state


async def dispatch_description(coordinator, work, identity):
    from handler import metadata
    from handler.database import db_rom_handler
    from handler.database.scan_write_fence import require_scan_write_context
    from handler.metadata.pc_steam_enrichment import (
        SteamPcEnrichmentRequest,
        resolve_steam_pc_enrichment,
    )
    from handler.scan_operation_checkpoint import bind_checkpoint_command
    from handler.scan_operation_worker import check_worker_boundary
    from utils.scan_provider_observation import (
        bind_provider_observation,
        mark_provider_invoked,
    )

    check_worker_boundary()
    if not description_binding_current(identity.binding):
        return
    rom = db_rom_handler.get_rom(work.rom_id)
    target = coordinator.description_targets[identity.key]
    if rom is None or rom.incarnation_token != identity.binding.rom_incarnation:
        return
    current = target_from_rom(rom)
    if target.component_id is not None:
        component = db_rom_handler.get_pc_component_by_id(rom.id, target.component_id)
        if component is None or component.component_metadata is None:
            return
        data = component.component_metadata
        current = replace(
            target,
            updated_at=component.updated_at,
            current={
                "steam_id": data.steam_id,
                "steam_metadata": deepcopy(data.steam_metadata),
                "manual_metadata": deepcopy(data.manual_metadata),
            },
            provider_id=data.steam_id,
        )
    if (
        current is None
        or current.provider_id != target.provider_id
        or current.updated_at != target.updated_at
        or identity.provider not in coordinator.sources()
        or completeness(coordinator.policy, current).complete
    ):
        return
    previous = get_description_retry_state(identity) or coordinator.states.get(
        identity.key
    )
    if not assess_retry(
        identity, previous, baseline_adopted_at=None, clock=coordinator.clock
    ).eligible:
        return
    context = require_scan_write_context()
    cause = None
    patch = {}
    with bind_checkpoint_command(work.command), bind_provider_observation(
        identity.provider,
        identity.game_key,
        operation_id=context.operation_id,
        attempt_id=context.attempt_id,
    ) as observation:
        mark_provider_invoked()
        try:
            if identity.provider == "steam":
                patch = await resolve_steam_pc_enrichment(
                    SteamPcEnrichmentRequest(
                        scan_context="description_retry",
                        current=current.current,
                        platform_slug=current.platform_slug,
                        fs_name=current.fs_name,
                        metadata_sources=("steam",),
                        explicit_steam_id=current.provider_id,
                        metadata_locale=coordinator.policy["metadata_locale"],
                        descriptions_only=True,
                        text_languages=coordinator.policy["description_languages"],
                    )
                )
            else:
                patch = dict(
                    await metadata.meta_ss_handler.get_rom_by_id(
                        rom,
                        current.provider_id,
                        metadata_locale=coordinator.policy["metadata_locale"],
                        descriptions_only=True,
                    )
                )
        except Exception as error:
            cause = type(error).__name__
        observation.outcome = (
            "failed" if cause else ("matched" if patch else "no_match")
        )
    facts = asdict(observation)
    for field in ("invoked_at", "request_at"):
        facts[field] = facts[field].isoformat() if facts[field] else None
    prior = getattr(work.quick, "automation_observation", None) or {}
    work.quick.automation_observation = {
        **facts,
        "requests": prior.get("requests", 0) + facts["requests"],
        "invoked": bool(prior.get("invoked") or facts["invoked"]),
        "cached": bool(prior.get("cached") or facts["cached"]),
    }
    complete = completeness(
        coordinator.policy, current, {**current.current, **patch}
    ).complete
    state = description_outcome(
        identity,
        previous,
        facts,
        complete=complete,
        clock=coordinator.clock,
        cause=cause,
    )
    check_worker_boundary()
    # The canonical writer owns both mutations in one checked transaction.
    applied = db_rom_handler.apply_description_patch(
        binding=identity.binding,
        component_id=current.component_id,
        provider=identity.provider,
        provider_id=current.provider_id,
        expected_updated_at=current.updated_at,
        data=patch,
        retry_state=state,
        expected_text_digest=_digest(current.current),
    )
    if applied:
        coordinator.states[identity.key] = state
