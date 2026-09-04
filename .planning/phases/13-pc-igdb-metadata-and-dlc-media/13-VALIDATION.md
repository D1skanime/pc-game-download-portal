---
phase: 13
slug: pc-igdb-metadata-and-dlc-media
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-04
---

# Phase 13 - Validation Strategy

## Test Infrastructure

| Property           | Value                                                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend            | pytest, existing IGDB cassettes and scan fixtures                                                                                                                   |
| Frontend           | Vitest and Vue Test Utils                                                                                                                                           |
| Quick backend run  | `cd backend && uv run pytest tests/handler/metadata/test_igdb_handler.py tests/handler/database/test_pc_igdb_enrichment.py tests/endpoints/sockets/test_scan.py -q` |
| Quick frontend run | `cd frontend && npm run test -- src/v2/components/GameDetails/OverviewTab.test.ts src/v2/components/GameDetails/PcDlcDetail.test.ts`                                |
| Contract/static    | `npm run generate && npm run typecheck`, locale parity/sort, `trunk fmt --no-fix && trunk check --no-fix`                                                           |

## Sampling Rate

- After every task commit, run that task's focused backend or frontend command.
- After every wave, run both quick suites and the relevant static check.
- Before verification, run generation, typecheck, locale checks, scoped Trunk and the migration dialect harness.
- Maximum focused feedback latency is 60 seconds, excluding code generation and dialect harnesses.

## Per-Task Verification Map

| Task  | Secure behavior                                                                        | Test type          | Required proof                                             | Status     |
| ----- | -------------------------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------- | ---------- |
| 13-01 | Developer/publisher/theme and Windows-only date normalization preserves legacy fields. | pytest             | Role, missing-data and non-Windows fixtures pass.          | ⬜ pending |
| 13-01 | Parent and component structured fields migrate safely.                                 | pytest + migration | MariaDB, MySQL and PostgreSQL upgrade/downgrade passes.    | ⬜ pending |
| 13-02 | Scan imports only unambiguous DLC data into owned storage.                             | pytest             | Ambiguous/unresolved no-op and parent/sibling decoys pass. | ⬜ pending |
| 13-02 | Optional remote media failure leaves metadata and scan visibility intact.              | pytest             | Failure fixture records no source write or scan abort.     | ⬜ pending |
| 13-03 | Parent/DLC detail views show only their own PC metadata and screenshots.               | Vitest             | Full/partial/empty and cross-owner fixtures pass.          | ⬜ pending |
| 13-03 | Locale and OpenAPI contracts agree.                                                    | static             | Generate, typecheck, parity and sort commands exit zero.   | ⬜ pending |
| 13-04 | New enrichment controls preserve immutable source boundary.                            | pytest + Vitest    | Source-mutation inventory and focused suites pass.         | ⬜ pending |

## Wave 0 Requirements

- [ ] Add `backend/tests/models/test_pc_igdb_metadata.py` for the migration and schema contract.
- [ ] Add `backend/tests/handler/database/test_pc_igdb_enrichment.py` for parent/component containment.
- [ ] Extend existing IGDB, scan, parent Overview and DLC detail fixtures with role/date/media cases.

## Manual-Only Verifications

| Behavior                                                                            | Why manual                                                                | Test instructions                                                                                     |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Parent and unique DLC metadata hierarchy is readable across themes and breakpoints. | Visual hierarchy and responsive gallery behavior need browser inspection. | Inspect both details at xs, md and xl in light/dark themes.                                           |
| Keyboard/gamepad navigation reaches facts and gallery without a focus trap.         | Input modality needs a running app.                                       | Traverse parent then DLC overview using keyboard and gamepad.                                         |
| Source library remains unchanged through a real scan.                               | Deployment evidence cannot be reproduced by fixtures alone.               | Compare configured source-tree manifest before and after scan; inspect only RomM-owned media changed. |

## Validation Sign-Off

- [ ] All tasks have focused automated verification or Wave 0 tests.
- [ ] Sampling continuity has no three consecutive tasks without automated checks.
- [ ] Wave 0 covers every new migration, scan and UI seam.
- [ ] No watch-mode flags are used.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** pending
