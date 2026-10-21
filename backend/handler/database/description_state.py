"""Narrow provider text updates in the canonical checked catalog transaction."""

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select

from handler.database.scan_inventory_state import (
    _digest,
    _enlist,
    _find,
    record_retry_outcome,
)
from handler.database.scan_write_fence import checked_scan_write
from handler.metadata.ss_descriptions import merge_ss_metadata
from handler.metadata.steam_descriptions import valid_app_id, valid_steam_provenance
from handler.metadata.steam_merge import normalize_steam
from models.rom import Rom, RomComponent, RomComponentMetadata
from models.scan_inventory import ScanMetadataRetry


def _text_metadata(provider, provider_id, current, incoming):
    old = deepcopy(dict(current)) if isinstance(current, Mapping) else {}
    new = incoming if isinstance(incoming, Mapping) else {}
    if provider == "ss":
        return merge_ss_metadata(old, new)
    if not valid_steam_provenance(new, provider_id):
        return old
    merged = normalize_steam(
        {
            "steam_id": provider_id,
            "steam_metadata": {"text_variants": new.get("text_variants")},
        },
        {"steam_id": provider_id, "steam_metadata": old},
    )["steam_metadata"]
    variants = merged.get("text_variants")
    if not variants:
        return old
    old.update(app_id=provider_id, source="storefront", text_variants=variants)
    return old


def apply_description_patch(
    *,
    binding,
    component_id,
    provider,
    provider_id,
    expected_updated_at,
    expected_text_digest,
    data,
    retry_state=None,
    expected_operation_version=None,
    session,
):
    if provider not in {"steam", "ss"} or not valid_app_id(provider_id):
        return False
    if component_id is not None and provider != "steam":
        return False
    if not isinstance(data, Mapping):
        return False
    if retry_state is not None and (
        retry_state.identity.purpose != "description"
        or retry_state.identity.binding != binding
        or retry_state.identity.provider != provider
        or retry_state.identity.query
        != (
            f"descriptions:v1:{provider_id}:"
            + ("parent" if component_id is None else f"component:{component_id}")
        )
    ):
        raise ValueError("description_retry_identity_mismatch")
    with checked_scan_write(
        session, expected_version=expected_operation_version
    ) as operation:
        _enlist(session, binding, operation)
        rom = session.scalar(
            select(Rom)
            .where(Rom.id == binding.rom_id)
            .with_for_update(of=Rom)
            .execution_options(populate_existing=True)
        )
        target = rom
        metadata = rom
        if component_id is not None:
            target = session.scalar(
                select(RomComponent)
                .where(
                    RomComponent.id == component_id,
                    RomComponent.rom_id == binding.rom_id,
                )
                .with_for_update(of=RomComponent)
                .execution_options(populate_existing=True)
            )
            metadata = session.scalar(
                select(RomComponentMetadata)
                .where(RomComponentMetadata.component_id == component_id)
                .with_for_update(of=RomComponentMetadata)
                .execution_options(populate_existing=True)
            )
        if target is None or metadata is None:
            return False
        # SQL equality preserves dialect timestamp precision, the digest also fences same-tick edits.
        model = Rom if component_id is None else RomComponent
        if (
            session.scalar(
                select(model.id).where(
                    model.id == target.id,
                    model.updated_at == expected_updated_at,
                )
            )
            is None
        ):
            return False
        if getattr(metadata, provider + "_id", None) != provider_id:
            return False
        field = provider + "_metadata"
        current = {
            provider + "_id": provider_id,
            field: deepcopy(getattr(metadata, field)),
            "manual_metadata": deepcopy(metadata.manual_metadata),
        }
        if _digest(current) != expected_text_digest:
            return False
        merged = _text_metadata(provider, provider_id, current[field], data.get(field))
        changed = merged != (current[field] or {})
        if changed:
            setattr(metadata, field, merged)
            target.updated_at = datetime.now(timezone.utc)
        retry_changed = False
        if retry_state is not None:
            row = _find(session, ScanMetadataRetry, retry_state.identity.fields())
            values = retry_state.persistence()
            retry_changed = row is None or any(
                getattr(row, stored) != values[argument]
                for stored, argument in (
                    ("outcome", "outcome"),
                    ("next_eligible_at", "next_eligible_at"),
                    ("last_invoked_at", "invoked_at"),
                    ("last_request_at", "request_at"),
                    ("no_match_streak", "no_match_streak"),
                    ("transient_streak", "transient_streak"),
                    ("config_blocked", "config_blocked"),
                )
            )
            if retry_changed:
                record_retry_outcome(binding, **values, session=session)
        session.flush()
        return changed or retry_changed
