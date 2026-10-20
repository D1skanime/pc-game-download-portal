---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 06
status: passed-with-limitations
---

# Phase 33 mandatory final UAT

The executable harness creates a fresh MariaDB database, mounts only
UAT_ROOT/fixture/Games:/app/romm/library:ro, discovers direct pc and My Games
folders, records request/response and screenshot evidence, compares fixture
manifests, and removes only its generated Compose project and volumes.

Run bash 33-uat.sh from the canonical Linux checkout. Inspect state.json and
the evidence directory before approving the browser checkpoint.


## 2026-10-19 resumed acceptance evidence

The user accepted the complete live library scan. The later manually selected
Belmont child scan exposed a separate path/collection case. Broader Phase 33
acceptance stays open while plan 33-10 implements the explicit collection
decision and safe retirement of the mistaken parent.

Canonical disposable runs never touched pgdp-dev, its database, Redis, Media,
or Games. All four attempted browser stacks were removed, and their source
immutability/cleanup receipts are retained under evidence. No failed or
skipped browser run is classified as PASS.

- Focused reachable-MariaDB baseline: 21 tests passed. Historical stale
  test fixtures were corrected to use an authenticated Starlette Request,
  the fixture library constant, and an explicit empty-directory fallback.
- The real fresh browser discovered direct pc and My Games, then failed because
  pc was unknown. That assertion remains unchanged. The shared existing PC to
  Windows identity now fixes discovery: RED one failed/one passed, GREEN
  18 focused setup/bootstrap tests passed.
- Latest stable frontend before the new collection contract: typecheck,
  129 files and 1,093 tests, and production build passed.
- No final theme/layout/input/promotion matrix is claimed from the early
  failed browser. Physical gamepad availability must be recorded separately.

Receipts and hashes: 33-ACCEPTANCE-RECEIPTS.json. The generated state.json
currently describes the retained failed browser attempt, not final approval.
The final harness requires actual request/response bodies, ready=true, Home
and Scan after reload, fixture Games/pc and Games/My Games, real worker
completion, and cleanup. It now includes explicit collection retirement and
normal/scheduled discovery of host-added synthetic direct children.

The primary synthetic bind remains
UAT_ROOT/fixture/Games:/app/romm/library:ro. The guarded disposable runner also
binds that identical source read-only at its isolated library path. No symlink
or writable source alias is permitted. Browser execution uses an isolated
snapshot-local Playwright config because the normal config excludes planning
specs and requires seeded users.

Run bash -n 33-uat.sh, then bash 33-uat.sh from the canonical phase directory.
The actual playwright test command and all target identities are retained in
state.json. The standalone Python adapter lives in backend/tools/phase33_uat.py
under the repository's tool-location rule.

## Final disposable technical acceptance

The final run is evidence/pgdp34-f4dd7651eda049868d9483e52118cfcb.
Its actual Playwright command, browser and frontend exit codes are zero.
Both evidence validators passed. Its current-production-proof.json matches
the final retained-state reconnect fix, and the unchanged frontend manifest
matches the retained 64fa62f2 frontend receipt.

All 22 named browser checks passed: discovery, inline_assignment, ready,
reload, get_only, scan_completed, mapped_reads, explicit_child_scope,
parent_retired, safe_owned_cleanup, known_child_preserved,
normal_discovers_children, scheduled_discovers_children, theme_dark,
theme_light, layout_320, layout_desktop, mouse, keyboard, touch,
touch_target, and progress_counts.

| Actual worker operation | Total games | Scanned games |
| --- | --- | --- |
| Fresh two-platform scan | 3 | 3 |
| Explicit Belmont child | 1 | 1 |
| Normal complete Windows scan | 4 | 4 |
| Registered scheduled scan | 6 | 6 |

The selected child detail response contains exactly game.part01.rar and
game.part02.rar at pc/Castlevania/Belmonts.Curse. Its sibling was absent from
the initial targeted result. The mistaken parent was retired and classified.
The parent's note and rating/backlog audit were retained separately from the
child. Two exclusively owned media files were removed; the shared-media
control and Games source hashes were preserved. A normal complete scan and
the actual registered scheduled consumer each discovered a host-added direct
child without recreating the parent. The immutable manifests match before and
after each application segment; only the two explicit host fixture additions
are permitted between segments.

The actual primary bind is
UAT_ROOT/fixture/Games:/app/romm/library:ro. The guarded alias binds the identical
source read-only. Retained Docker inspection proves both exact source paths,
Mode ro and RW false. The generated stack, network, volumes and snapshot/root
were removed. No live database, Redis, Media or Games was reset by this harness.

Theme classes and both theme screenshots were captured; 320px and 1440px had
no document overflow. Mouse selection, keyboard focus and touchscreen
continuation ran. Both visible Next and Previous controls measured 48px high.
The existing dark canvas styling remains visible in the light-theme screenshot;
human visual acceptance is still required. Physical gamepad input is BLOCKED:
navigator.getGamepads() returned zero connected devices in headless Chromium.
That optional hardware limitation is not reported as a passed input test.

Latest unchanged-frontend quality: typecheck, all 1,102 tests, build and
maintainability passed. Focused historical setup/backend gates passed 21 and
18 tests. The final retained-identity reconnect regression and existing
lifecycle controls passed 9 tests on each of MariaDB and PostgreSQL. Eight
adversarial harness tests passed, including target refusal, immutable fixture
segments and rejection of writable or external Docker library mounts.

Historical failures remain retained: stale authenticated fixtures, PC alias
discovery, an unsafe symlink fixture, 40px navigation targets, actual worker
session/lock/import bugs, and harness CSRF/gallery-read/compose-normalization
mistakes. Failed runs were never converted to browser PASS. The earlier
47a9b75c run passed all 22 browser checks but its initial validator rejected a
lexically equivalent Compose source; authoritative Docker inspection and the
corrected strict validator passed afterwards. The final f4dd run uses the
direct source path and passed the complete command without that repair.

The operator enabled Dev autoscan every 15 minutes after technical validation.
The sanitized activation receipt is
evidence/live-autoscan-15m/activation-receipt.json. Root verified the registered
cron job, enabled flag, idle worker, frontend/API HTTP 200, unchanged DB/Redis
identities and the existing 33 games/one user. This is separate from the
disposable fixture's scheduled-consumer proof.

Schema receipts and SHA-256 provenance are listed in
33-ACCEPTANCE-RECEIPTS.json. Fresh final MariaDB, MySQL and PostgreSQL schema
upgrade/downgrade/re-upgrade/parity runs passed with 39, 39 and 40 successful
commands. Each full source manifest is identical to the final browser manifest
3326a6533fc597e42198ddcff6b62a3276203540ba007dbe388fdfcfba9d0b9d.
Cleanup and source immutability passed on every dialect. These refreshes
supersede historical receipts that predated the final audit/cleanup columns.

Plan 33-06 task 1 is technically verified. Task 2 acceptance of the exercised
live scope was subsequently supplied by the user below. Earlier pending
checkpoint statements describe the historical state. No following phase starts.

## Human live UAT acceptance, 2026-10-20

The user confirmed in the shared chat: "gut uat so weit bestanden".
The currently exercised live flow is accepted. This follows the collection-folder,
scan and download checks; the absent Tales of Berseria base download was explained
by an empty source directory and was not a scanner defect.

Recorded at 2026-10-20T10:17:09.659237+02:00. This is acceptance of the tested scope, not evidence that
every platform, theme or hardware input was manually retested. Physical gamepad
verification remains blocked. Independent deep code review remains pending.
The discussed optimization of repeated Windows quick-scan processing is not
implemented or accepted by this confirmation. No following phase is started.
