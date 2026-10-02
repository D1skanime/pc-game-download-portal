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

## Required 20-File DLC Layout

The fresh browser UAT uses 20 synthetic text files with real-title names, but
the Cyberpunk pair has one mandatory scanner-compatible shape. It is one parent
directory and one DLC child directory, never two sibling ROM fixtures:

```text
library/roms/win/Cyberpunk 2077/Cyberpunk 2077.iso
library/roms/win/Cyberpunk 2077/dlc/Phantom Liberty/Phantom Liberty.zip
```

Do not create a flat sibling such as `win/Cyberpunk 2077: Phantom Liberty.zip`.
That shape is intentionally a second parent ROM and cannot exercise DLC
component scanning. The other 18 text-only files may cover the established
real-title cases. Capture their complete manifest before starting the stack.

Before opening the browser queue, query the disposable catalog or authenticated
API and record these non-secret assertions:

1. exactly one parent ROM is named Cyberpunk 2077;
2. that parent exposes a `dlc/Phantom Liberty` component of kind `DLC`;
3. no second Cyberpunk parent exists for Phantom Liberty.

For Steam app ids `1091500` and `2138330`, also record that the disposable
catalog summary is the German Storefront description, with Steam provenance
`language=german` and without `summary` in `fallback_fields`. Do not record
provider credentials, session credentials, full API responses, or real paths.

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

## Fresh Manual-Correction Proof

Run this proof only in a new disposable project. Do not reuse a running UAT
database, fixture directory, volume, or Compose project.

1. Create a new `mktemp -d` root containing the established 20 text-only
   Windows fixtures. The fixture names may use real title text, but the file
   contents must be synthetic text only. Use the fixture root's `roms` child
   as `PHASE10_FIXTURE_SOURCE` and mount it read-only.
2. Select a unique `COMPOSE_PROJECT_NAME` of the form
   `romm-phase22-correction-<timestamp>`. Create an untracked environment
   override under that same temporary root. The override sets only
   `DEV_MODE=true`, `PC_AUTOMATION_UAT_INTERVAL_SECONDS=10`, and the normal
   local provider configuration. Never put a provider key, login secret, or
   production path in this record or an override.
3. Capture the complete manifest as `before.json`. Start only the named
   project with `backend/docker-compose.pc-integration-test.yml`, wait for its
   app and database to become healthy, then run
   `python /app/backend/tools/seed_phase22_uat_database.py` twice inside its
   app service. Both runs must report the same non-secret root, platform, and
   mapping ids. Confirm the root is `/romm/library/roms`, has mode
   `external_read_only`, and has an active `win` mapping at relative path
   `win`.
4. In the browser through the established SSH tunnel on port 3344, log in to
   this disposable stack and run **Library scan, Quick scan**. Record the
   pending-review count after the scan and preserve an authenticated API or
   disposable database query that identifies the Cyberpunk 2077: Phantom
   Liberty component queue row.
5. Use the existing MatchRomDialog to select the canonical Cyberpunk 2077:
   Phantom Liberty Steam candidate, app id `2138330`. After a successful
   save, reload the queue. The exact component row must be terminal `claimed`
   and absent from the pending response. The pending count must decrease by
   one and unrelated rows must remain pending.
6. Perform the stale proof in the same disposable project by first retaining
   or creating a newer component target incarnation and pending queue version.
   A later resolution using the consumed old target version must be a no-op;
   the newer pending row must remain visible.
7. Capture the manifest after scan and after every browser action. Compare
   each capture byte-for-byte with `before.json`. Record only the comparison
   outcome, project name, non-secret identifiers, and queue outcomes.
8. After the final comparison, run `docker compose down --volumes
--remove-orphans` with this exact project name and remove only this exact
   `mktemp -d` root. Do not use global Docker prune commands.

The manual-correction proof passes only when the exact consumed row becomes
`claimed`, stale replacement evidence stays `pending`, and all fixture
manifests remain identical.

## Automated Interval-Scan Evidence, 2026-10-02

The scheduler proof used the disposable Compose project
`romm-phase22-qut-1790974495` and a new temporary fixture root. It ran the
repository Compose definition with `app`, `database`, `queue`, `scheduler`,
`worker`, and `nginx`, with the development-only ten-second interval enabled.
All fixture files were synthetic text files and the source bind was read-only.

- The first two scheduled executions ran before seeding and logged an empty
  active-mapping set without failing. This proves an unmapped platform cannot
  abort the recurring job.
- The seeded active `win` mapping was then detected by the next interval
  execution. The low-priority worker completed a full mapped scan without a
  browser-started scan.
- `Sekiro Shadows Die Twice/Sekiro Shadows Die Twice.iso` was added only after
  the baseline setup. A later ten-second interval discovered it automatically
  as `Sekiro: Shadows Die Twice`; the disposable catalog contains one ROM and
  one pending review item with normalized query `Sekiro Shadows Die Twice`.
- The fixture manifest captured immediately after adding Sekiro matched the
  manifest captured after two further interval windows byte-for-byte. A worker
  mount check also confirmed the source file was not writable.
- Cleanup ran only for project `romm-phase22-qut-1790974495` with
  `down --volumes --remove-orphans`. Its temporary fixture root was moved to
  the local trash after the manifest comparison.

This is automated scheduler evidence only. The browser review, correction,
skip, and stale-conflict checks remain required before Phase 22 can be marked
UAT-approved.

## UAT Approval, 2026-10-02

The operator completed and approved the isolated Phase 22 UAT on the disposable
port-3344 stack. A DLC was manually matched and its review row was claimed;
a normal review row was skipped without a Conflict response; and, after a
baseline scan, a newly added synthetic `NieR Automata.iso` was discovered by
the ten-second scheduler without another manual scan. No real game content or
real library mount was used.
