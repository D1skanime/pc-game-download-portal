---
phase: 23
plan: 03
status: blocked-after-genuine-isolated-scan-awaiting-dlc-steam-evidence
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
```

Write only `phase23-parent-fixture` and `phase23-dlc-fixture` as file content.
Capture `before.json` before starting the stack and `after.json` after the
scan and every browser observation. Every entry contains its relative path,
entry type, byte size, modification timestamp, and file SHA-256. The JSON
files must compare byte-for-byte.

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
```

3. Start only this new project with
   `backend/docker-compose.pc-integration-test.yml` and its exact override.
   Confirm every new volume and network has this exact project prefix, the
   database volume is new and empty, and `/romm/library/roms` is read-only.
4. Register only the fixture Windows root and create its `win` mapping in the
   new app. Perform exactly one immediate manual quick scan. Scheduled
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

| Check                                                   | Result                | Observed value |
| ------------------------------------------------------- | --------------------- | -------------- |
| New project/database/volume identity                    | Pending isolated scan |                |
| Read-only synthetic fixture mount                       | Pending isolated scan |                |
| `PC_AUTOMATION_UAT_INTERVAL_SECONDS=0`                  | Pending isolated scan |                |
| Scheduled rescans disabled, cron retained at 15 minutes | Pending isolated scan |                |
| Parent German and English variant readback              | Pending isolated scan |                |
| DLC German and English variant readback                 | Pending isolated scan |                |
| Parent German, English, and fallback                    | Pending browser UAT   |                |
| DLC German, English, and fallback                       | Pending browser UAT   |                |
| Before/after fixture manifest                           | Pending browser UAT   |                |
| Exact-project cleanup                                   | Pending browser UAT   |                |

## Isolated Scan Evidence, 2026-10-05

The one permitted immediate quick scan was run in the new project
`romm-phase23-1791196505`. This was not a Phase 22 project or a reused Docker
resource: it created its own `phase10-database` volume together with seven
other project-labelled disposable volumes and its own default network. Before
the fixture root, mapping, and scan were registered, its catalog counts were
`roms=0` and `rom_components=0`.

The fixture was the two-file parent/DLC shape above, with the specified
synthetic contents only. The mount was verified non-writable from the app.
The running services reported:

```text
ENABLE_SCHEDULED_RESCAN=false
PC_AUTOMATION_UAT_INTERVAL_SECONDS=0
SCHEDULED_RESCAN_CRON=*/15 * * * *
STEAM_API_TEXT_LANGUAGES=(german, english)
```

No 10-second job or scheduled rescan was enabled. A locally-created,
disposable admin was required only to create the new project's storage mapping;
no account, credential, catalog record, metadata, or database state was
imported from Phase 22.

The normal `scan_platforms(..., metadata_sources=[STEAM],
scan_type=QUICK)` path then ran once against the external Steam storefront.
It created the parent catalog record and populated its Steam metadata without
any direct database write:

| Target                    | Observed isolated database readback                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent `Cyberpunk 2077`   | App ID `1091500`; `de` source `german`: `Cyberpunk 2077 ist ein Open-World-Action-Adventure-RPG, das in Night City spielt – einer gefährlichen Metropole, deren Bewohner von Macht, Glamour und Körpermodifikationen besessen sind.`; `en` source `english`: `Cyberpunk 2077 is an open-world, action-adventure RPG set in the dark future of Night City — a dangerous megalopolis obsessed with power, glamor, and ceaseless body modification.` |
| DLC `dlc/Phantom Liberty` | Component was discovered at relative path `dlc/Phantom Liberty`, but has no Steam app ID, Steam metadata, or `de`/`en` text variants.                                                                                                                                                                                                                                                                                                             |

The scanner output reported `scanned_roms=1`, `new_roms=1`, and
`identified_roms=0`, with `Cyberpunk 2077 not identified`; the parent metadata
readback above nevertheless proves the parent Steam storefront enrichment
persisted. The required DLC matching/enrichment did not occur, so its two
localized variants are absent. This is the concrete live-scan blocker. No
retry, direct seeding, manufactured metadata, or browser check was performed.

The post-scan synthetic fixture manifest contains seven entries and has SHA-256
`47bf03d9b21c243b0cc1040d7fe3967933e9926f2eba730637781e378d0fa034`.
The initial operator captured the two synthetic file hashes before the scan,
but did not persist the required full `before.json`; therefore a byte-for-byte
manifest comparison is intentionally **not claimed**. This procedural gap and
the absent DLC Steam variants both prevent approval.

The former `romm-phase22-live` project was separately stopped and verified
absent (`0` project-labelled containers, volumes, and networks). Only its two
known override files and exact temporary root were moved to the recoverable
trash; no Docker-wide cleanup or other Compose project was touched.

## Browser Check Status

Browser UAT is blocked and has not started because the DLC database proof is
missing. Once a fresh isolated reproduction produces both parent and DLC
variants, still verify: parent and DLC German summaries, English switch,
French-to-English fallback, immediate switch-back to German, then a
byte-for-byte before/after fixture-manifest comparison. Keep this exact
disposable project isolated and scheduled automation disabled while awaiting
that decision.

## Automated Preparation Evidence

- PASS: isolated OpenAPI generation produced typed Steam parent and DLC links.
- PASS: `npm run test -- steamTextVariants`, 6 tests passed.
- PASS: `npm run typecheck` and scoped `trunk check --no-fix`.
- BLOCKED: host backend endpoint tests require the unavailable MariaDB endpoint
  at `127.0.0.1:3306` before assertions run.

No isolated scan, Steam database evidence, browser result, manifest comparison,
or UAT approval has been claimed by this preparation record.
