"""Seed the CI library through canonical mapped scan operations."""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
)

from rq import Worker  # noqa: E402

from endpoints.sockets.scan import mapping_scan_commands  # noqa: E402
from handler.database import db_user_handler  # noqa: E402
from handler.database.scan_operations_handler import (  # noqa: E402
    DBScanOperationsHandler,
)
from handler.redis_handler import high_prio_queue, redis_client  # noqa: E402
from handler.scan_command import ScanScope, ScanTrigger  # noqa: E402
from handler.scan_handler import ScanType  # noqa: E402
from handler.setup_folder_handler import setup_folder_handler  # noqa: E402
from handler.setup_recovery import setup_recovery_handler  # noqa: E402
from tasks.scan_operation_dispatch import accept_commands  # noqa: E402


def _scan() -> int:
    actor = db_user_handler.get_user_by_username("e2e_admin")
    if actor is None:
        raise RuntimeError("Seed the E2E fixture users before the library")
    discovered = setup_folder_handler.discover_response()
    assignments = []
    for folder in discovered["folders"]:
        slug = folder["suggested_platform"]
        if not slug:
            raise RuntimeError("Unknown E2E fixture platform: " + folder["name"])
        assignments.append({"folder_name": folder["name"], "platform_slug": slug})
    setup_recovery_handler.assign(
        assignments,
        {"actor_user_id": actor.id, "actor_display_name": actor.username},
    )
    commands = mapping_scan_commands(
        [],
        trigger=ScanTrigger.MANUAL,
        scope=ScanScope.LIBRARY,
        scan_type=ScanType.QUICK,
    )
    if not commands:
        raise RuntimeError("No healthy read-only E2E fixture mappings")
    repository = DBScanOperationsHandler()
    accepted = accept_commands(actor.id, commands, {"apis": [], "type": "quick"})
    Worker([high_prio_queue], connection=redis_client).work(
        burst=True, with_scheduler=False, max_jobs=1
    )
    result = repository.execution(accepted.id)
    stats = result["scan_stats"]
    print("E2E mapped scan", result["state"], stats)
    if result["state"] != "completed" or stats.get("scanned_roms", 0) == 0:
        raise RuntimeError("E2E fixture scan did not complete with games")
    return 0


if __name__ == "__main__":
    sys.exit(_scan())
