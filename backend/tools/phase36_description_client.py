"""Authenticated API execution and guarded disposable SQL facts."""

import argparse
import asyncio
import hashlib
import json
import sys
from contextlib import closing
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase33_collection_fixture import authority
from phase35_incremental_client import catalog as inventory_catalog
from phase35_incremental_client import login, wait
from phase36_description_fixture import reset_one, seed, seed_ss_fault

EVIDENCE = Path("/phase34/evidence")


def request(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.is_error:
        print(
            "HTTP failure",
            method,
            path,
            response.status_code,
            response.text[:1200],
            flush=True,
        )
    response.raise_for_status()
    return response.json() if response.content else None


def catalog():
    from sqlalchemy import select

    from handler.database.base_handler import sync_session
    from models.rom import Rom, RomComponentMetadata
    from models.scan_inventory import ScanMetadataRetry
    from models.user import User

    result = inventory_catalog()
    with sync_session() as session:
        result["descriptions"] = [
            {
                "id": row.id,
                "name": row.fs_name,
                "summary": row.summary,
                "manual": row.manual_metadata,
                "steam_id": row.steam_id,
                "ss_id": row.ss_id,
                "steam": row.steam_metadata,
                "ss": row.ss_metadata,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in session.scalars(select(Rom).order_by(Rom.id))
        ]
        result["component_descriptions"] = [
            {
                "id": row.component_id,
                "steam_id": row.steam_id,
                "steam": row.steam_metadata,
                "manual": row.manual_metadata,
                "summary": row.summary,
            }
            for row in session.scalars(
                select(RomComponentMetadata).order_by(RomComponentMetadata.component_id)
            )
        ]
        result["auth"] = [
            {
                "id": row.id,
                "username": row.username,
                "role": str(row.role),
                "credential_digest": hashlib.sha256(
                    (row.hashed_password or "").encode()
                ).hexdigest(),
            }
            for row in session.scalars(select(User).order_by(User.id))
        ]
        result["description_retries"] = [
            {
                "id": row.id,
                "rom_id": row.rom_id,
                "query": row.normalized_query,
                "outcome": row.outcome,
                "requested": (
                    row.last_request_at.isoformat() if row.last_request_at else None
                ),
                "next": (
                    row.next_eligible_at.isoformat() if row.next_eligible_at else None
                ),
            }
            for row in session.scalars(
                select(ScanMetadataRetry).order_by(ScanMetadataRetry.id)
            )
        ]
    return result


def scheduled():
    from unittest.mock import patch

    from handler import metadata
    from tasks.scheduled import scan_library

    for name, handler in vars(metadata).items():
        if name.startswith("meta_") and hasattr(handler, "is_enabled"):
            handler.is_enabled = lambda: False
    patch.object(metadata.meta_steam_handler, "is_enabled", return_value=True).start()
    patch.object(metadata.meta_ss_handler, "is_enabled", return_value=True).start()
    patch.object(scan_library, "ENABLE_SCHEDULED_RESCAN", True).start()
    accepted = asyncio.run(scan_library.scan_library_task.run())
    if not accepted.get("operation_id"):
        raise RuntimeError("scheduler did not accept actual work")
    return accepted["operation_id"]


def accept(client, mode="quick", locale="de", apis=None, provider=None, targeted=False):
    platforms = request(client, "GET", "/api/platforms")
    ids = [
        row["id"]
        for row in platforms
        if provider is None or row["slug"] == ("win" if provider == "steam" else "snes")
    ]
    payload = {
        "request_key": str(uuid4()),
        "platforms": ids,
        "apis": ["steam", "ss", "igdb"] if apis is None else apis,
        "type": mode,
        "metadata_locale": locale,
    }
    if targeted:
        name = "Known.Game" if provider == "steam" else "Control.sfc"
        payload.update(
            roms_ids=[
                next(
                    row["id"]
                    for row in catalog()["descriptions"]
                    if row["name"] == name
                )
            ],
            metadata_only=True,
        )
    return request(client, "POST", "/api/scan-operations", json=payload)["id"]


def language(client, locale):
    current = request(client, "GET", "/api/config")
    priority = current["SCAN_LANGUAGE_PRIORITY"]
    return request(
        client,
        "PUT",
        "/api/config/scan/language",
        json={
            "language_priority": [locale, "en"] if locale != "en" else ["en"],
            "expected_language_priority": priority,
        },
    )


def interactive(client, provider, locale):
    before = catalog()
    name = "Known.Game" if provider == "steam" else "Control.sfc"
    rom = next(row for row in before["descriptions"] if row["name"] == name)
    identity = rom[provider + "_id"]
    search = {
        kind: request(
            client,
            "GET",
            "/api/search/roms",
            params={
                "rom_id": rom["id"],
                "search_term": (
                    str(identity)
                    if kind == "id"
                    else "Known Game" if provider == "steam" else "Control"
                ),
                "search_by": kind,
                "metadata_locale": locale,
            },
        )
        for kind in ("name", "id")
    }
    language(client, "fr" if locale == "de" else "de")
    response = request(
        client,
        "PUT",
        "/api/roms/" + str(rom["id"]),
        params={"metadata_locale": locale, "expected_version": rom["updated_at"]},
        data={provider + "_id": str(identity)},
    )
    reload = request(client, "GET", "/api/roms/" + str(rom["id"]))
    selected = None
    if provider == "steam":
        reset_one(provider)
        candidates = request(
            client,
            "GET",
            "/api/roms/" + str(rom["id"]) + "/pc-metadata-candidates",
            params={"query": "Known Game", "metadata_locale": locale},
        )
        candidate = next(
            row
            for row in candidates["providers"]["steam"]["candidates"]
            if row["provider_ids"].get("steam_id") == identity
        )
        selected = request(
            client,
            "POST",
            "/api/roms/" + str(rom["id"]) + "/pc-metadata-selection",
            json={
                "candidate_id": candidate["id"],
                "query": "Known Game",
                "metadata_locale": locale,
                "selected_media_ids": [],
                "expected_version": candidates["expected_version"],
            },
        )
        reload = request(client, "GET", "/api/roms/" + str(rom["id"]))
    current = catalog()
    stored = next(row for row in current["descriptions"] if row["id"] == rom["id"])
    for tag in (locale, "en"):
        if not stored[provider]["text_variants"].get(tag, {}).get("summary"):
            raise RuntimeError(
                "interactive provider locale missing after actual reload"
            )
    if stored["manual"] != rom["manual"] or stored["summary"] != rom["summary"]:
        raise RuntimeError("same-ID confirmation changed protected manual/scalar")
    return {
        "search": search,
        "response": response,
        "selection": selected,
        "reload": reload,
        "catalog": current,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "setup",
            "inspect",
            "seed",
            "ss-fault",
            "complete",
            "reset",
            "scan",
            "scheduled",
            "adopt",
            "refresh",
            "interactive",
            "authority",
            "authority-suite",
            "language",
            "auth",
            "concurrent",
        ),
    )
    parser.add_argument("--stage", default="inspect")
    parser.add_argument("--mode", default="quick")
    parser.add_argument("--locale", default="de")
    parser.add_argument("--provider", default="steam", choices=("steam", "ss"))
    args = parser.parse_args()
    authority()
    if args.action in {"seed", "complete"}:
        seed("initial" if args.action == "seed" else "complete")
        result = catalog()
    elif args.action == "ss-fault":
        seed_ss_fault()
        result = catalog()
    elif args.action == "reset":
        reset_one(args.provider)
        result = catalog()
    elif args.action == "inspect":
        result = catalog()
    else:
        with closing(login(create=args.action == "setup")) as client:
            if args.action == "setup":
                result = request(
                    client,
                    "POST",
                    "/api/setup/folders/assign",
                    json={
                        "assignments": [
                            {"folder_name": "pc", "platform_slug": "win"},
                            {"folder_name": "My Games", "platform_slug": "snes"},
                        ]
                    },
                )
            elif args.action == "language":
                result = language(client, args.locale)
            elif args.action == "interactive":
                result = interactive(client, args.provider, args.locale)
            elif args.action == "authority-suite":
                from phase36_description_authority import suite

                result = suite(client)
            elif args.action == "auth":
                from phase36_description_authority import auth_cases

                result = auth_cases(client)
            elif args.action == "concurrent":
                from phase36_description_authority import concurrent_case

                result = concurrent_case(client, args.provider)
            elif args.action == "authority":
                from phase36_description_authority import execute_case

                result = execute_case(client, args.provider, args.stage)
            else:
                identity = (
                    scheduled()
                    if args.action == "scheduled"
                    else accept(
                        client,
                        args.mode,
                        args.locale,
                        apis=[] if args.action == "adopt" else None,
                        provider=args.provider if args.action == "refresh" else None,
                        targeted=args.action == "refresh",
                    )
                )
                result = wait(client, identity)
                from config.scan_language import normalize_language
                from handler.database.base_handler import sync_session
                from models.scan_operation import ScanOperation

                with sync_session() as session:
                    result["accepted_request"] = session.get(
                        ScanOperation, identity
                    ).command["request"]
                priority = request(client, "GET", "/api/config")[
                    "SCAN_LANGUAGE_PRIORITY"
                ]
                expected_locale = (
                    (normalize_language(priority[0]) if priority else "en")
                    if args.action == "scheduled"
                    else normalize_language(args.locale) or "en"
                )
                if result["accepted_request"]["metadata_locale"] != expected_locale:
                    raise RuntimeError(
                        "accepted request changed captured metadata locale"
                    )
                result["catalog"] = catalog()
                result["api"] = {
                    str(row["id"]): request(
                        client, "GET", "/api/roms/" + str(row["id"])
                    )
                    for row in result["catalog"]["descriptions"]
                }
    (EVIDENCE / (args.stage + ".json")).write_text(json.dumps(result, indent=2))
    print("PHASE36", args.stage, result.get("state", "fixture"), flush=True)


if __name__ == "__main__":
    main()
