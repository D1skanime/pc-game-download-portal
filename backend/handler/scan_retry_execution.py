"""Operation-wide unknown retries through existing metadata-only execution."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from decorators.database import begin_session
from handler.database import db_rom_handler
from handler.database.scan_inventory_state import (
    InventoryBinding,
    _current,
    _digest,
    _enlist,
    _find,
    load_baseline,
    load_retry_states,
    record_retry_outcome,
)
from handler.scan_inventory_contracts import InventoryAssessment, QuickScanDecision
from handler.scan_metadata_retry_policy import (
    RetryCandidate,
    RetryIdentity,
    RetryState,
    assess_retry,
    observe_outcome,
    select_retries,
)
from handler.scan_operation_checkpoint import (
    bind_checkpoint_command,
    current_checkpoint_command,
)
from handler.scan_operation_worker import check_worker_boundary
from models.scan_inventory import ScanInventoryBaseline

_CURRENT = ContextVar("scan_retry_coordinator", default=None)


@contextmanager
def bind_retry_coordinator(coordinator):
    token = _CURRENT.set(coordinator)
    try:
        yield coordinator
    finally:
        _CURRENT.reset(token)


def configured_sources(policy):
    from handler import metadata

    return [
        str(provider)
        for provider in policy.get("apis", [])
        if getattr(metadata, "meta_" + str(provider) + "_handler", None) is not None
        and getattr(metadata, "meta_" + str(provider) + "_handler").is_enabled()
        and (provider != "playmatch" or policy.get("playmatch_enabled", True))
    ]


@begin_session
def baseline_completed_at(binding, *, session=None):
    row = _find(session, ScanInventoryBaseline, binding.fields())
    return row.completed_at if row is not None and row.reusable else None


@dataclass
class RetryWork:
    quick: object
    rom_id: int
    command: object


class RetryCoordinator:
    def __init__(self, policy, *, clock=lambda: datetime.now(timezone.utc)):
        from handler.scan_description_retry import snapshot_policy

        self.policy = snapshot_policy(policy)
        self.clock = clock
        self.candidates = []
        self.work = {}
        self.states = {}
        self.identities = {}
        self.selection: tuple[RetryCandidate, ...] = ()
        self.attention_games = set()
        self.description_targets = {}

    def sources(self):
        return configured_sources(self.policy)

    def consider_descriptions(self, quick, rom, command, *, targets=None):
        from handler.scan_description_retry import collect_descriptions

        collect_descriptions(self, quick, rom, command, targets=targets)

    def identity(self, binding, provider, query):
        locale = self.policy.get("metadata_locale") or "en-US"
        fingerprint = _digest(
            [
                str(provider),
                str(provider) in configured_sources(self.policy),
                locale,
                self.policy.get("launchbox_remote_enabled", True),
                self.policy.get("playmatch_enabled", True),
            ]
        )
        return RetryIdentity(binding, str(provider), query, locale, fingerprint)

    def consider(self, quick, rom, command):
        if quick.binding is None or quick.decision != QuickScanDecision.METADATA_ONLY:
            return
        rows = load_retry_states(quick.binding)
        sources = configured_sources(self.policy)
        if not sources:
            self.attention_games.add(_digest(quick.binding.fields()))
        for provider in sources:
            identity = self.identity(quick.binding, provider, rom.fs_name)
            previous = next(
                (row for row in rows if row.identity_digest == identity.key), None
            )
            state = RetryState.from_record(identity, previous) if previous else None
            if state is None:
                blocked = next(
                    (
                        row
                        for row in rows
                        if row.provider == provider
                        and row.config_fingerprint == identity.config_fingerprint
                        and row.config_blocked
                    ),
                    None,
                )
                if blocked is not None:
                    state = RetryState(identity, config_blocked=True)
            assessment = assess_retry(
                identity,
                state,
                baseline_adopted_at=baseline_completed_at(quick.binding),
                clock=self.clock,
            )
            self.candidates.append(RetryCandidate(identity, assessment))
            self.states[identity.key] = state
            self.identities[(rom.id, provider)] = identity
            self.work[identity.game_key] = RetryWork(quick, rom.id, command)

    async def revalidate(self, work, *, purpose="unknown"):
        from handler.filesystem.roms_handler import FSRomsHandler
        from handler.storage.read_context import MappingReadContext
        from handler.windows_quick_policy import is_identified_windows

        check_worker_boundary()
        rom = db_rom_handler.get_rom(work.rom_id)
        binding = work.quick.binding
        if (
            rom is None
            or rom.incarnation_token != binding.rom_incarnation
            or (purpose == "unknown" and is_identified_windows(rom))
        ):
            return False
        mapping = MappingReadContext(
            binding.mapping_id, binding.mapping_revision
        ).validate()
        if purpose == "description":
            from handler.metadata.steam_handler import STEAM_PLATFORMS
            from handler.scan_description_retry import description_binding_current

            if rom.platform_slug not in STEAM_PLATFORMS:
                return description_binding_current(binding)
        handler = FSRomsHandler.for_mapping(mapping, binding.game_relative_path)
        current = await handler.get_pc_inventory(rom)
        baseline = load_baseline(binding, current)
        return (
            baseline is not None
            and InventoryAssessment.compare(current, baseline).state == "unchanged"
        )

    async def run(self, dispatch):
        from handler.scan_inventory_status import emit_retry_status

        self.selection = select_retries(self.candidates)
        await emit_retry_status(self)
        descriptions = [
            item
            for item in self.selection
            if item.assessment.eligible and item.identity.purpose == "description"
        ]
        selected: dict[str, list[str]] = {}
        for item in self.selection:
            if item.assessment.eligible and item.identity.purpose == "unknown":
                selected.setdefault(item.identity.game_key, []).append(
                    item.identity.provider
                )
        for game, providers in selected.items():
            check_worker_boundary()
            work = self.work[game]
            if not await self.revalidate(work):
                continue
            binding = work.quick.binding
            rows = load_retry_states(binding)
            configured = configured_sources(self.policy)
            eligible = []
            for provider in providers:
                identity = self.identities[(work.rom_id, provider)]
                row = next(
                    (row for row in rows if row.identity_digest == identity.key), None
                )
                state = (
                    RetryState.from_record(identity, row)
                    if row
                    else self.states.get(identity.key)
                )
                if assess_retry(
                    identity,
                    state,
                    baseline_adopted_at=baseline_completed_at(binding),
                    clock=self.clock,
                    configured=provider in configured,
                ).eligible:
                    eligible.append(provider)
            if not eligible:
                continue
            command = replace(
                work.command,
                scan_type="complete",
                options=(("relative_path", binding.game_relative_path),),
            )
            with bind_checkpoint_command(command):
                await dispatch(
                    command,
                    metadata_sources=eligible,
                    roms_ids=[work.rom_id],
                    metadata_only=True,
                    media_only=False,
                    metadata_locale=self.policy.get("metadata_locale"),
                    launchbox_remote_enabled=self.policy.get(
                        "launchbox_remote_enabled", True
                    ),
                    playmatch_enabled=self.policy.get("playmatch_enabled", True),
                )
            await emit_retry_status(self, game=game)

        from handler.scan_description_retry import dispatch_description

        for item in descriptions:
            work = self.work[item.identity.game_key]
            if await self.revalidate(work, purpose="description"):
                await dispatch_description(self, work, item.identity)
                await emit_retry_status(self, game=item.identity.game_key)

    def observe(self, provider, rom, observation, cause):
        if (
            observation is None
            or rom is None
            or str(provider) not in self.policy.get("apis", [])
        ):
            return
        from pathlib import PurePosixPath

        from handler.storage.read_context import MappingReadContext
        from handler.windows_quick_execution import (
            current_windows_quick,
            inventory_binding,
        )

        identity = self.identities.get((rom.id, str(provider)))
        if identity is None:
            quick = current_windows_quick()
            command = current_checkpoint_command()
            if quick is None and (
                command is None
                or rom.platform_slug != "win"
                or command.scan_type not in {"unmatched", "complete", "update"}
            ):
                return
            binding = quick.binding if quick is not None else None
            if binding is None:
                command = current_checkpoint_command()
                mapping = MappingReadContext(
                    command.mapping_id, command.expected_revision
                ).validate()
                path = (
                    (PurePosixPath(rom.fs_path) / rom.fs_name)
                    .relative_to(mapping.relative_path)
                    .as_posix()
                )
                binding = inventory_binding(rom, path)
            identity = self.identity(binding, provider, rom.fs_name)
        check_worker_boundary()
        previous = self.states.get(identity.key)
        if previous is None:
            row = next(
                (
                    row
                    for row in load_retry_states(identity.binding)
                    if row.identity_digest == identity.key
                ),
                None,
            )
            previous = RetryState.from_record(identity, row) if row else None

        def timestamp(name):
            value = observation.get(name)
            return datetime.fromisoformat(value) if value else None

        outcome = observation["outcome"]
        if observation["cached"] and not observation["requests"]:
            outcome = "cache_hit"
        elif cause:
            outcome = "transient"
        elif not observation["invoked"]:
            outcome = "not_invoked"
        elif outcome == "failed":
            outcome = "transient"
        elif outcome not in {"matched", "no_match"}:
            outcome = "unknown"
        now = self.clock()
        delay = observation.get("retry_after_seconds")
        state = observe_outcome(
            identity,
            previous,
            outcome=outcome,
            clock=self.clock,
            invoked_at=timestamp("invoked_at"),
            request_at=timestamp("request_at"),
            retry_after=now + timedelta(seconds=delay) if delay is not None else None,
        )
        record_retry_outcome(identity.binding, **state.persistence())
        self.states[identity.key] = state


def current_retry_coordinator():
    return _CURRENT.get()


def consider_unknown_retry(quick, rom):
    coordinator = _CURRENT.get()
    if coordinator is not None:
        coordinator.consider(quick, rom, current_checkpoint_command())


def observe_retry_result(provider, rom, observation, cause):
    coordinator = _CURRENT.get()
    if coordinator is not None:
        coordinator.observe(str(provider), rom, observation, cause)


@begin_session
def invalidate_refresh_baselines(command, policy, *, session=None):
    """Explicit file refresh cannot reuse an earlier successful baseline."""
    from handler.database.scan_write_fence import checked_scan_write

    if policy.get("metadata_only") or policy.get("media_only"):
        return
    if command.scan_type not in {"complete", "hashes", "update"} and not policy.get(
        "roms_ids"
    ):
        return
    query = select(ScanInventoryBaseline).where(
        ScanInventoryBaseline.mapping_id == command.mapping_id,
        ScanInventoryBaseline.mapping_revision == command.expected_revision,
        ScanInventoryBaseline.reusable.is_(True),
    )
    relative = dict(command.options).get("relative_path")
    if relative is not None:
        query = query.where(ScanInventoryBaseline.game_relative_path == relative)
    if policy.get("roms_ids"):
        query = query.where(ScanInventoryBaseline.rom_id.in_(policy["roms_ids"]))
    with checked_scan_write(session) as operation:
        for row in session.scalars(query):
            binding = InventoryBinding(
                **{
                    name: getattr(row, name)
                    for name in InventoryBinding.__dataclass_fields__
                }
            )
            if _current(session, binding):
                _enlist(session, binding, operation)
                row.reusable = False
        session.flush()
