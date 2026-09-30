---
phase: 19
slug: fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-28
---

# Phase 19 - Validation Strategy

> Per-phase validation contract for PC scan matching and safe component enrichment.

## Test Infrastructure

| Property               | Value                                                                                                                                                                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Framework**          | pytest 9.0.3 with pytest-asyncio and pytest-mock                                                                                                                                                                                |
| **Config file**        | `backend/pyproject.toml`                                                                                                                                                                                                        |
| **Quick run command**  | `cd backend && uv run pytest tests/handler/test_scan_handler.py tests/endpoints/sockets/test_scan.py tests/handler/metadata/test_pc_match_handler.py -x`                                                                        |
| **Full suite command** | `cd backend && uv run pytest tests/handler/test_scan_handler.py tests/handler/test_fastapi.py tests/endpoints/sockets/test_scan.py tests/handler/metadata/test_pc_match_handler.py tests/endpoints/roms/test_pc_metadata.py -x` |
| **Estimated runtime**  | Under 60 seconds in the Compose-backed test environment                                                                                                                                                                         |

## Sampling Rate

- **After every task commit:** Run the quick command.
- **After every plan wave:** Run the full phase suite.
- **Before verification:** Run the full phase suite and `trunk fmt && trunk check`.
- **Max feedback latency:** 60 seconds.

## Per-Task Verification Map

| Task ID  | Plan | Wave | Requirement | Threat Ref | Secure Behavior                                                                                                                                       | Test Type        | Automated Command                                                                                                                      | File Exists | Status     |
| -------- | ---- | ---- | ----------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ---------- |
| 19-01-01 | 01   | 1    | D-01        | T-19-01    | A compact Windows PC name is presented to IGDB as a searchable title while a classic ROM keeps its raw filename.                                      | unit             | `cd backend && uv run pytest tests/handler/test_scan_handler.py -k 'compact or classic' -x`                                            | ❌ W0       | ⬜ pending |
| 19-01-02 | 01   | 1    | D-03        | T-19-02    | A Steam-only Windows ROM enters an IGDB-selected update, uses IGDB name lookup, preserves its row identity, and does not run when IGDB is unselected. | unit/integration | `cd backend && uv run pytest tests/endpoints/sockets/test_scan.py tests/handler/test_fastapi.py -k steam_only -x`                      | ❌ W0       | ⬜ pending |
| 19-01-03 | 01   | 1    | D-04, D-06  | T-19-03    | A matched parent enriches only one exact related DLC or expansion; ambiguity and unrelated entries cause no automatic component write.                | integration      | `cd backend && uv run pytest tests/endpoints/sockets/test_scan.py tests/handler/metadata/test_pc_match_handler.py -k enrichment -x`    | ⚠ extend    | ⬜ pending |
| 19-01-04 | 01   | 1    | D-05        | T-19-04    | An exact-title component search remains review-only until an explicit selected candidate is posted.                                                   | endpoint         | `cd backend && uv run pytest tests/handler/metadata/test_pc_match_handler.py tests/endpoints/roms/test_pc_metadata.py -k component -x` | ✅          | ⬜ pending |

## Wave 0 Requirements

- [ ] `backend/tests/handler/test_scan_handler.py` - compact Windows and unchanged classic scan inputs.
- [ ] `backend/tests/endpoints/sockets/test_scan.py` - Steam-only Windows update eligibility and related DLC/expansion safety.
- [ ] `backend/tests/handler/test_fastapi.py` - no-duplicate Steam-only refresh persistence.

## Manual-Only Verifications

| Behavior                                                                     | Requirement | Why Manual                                               | Test Instructions                                                                                                                                                                                  |
| ---------------------------------------------------------------------------- | ----------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UAT fixture shows parent plus a DLC and expansion after a normal quick scan. | D-01, D-04  | Requires live provider response and UAT mounted fixture. | Scan `EuroTruckSimulator2` with IGDB and Steam selected. Confirm the existing ROM is enriched and its `Special Transport` DLC and `Italia` expansion have metadata without a duplicate parent ROM. |

## Validation Sign-Off

- [x] All planned behaviors have an automated test seam.
- [x] Sampling continuity has a focused command after each task.
- [x] Wave 0 identifies missing regression coverage.
- [ ] Full phase suite is green.
- [ ] `trunk fmt && trunk check` is green.

**Approval:** pending
