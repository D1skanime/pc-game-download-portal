---
phase: 23
plan: 03
status: prepared-awaiting-browser-checkpoint
scope: disposable-synthetic-multilingual-detail-stack
---

# Phase 23 Multilingual Steam Detail UAT

## Safety Boundary

Use one new `mktemp -d` root and a new Compose project name beginning with
`romm-phase23-`. The only source fixture is two small, synthetic text files.
The Compose source bind must be read-only at `/romm/library/roms`.

Do not use a NAS path, Team4s service, production library, real game file,
existing Compose project, or production credential. Do not edit a repository
Compose file. Do not run a Docker-wide cleanup command. Cleanup is limited to
the exact project name and exact temporary root created for this UAT.

## Fixture and Manifest

Create only this text-file fixture under the new temporary root:

```text
library/roms/win/Phase 23 Parent/Phase 23 Parent.iso
library/roms/win/Phase 23 Parent/dlc/Phase 23 DLC/Phase 23 DLC.zip
```

Write the literal synthetic payloads `phase23-parent-fixture` and
`phase23-dlc-fixture`. Capture `before.json` before starting the stack and
`after.json` after every browser observation. Each manifest entry must contain
the relative path, entry type, byte size, and SHA-256 for files. Compare the
two JSON files byte-for-byte. They must match.

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
    }
    if path.is_file():
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entries.append(entry)
print(json.dumps(entries, sort_keys=True, separators=(",", ":")))
PY
```

## Disposable Stack and Synthetic Metadata Seed

1. Set `UAT_ROOT` to the exact new temporary directory and
   `COMPOSE_PROJECT_NAME` to `romm-phase23-<random>`. Set
   `PHASE10_FIXTURE_SOURCE="$UAT_ROOT/library"`.
2. Create an untracked override inside `UAT_ROOT` that only enables
   `DEV_MODE: "true"`. Do not put credentials, host paths, or provider keys in
   it. Start only the database, queue, app, worker, scheduler, and nginx
   services from `backend/docker-compose.pc-integration-test.yml` with that
   project name.
3. Verify the running app container sees `/romm/library/roms` and cannot write
   there. Verify the source tree contains only the two files above. Register
   the isolated Windows mapping and scan it once so one parent and one DLC
   component exist.
4. In the disposable app container, seed only the scanned parent and its DLC
   component with these persisted values. The parent has `fields: ["summary"]`
   and no manual summary marker. The DLC has `metadata_source: "steam"`.

```json
{
  "parent": {
    "summary": "Phase 23 German parent summary",
    "steam_metadata": {
      "app_id": 230001,
      "source": "storefront",
      "fields": ["summary"],
      "text_variants": {
        "de": {
          "source_language": "german",
          "summary": "Phase 23 German parent summary"
        },
        "en": {
          "source_language": "english",
          "summary": "Phase 23 English parent summary"
        }
      }
    }
  },
  "dlc": {
    "summary": "Phase 23 German DLC summary",
    "metadata_source": "steam",
    "steam_metadata": {
      "app_id": 230002,
      "source": "storefront",
      "text_variants": {
        "de": {
          "source_language": "german",
          "summary": "Phase 23 German DLC summary"
        },
        "en": {
          "source_language": "english",
          "summary": "Phase 23 English DLC summary"
        }
      }
    }
  }
}
```

The seed is local database state for this one disposable project. It makes no
Steam request and does not modify either text fixture. Do not seed production
or an existing UAT database.

Run this seed only through the exact disposable project after confirming the
scanned names and DLC path. It updates no source files and does not call a
provider:

```bash
docker compose -p "$COMPOSE_PROJECT_NAME" -f backend/docker-compose.pc-integration-test.yml exec -T app python - <<'PY'
from sqlalchemy import select

from handler.database.base_handler import sync_session
from models.rom import Rom, RomComponent, RomComponentMetadata

with sync_session.begin() as session:
    parent = session.scalars(
        select(Rom).where(Rom.fs_name_no_ext == "Phase 23 Parent")
    ).one()
    dlc = session.scalars(
        select(RomComponent).where(
            RomComponent.rom_id == parent.id,
            RomComponent.relative_path == "dlc/Phase 23 DLC",
        )
    ).one()
    parent.summary = "Phase 23 German parent summary"
    parent.steam_id = 230001
    parent.steam_metadata = {
        "app_id": 230001,
        "source": "storefront",
        "fields": ["summary"],
        "text_variants": {
            "de": {"source_language": "german", "summary": "Phase 23 German parent summary"},
            "en": {"source_language": "english", "summary": "Phase 23 English parent summary"},
        },
    }
    metadata = dlc.component_metadata
    if metadata is None:
        metadata = RomComponentMetadata(component_id=dlc.id)
        dlc.component_metadata = metadata
    metadata.summary = "Phase 23 German DLC summary"
    metadata.metadata_source = "steam"
    metadata.steam_id = 230002
    metadata.steam_metadata = {
        "app_id": 230002,
        "source": "storefront",
        "text_variants": {
            "de": {"source_language": "german", "summary": "Phase 23 German DLC summary"},
            "en": {"source_language": "english", "summary": "Phase 23 English DLC summary"},
        },
    }
PY
```

## Browser Checks

Open only the disposable nginx URL through the established SSH tunnel.

1. Open the seeded parent detail. In German, record `Phase 23 German parent
summary`. Switch to English and record `Phase 23 English parent summary`
   without a scan or provider request.
2. Select a shipped UI locale that has no stored variant, such as French. The
   parent must show `Phase 23 English parent summary`. Switch back to German
   and verify the German text returns immediately.
3. Open the parent DLC detail and repeat German, English, and French fallback.
   Record the corresponding distinct DLC strings.
4. Capture `after.json`, compare it byte-for-byte with `before.json`, then
   stop only the exact `romm-phase23-<random>` project with its volumes and
   remove only that exact temporary root.

## Evidence Record

| Check                             | Result              | Observed value |
| --------------------------------- | ------------------- | -------------- |
| Read-only synthetic fixture mount | Pending browser UAT |                |
| Parent German                     | Pending browser UAT |                |
| Parent English                    | Pending browser UAT |                |
| Parent missing-language fallback  | Pending browser UAT |                |
| DLC German                        | Pending browser UAT |                |
| DLC English                       | Pending browser UAT |                |
| DLC missing-language fallback     | Pending browser UAT |                |
| Before/after fixture manifest     | Pending browser UAT |                |
| Exact-project cleanup             | Pending browser UAT |                |

## Automated Preparation Evidence

- PASS: Isolated OpenAPI generation produced `SteamMetadataSchema` and
  `SteamTextVariantSchema`, with typed detailed parent and DLC metadata links.
- PASS: `npm run test -- steamTextVariants`, 6 tests passed.
- PASS: `npm run typecheck`.
- PASS: scoped `trunk fmt` and `trunk check --no-fix` for the modified source
  files.
- BLOCKED: `cd backend && uv run pytest tests/endpoints/roms/test_rom.py -q`
  cannot establish the pre-existing host test connection to
  `127.0.0.1:3306`, before test assertions run.

No browser stack, fixture manifest comparison, or UAT outcome has been claimed
by this preparation record.
