"""Bind public scan choices to existing immutable mapped scan commands."""

from dataclasses import asdict

from endpoints.responses.scan_operations import ScanOperationRequest
from handler.database import db_platform_handler, db_rom_handler
from handler.filesystem.storage_policy import StorageOperation
from handler.scan_command import ScanScope, ScanTrigger
from handler.storage.read_context import MappingReadContext


def canonical_request(body: ScanOperationRequest) -> dict:
    payload = body.model_dump(exclude={"request_key"})
    if payload.get("collection_promotion") is None:
        payload.pop("collection_promotion", None)
    for key in ("platforms", "platform_fs_slugs", "roms_ids", "apis"):
        payload[key] = sorted(set(payload[key]))
    return payload


def normalize_scan_request(body: ScanOperationRequest) -> dict:
    from endpoints.sockets.scan import mapping_scan_commands
    from handler.scan_handler import MetadataSource, ScanType

    payload = canonical_request(body)
    if any(
        provider not in {source.value for source in MetadataSource}
        for provider in body.apis
    ):
        raise ValueError("unknown_metadata_provider")
    platforms = list(db_platform_handler.get_platforms())
    ids, slugs = set(body.platforms), set(body.platform_fs_slugs)
    if ids - {p.id for p in platforms} or slugs - {p.fs_slug for p in platforms}:
        raise ValueError("unknown_scan_platform")
    selected = [
        p
        for p in platforms
        if (p.id in ids if ids else not slugs or p.fs_slug in slugs)
    ]
    if set(body.filesystem_scope_paths) - {p.fs_slug for p in selected}:
        raise ValueError("scope_outside_selection")
    commands = mapping_scan_commands(
        payload["platforms"],
        trigger=ScanTrigger.MANUAL,
        scope=ScanScope.ROM if body.roms_ids else ScanScope.PLATFORM,
        scan_type=ScanType(body.type),
        platform_fs_slugs=payload["platform_fs_slugs"],
        filesystem_scope_paths=body.filesystem_scope_paths,
    )
    if not commands:
        raise ValueError("missing_scan_scope")
    mapped_platforms = set()
    for command in commands:
        context = MappingReadContext(command.mapping_id, command.expected_revision)
        mapping = context.validate()
        mapped_platforms.add(mapping.platform_id)
        relative = dict(command.options).get("relative_path", "")
        with context.open(StorageOperation.RESOLVE, relative):
            pass
    if (ids or slugs) and mapped_platforms != {p.id for p in selected}:
        raise ValueError("mapping_not_ready")
    for identity in body.roms_ids:
        rom = db_rom_handler.get_rom(identity)
        if rom is None or rom.platform_id not in mapped_platforms:
            raise ValueError("rom_outside_scan_scope")
    from handler.scan_collection_policy import get_validated_promotion

    promotion = get_validated_promotion(body, commands)
    normalized = {
        "commands": [asdict(command) for command in commands],
        "request": payload,
    }
    if promotion is not None:
        normalized["collection_promotion"] = promotion
    return normalized
