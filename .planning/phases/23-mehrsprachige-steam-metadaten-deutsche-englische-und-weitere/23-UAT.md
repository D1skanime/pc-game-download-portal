---
phase: 23
plan: 03
status: prepared-fresh-expanded-fixture-awaiting-manual-scan
scope: disposable-synthetic-multilingual-detail-stack
---

# Phase 23 Multilingual Steam Detail UAT

## Safety Boundary

Use one new `mktemp -d` root and one new Compose project named
`romm-phase23-<random>`. The project must start with an empty, project-owned
database volume. Never import, copy, reuse, or seed Phase 22 database state.
The scan must create this project's catalog records from the fixture below.

Do not use a NAS path, Team4s service, production library, real game file,
production credential, existing Compose project, existing volume, or existing
network. Do not edit a repository Compose file or run Docker-wide cleanup.
Cleanup is limited to the exact Phase 23 project and temporary root.

## Fixture and Immutable Manifest

Copy the established Phase 22 scanner-compatible parent/DLC shape into the new
temporary root. The files are deliberately small synthetic text despite their
extensions:

```text
library/roms/win/Cyberpunk 2077/Cyberpunk 2077.iso
library/roms/win/Cyberpunk 2077/dlc/Phantom Liberty/Phantom Liberty.zip
library/roms/gb/Tetris/Tetris.gb
library/roms/nds/Mario Kart DS/Mario Kart DS.nds
library/roms/switch/The Legend of Zelda - Tears of the Kingdom/The Legend of Zelda - Tears of the Kingdom.nsp
```

Write only `phase23-parent-fixture` and `phase23-dlc-fixture` as file content.
Capture `before.json` before starting the stack and `after.json` after the
scan and every browser observation. Every entry contains its relative path,
entry type, byte size, modification timestamp, and file SHA-256. The JSON
files must compare byte-for-byte.

For the rebuilt disposable run, retain that scanner-compatible pair and add
ten tiny, deterministic Windows parents with real game names. Every added
Windows parent has one explicitly named DLC, update, or expansion subdirectory.
The three console fixtures are separate single-ROM platform directories. File
contents remain synthetic text and are never game data.

| Platform                   | Parents                                                                                                                                                                                                 | Extensions                   | Components                                                                                                                                                      |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Windows (`win`)            | `Cyberpunk 2077`, `Baldur's Gate 3`, `The Witcher 3 Wild Hunt`, `Elden Ring`, `Hades`, `Stardew Valley`, `Red Dead Redemption 2`, `DOOM Eternal`, `Hollow Knight`, `Forza Horizon 5`, `Resident Evil 4` | 4 `.zip`, 4 `.iso`, 3 `.rar` | 4 `dlc`, 3 `update`, 3 `expansion`, including `Phantom Liberty`, `Shadow of the Erdtree`, `Hearts of Stone`, and `Separate Ways` (4 `.zip`, 4 `.iso`, 3 `.rar`) |
| Game Boy (`gb`)            | `Tetris`                                                                                                                                                                                                | `.gb`                        | none                                                                                                                                                            |
| Nintendo DS (`nds`)        | `Mario Kart DS`                                                                                                                                                                                         | `.nds`                       | none                                                                                                                                                            |
| Nintendo Switch (`switch`) | `The Legend of Zelda - Tears of the Kingdom`                                                                                                                                                            | `.nsp`                       | none                                                                                                                                                            |

```bash
python3 - "$UAT_ROOT/library" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
entries = []
for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
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

## New Empty Disposable Stack

1. Set `UAT_ROOT` to the exact new temporary directory,
   `COMPOSE_PROJECT_NAME` to the new `romm-phase23-<random>` name,
   `PHASE10_FIXTURE_SOURCE="$UAT_ROOT/library"`, and
   `PHASE10_REPO_ROOT=/home/d1sk/romm`.
2. Create an untracked override under `UAT_ROOT`. It may contain only these
   configuration values, never a secret, credential, host path, or provider
   key:

```yaml
services:
  app:
    environment:
      DEV_MODE: "true"
      ENABLE_SCHEDULED_RESCAN: "false"
      SCHEDULED_RESCAN_CRON: "*/15 * * * *"
      PC_AUTOMATION_UAT_INTERVAL_SECONDS: "0"
      STEAM_API_ENABLED: "true"
      STEAM_API_TEXT_LANGUAGES: "german,english"
  worker:
    environment:
      DEV_MODE: "true"
      ENABLE_SCHEDULED_RESCAN: "false"
      SCHEDULED_RESCAN_CRON: "*/15 * * * *"
      PC_AUTOMATION_UAT_INTERVAL_SECONDS: "0"
      STEAM_API_ENABLED: "true"
      STEAM_API_TEXT_LANGUAGES: "german,english"
  scheduler:
    environment:
      DEV_MODE: "true"
      ENABLE_SCHEDULED_RESCAN: "false"
      SCHEDULED_RESCAN_CRON: "*/15 * * * *"
      PC_AUTOMATION_UAT_INTERVAL_SECONDS: "0"
      STEAM_API_ENABLED: "true"
      STEAM_API_TEXT_LANGUAGES: "german,english"
  nginx:
    ports:
      - "127.0.0.1:3344:80"
```

3. Start only this new project with
   `backend/docker-compose.pc-integration-test.yml` and its exact override.
   Confirm every new volume and network has this exact project prefix, the
   database volume is new and empty, and `/romm/library/roms` is read-only.
4. Register the one fixture root and create active mappings for `win`, `gb`,
   `nds`, and `switch` in the new app. Perform exactly one immediate manual
   quick scan. Scheduled
   automation remains disabled for this UAT; the 10-second automation path is
   prohibited. If scheduled rescans are enabled in a future reproduction,
   retain `SCHEDULED_RESCAN_CRON=*/15 * * * *` and
   `PC_AUTOMATION_UAT_INTERVAL_SECONDS=0`.

## Genuine Steam Enrichment and Database Evidence

Use the normal Phase 23 Steam enrichment/scan path only. Do not write or seed
`steam_metadata`, `text_variants`, summaries, App IDs, or component metadata
directly in the disposable database. Do not manufacture a fallback result.

After the scan, query only this new project's isolated database and record
non-secret, bounded evidence for the scanned parent and DLC component:

| Target                    | Required readback                                                                                            |
| ------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Parent `Cyberpunk 2077`   | Steam app ID; `text_variants.de` source language and summary; `text_variants.en` source language and summary |
| DLC `dlc/Phantom Liberty` | Steam app ID; `text_variants.de` source language and summary; `text_variants.en` source language and summary |

The proof may record only app IDs, language tags, source-language provenance,
and the two visible summaries. Do not record database credentials, full API
responses, session data, or host paths. If either German or English variant is
absent because Steam's live response is unavailable or non-deterministic, stop
the UAT and report that concrete blocker. Do not proceed to browser checks.

## Browser Checks, Only After Database Proof

Open only the new disposable nginx URL through the established SSH tunnel.

1. On the parent detail, German must show the persisted German Steam summary.
   Switch to English and verify the persisted English summary appears without a
   rescan or provider request.
2. Select a shipped UI locale with no stored variant, such as French. The
   parent must show English. Switch back to German and verify an immediate
   return to German.
3. Open the parent DLC detail and repeat German, English, French fallback, and
   immediate switch-back checks.
4. Capture `after.json` and compare it byte-for-byte with `before.json`.
   Stop only the exact Phase 23 project after the checkpoint is approved.

## Evidence Record

| Check                                                   | Result              | Observed value |
| ------------------------------------------------------- | ------------------- | -------------- |
| New project/database/volume identity                    | Pending fresh UAT   |                |
| Read-only synthetic fixture mount                       | Pending fresh UAT   |                |
| `PC_AUTOMATION_UAT_INTERVAL_SECONDS=0`                  | Pending fresh UAT   |                |
| Scheduled rescans disabled, cron retained at 15 minutes | Pending fresh UAT   |                |
| Parent German and English variant readback              | Pending fresh UAT   |                |
| DLC German and English variant readback                 | Pending fresh UAT   |                |
| Parent German, English, and fallback                    | Pending browser UAT |                |
| DLC German, English, and fallback                       | Pending browser UAT |                |
| Before/after fixture manifest                           | Pending browser UAT |                |
| Exact-project cleanup                                   | Pending browser UAT |                |

## Fresh Expanded Fixture Environment, 2026-10-05

The preceding `romm-phase23-1791196505` project was stopped and removed with
only its own labelled containers, volumes, and network; its exact temporary
root was recoverably removed. The rebuilt project is a separate disposable
project with a new empty database volume and a new network. Its catalog counts
are `roms=0` and `rom_components=0`; no scan or catalog write has occurred.

The full immutable pre-service manifest is persisted at
`$UAT_ROOT/artifacts/before.json`. It contains 57 entries (22 files) and has
SHA-256 `ed162480ec944e5bcba127f0a5621002eb06d7783371d387fbe57fbd83cffb65`.
It is the sole baseline for the later byte-for-byte comparison. The fixture
mount is read-only, scheduled rescans are disabled, and the 10-second path is
disabled. Do not claim scan, Steam metadata, browser, after-manifest, or UAT
approval evidence until the next explicitly authorized action.

## Automated Preparation Evidence

- PASS: isolated OpenAPI generation produced typed Steam parent and DLC links.
- PASS: `npm run test -- steamTextVariants`, 6 tests passed.
- PASS: `npm run typecheck` and scoped `trunk check --no-fix`.
- BLOCKED: host backend endpoint tests require the unavailable MariaDB endpoint
  at `127.0.0.1:3306` before assertions run.

No isolated scan, Steam database evidence, browser result, manifest comparison,
or UAT approval has been claimed by this preparation record.
