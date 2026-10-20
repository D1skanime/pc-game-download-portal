# Phase 34 Wave 2 Verification Remediation

Date: 2026-10-19. Source/test commit: `15ed063ac`.

## Scope and Environment

This is the authorized bounded Wave 2 gate repair, not a new numbered plan.
The adjacent setup fixture error and five TypeScript diagnostics prevented useful
verification before the next wave. No feature, matcher, resolver, API contract,
check configuration or assertion was removed or weakened.

Preflight passed through `ssh team4s-linux`: Linux, canonical root
`/home/d1sk/pc-game-download-portal`, branch `codex/phase-32-pgdp-naming`, origin
`https://github.com/D1skanime/pc-game-download-portal.git`. Planning state identifies
the RomM PC Library project and active Phase 34. No branch switch, worktree or
nested agent was used.

The backend-development, frontend-v2-components, frontend-v2-patterns and
pre-pr-verification guides informed the changes. Debugging, TDD and verification
guides informed reproduction and evidence classification. Shared STATE, ROADMAP,
REQUIREMENTS and Phase 33 acceptance remain owned by the parent executor.

## Changes

- Declare `tmp_path` in the existing setup-handler test. Preserve all bootstrap,
  folder-discovery, association and path-redaction assertions and the 12-case count.
- Declare complete `MatchSearchRom` fixtures with required platform and identity
  fields. Preserve all eight provider-cover result checks and Steam attribution.
- Narrow mapping rows with `NonNullable<typeof row>`. This retains the derived
  required string fields instead of widening them to an interface's optional fields.
- Add four mapping tests: sorted paths and display-name fallback, partial request
  failure, unsaved-platform filtering, and empty/all-failed requests. API response
  and platform fixtures are typed without `any`, suppression or double assertions.

The only changed runtime module is 35 physical lines. No new runtime implementation,
operator path, UI copy, provider implementation or storage model was introduced.

## Actual Reproduction and Verification

| Check | Actual result |
| --- | --- |
| Original adjacent setup command, before edits | Exit 1: 11 passed, 1 NameError at undeclared tmp_path, line 77 |
| Isolated full npm run typecheck, before edits | Exit 2: exactly TS2352, TS2322, TS2677 and two TS18047 diagnostics |
| Combined adjacent setup and recovery suites after edits | Exit 0: 39 passed, comprising the original 12 plus 9 handler and 18 endpoint recovery cases |
| Focused MatchRom and mapping tests | Exit 0: 15 passed, 11 provider tests plus four mapping tests |
| Host runner unittest discovery | Exit 0: 23 passed |
| Isolated full npm run typecheck after edits | Exit 0: zero diagnostics on retained generated contracts |
| Isolated npm run build | Exit 0, including token prebuild and PWA output |
| Full isolated frontend suite | Exit 1: 1009 passed, four failed, zero skipped/errors, 1013 total |
| Pre-fix authority-inventory comparison | Exit 1: 19 passed, same one inventory failure |
| Scoped trunk fmt and trunk check --no-fix | Exit 0: all four source/test files clean |
| Commit hook | Passed without bypass; four modified files clean |
| git diff --check and deletion inspection | Passed; source commit deletes no tracked file |

The original reproduction command was:

```sh
python3 backend/tools/phase34.py backend tests/handler/test_setup_folder_handler.py tests/endpoints/test_setup.py tests/integration/test_setup_folder_assignments.py -q
```

The combined GREEN command used `backend_command` for those same three files plus
`tests/handler/test_setup_recovery.py` and `tests/endpoints/test_setup_recovery.py`,
with `-q` and JUnit name `setup-39`. Frontend focus used `frontend_command` for
`src/v2/components/MatchRom/types.test.ts` and
`src/v2/components/Settings/pgdpFolderMappings.test.ts`, JUnit name `focused-15`.
Host checks used `python3 -m unittest discover -s backend/tools/tests -p
'test_phase34*.py' -q`.

The batch used the existing `Run.start/exec/close` API through Python stdin, with
`try/finally` cleanup. It ran `npm run typecheck`, `npm run build`, then the full
frontend test command in the disposable snapshot. No API regeneration was needed
or retained. This proves the retained-contract typecheck, not the exploratory
full-regeneration baseline with the separately deferred store errors.

The fixture NameError is a verification failure, not behavioral RED evidence.
The five TS diagnostics are static verification RED followed by zero diagnostics.
The first new-test run had 14 passes and one test-hook cleanup error: a reset
callback returned the mock function. The callback now returns void. This setup
mistake is not counted as a production defect or behavioral RED. Existing mapping
and provider behavior remains covered, with no invented RED or duplicate feature.

## Remaining Failures and Limits

The full frontend run retains these failures without weakening checks:

- `useScanLifecycle/index.test.ts`: reinstalls listeners after scope disposal
  (`P34_REMOUNT`), keeps listeners while another owner survives (`P34_OWNERS`),
  and cancels debounce work on final disposal (`P34_DEBOUNCE`). These remain owned
  by the planned lifecycle fix. The three existing RQ REDs were not rerun or fixed.
- `sourceMutationInventory.test.ts`: inventories every production v2 module and
  reachable API service. The existing `services/api/setup.ts` call
  `assignFolders:api.post`, `POST /setup/folders/assign`, is unclassified
  (`payload=none operation=UNKNOWN storage=unknown`). A separate disposable
  comparison reversed all three remediation diffs only inside its snapshot and
  reproduced the same failure. Neither authority rules nor the setup API changed.

The production build reports CSS `:deep` minifier warnings, dependency `eval`
warnings from vue3-pdf-app and large-chunk warnings. Successful backend tests retain
the existing Alembic path_separator and SQLAlchemy relationship warnings.
These warnings and the inventory issue are deferred, not silently repaired.

No full-phase, browser, worker, deployment or global-green acceptance is claimed.
Plans 34-03, 34-11 and 34-12 remain open. No plan SUMMARY or requirement completion
was created. This repair does not change visible UI behavior.

## Retained Linux Evidence and Cleanup

Each path below is under `/tmp/` and contains bounded redacted `evidence/` logs,
command receipts, JUnit where applicable, source manifests and `cleanup.json`.
Private target manifests remain in `control/`. Every cleanup receipt reports
`clean=true`, `source_unchanged=true`, empty remaining containers/volumes/networks,
and an absent owned checkout snapshot.

| Purpose | Evidence root |
| --- | --- |
| Fixture reproduction | pgdp34-47ed22efbde4450eb6bcfe0dd70f615c-ty_a7vyh |
| Five TS diagnostics | pgdp34-6f8621ce21e9474e8dc0f4090d6893f8-zzkv0a7c |
| Initial focused tests with hook error | pgdp34-632edc0dccb74183b82434be8537bcfa-agler5vq |
| Final 39/15/typecheck/build/full-suite batch | pgdp34-2c007e0075c8421a9328edd4888a2912-7kms8u7f |
| Pre-fix inventory comparison | pgdp34-a493fada331f4489996bfecbc93263ce-_7a7fb06 |

Teardown used exact ownership-validated resources. The disposable build directory's
container-created ownership was restored after verifying its runner label and exact
snapshot mount, enabling ordinary runner cleanup. Synthetic Games stayed read-only
and unchanged. No real Games access, live DB reset, scan, restart or deployment
occurred. All initially dirty files and both pgdp_test directories remain intact
and outside the source/test commit. No broad staging or cleanup command was used.
