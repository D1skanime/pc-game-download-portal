---
phase: 22
plan: 06
status: prepared-awaiting-browser-checkpoint
scope: isolated-synthetic-pc-library
---

# Phase 22 Isolated PC Automation UAT

## Safety Boundary

This procedure uses one newly created temporary directory and only text-file
fixtures with PC-like names. The temporary source-library bind is read-only.
Do not use a NAS path, Team4s path, production library, or any real game file.
Do not edit the repository Docker Compose source. Do not write, rename, move,
or delete anything under the fixture after its pre-run evidence is captured.

The existing isolated Phase 10 Compose definition is used only as a read-only
base with a unique project name and a temporary, untracked environment override.
The override contains configuration switches only. It must not contain a secret.
Provider credentials remain in the local backend environment and must never be
printed, copied to this record, or added to a Compose file.

## Temporary Fixture Contract

Create this exact structure below a new `mktemp -d` directory. Every file is a
small text file, despite its extension.

```text
library/roms/win/Safe Main Title/Safe Main Title.iso
library/roms/win/Safe Main Title/DLC/Safe Main Title DLC.zip
library/roms/win/Ambiguous Title/Ambiguous Title.iso
```

Use deterministic, non-game text payloads such as `phase22-safe-main`,
`phase22-safe-dlc`, and `phase22-ambiguous`. The unambiguous title must resolve
to exactly one configured Steam candidate. The ambiguous title must resolve to
zero or multiple candidates and create exactly one pending review row.

## Evidence Capture Command

Run this command before starting the stack and again after every browser review
action. It records relative names, entry type, size, modification timestamp, and
SHA-256 for each file without referring to a real-library path.

```bash
python3 - "$UAT_ROOT/library" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
entries = []
for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
    stat = path.lstat()
    entry = {
        "path": path.relative_to(root).as_posix(),
        "type": "directory" if path.is_dir() else "file",
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if path.is_file():
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entries.append(entry)
print(json.dumps(entries, sort_keys=True, separators=(",", ":")))
PY
```

Save the command output as `before.json` and `after.json` in the temporary UAT
artifact directory. The byte-for-byte JSON comparison must succeed.

## Isolated Development Configuration

Use a unique `COMPOSE_PROJECT_NAME` and the temporary fixture root as
`PHASE10_FIXTURE_SOURCE`. Use a temporary untracked Compose override with only:

```yaml
services:
  app:
    environment:
      DEV_MODE: "true"
      ENABLE_SCHEDULED_RESCAN: "true"
      PC_AUTOMATION_UAT_INTERVAL_SECONDS: "10"
      STEAM_API_ENABLED: "true"
```

Start only the disposable database, queue, app, and nginx services from
`backend/docker-compose.pc-integration-test.yml` plus that override. The
fixture is mounted by the base definition at `/romm/library/roms:ro`; keep that
mount read-only. Obtain the isolated service URL with the Compose `port nginx
80` command, then use the established SSH tunnel on port 3344 for browser
access. Do not expose or record credentials.

The production cron remains `*/15 * * * *`. The exact 10-second interval is
valid here only because `DEV_MODE=true`; `PC_AUTOMATION_UAT_INTERVAL_SECONDS`
must be exactly `10` and must return to the default `0` when the disposable
stack is removed.

## Browser Verification Steps

1. Register only the temporary Windows fixture root and create its mapped
   platform mapping in the isolated application.
2. Capture `before.json`, then wait at least one 10-second interval execution.
3. In v2 Administration, open **PC automation**. Confirm progress and the
   outstanding count are visible.
4. Confirm the safe main title and its DLC were enriched through the guarded
   catalog and owned-media paths. Confirm the ambiguous title appears once with
   candidate evidence and a pending reason.
5. Accept one safe pending row, correct one row through the existing match
   dialog, skip one row, then submit a mixed or stale batch. Only valid rows may
   resolve. The invalid batch must be rejected without partial application.
6. Capture `after.json` and compare it to `before.json`. Names, structure,
   sizes, modification timestamps, and SHA-256 values must be identical.
7. Run the isolated Compose cleanup using its unique project name and remove
   only the temporary UAT directory.

## Automated Preparation Evidence

| Item             | Actual isolated result                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Command          | `cd backend && uv run pytest tests/integration/test_scan_source_immutability.py -q`                                            |
| Result           | 3 passed in 0.21s, with one non-fatal local pytest-cache permission warning                                                    |
| Fixture          | Temporary pytest directory containing named text `.iso` and `.zip` files only                                                  |
| Covered paths    | Development interval delegation, safe parent application, safe DLC application, and ambiguous pending creation                 |
| Source evidence  | Relative names, directory structure, sizes, `mtime_ns`, and SHA-256 were identical before and after the automation transitions |
| Capability guard | The mapped scan contract requires `StorageOperation.SCAN` and contains no `StorageOperation.WRITE` request                     |

## Browser Evidence, Pending Checkpoint

No isolated Docker stack or browser action has been run while preparing this
record. Task 3 must append the actual unique project name, isolated URL,
pre/post digest outputs, observed queue count/progress, action outcomes, and
cleanup result. Do not mark this UAT approved until that evidence is recorded.
