---
phase: 05
slug: preview-and-read-path-cutover
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-11
---

# Phase 05 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------- |
| **Framework**          | pytest 9.0.3 with pytest-asyncio 1.3.0                                                  |
| **Config file**        | `pyproject.toml`                                                                        |
| **Quick run command**  | `cd backend; uv run pytest tests/handler/storage tests/handler/test_scan_command.py -x` |
| **Full suite command** | `cd backend; uv run pytest`                                                             |
| **Estimated runtime**  | Quick suite under 60 seconds; full-suite duration is environment-dependent              |

---

## Sampling Rate

- **After every task commit:** Run the narrowest affected test file with `-x`.
- **After every plan wave:** Run mapped scan, preview, watcher, and ROM endpoint suites.
- **Before `$gsd-verify-work`:** Run the full backend suite and `trunk check`.
- **Max feedback latency:** 60 seconds for per-task sampling.

---

## Per-Task Verification Map

| Task ID  | Plan         | Wave | Requirement  | Threat Ref | Secure Behavior                                                                                        | Test Type                | Automated Command                                                                                  | File Exists              | Status  |
| -------- | ------------ | ---- | ------------ | ---------- | ------------------------------------------------------------------------------------------------------ | ------------------------ | -------------------------------------------------------------------------------------------------- | ------------------------ | ------- |
| 05-W1-01 | 05-02 Task 1 | 1    | SCAN-01      | T-05-01    | Every scan resolves the expected active mapping revision                                               | integration              | `cd backend; uv run pytest tests/integration/test_mapped_scan.py -x`                               | No, Wave 1               | pending |
| 05-W1-02 | 05-02 Task 1 | 1    | SCAN-02      | T-05-01    | Scan reads source and writes only to database or RomM-owned storage                                    | adversarial integration  | `cd backend; uv run pytest tests/integration/test_scan_source_immutability.py -x`                  | No, Wave 1               | pending |
| 05-W1-03 | 05-02 Task 3 | 1    | SCAN-03      | T-05-05    | Watch bursts are contained, debounced, and coalesced per mapping                                       | unit and integration     | `cd backend; uv run pytest tests/test_watcher.py -x`                                               | Extend existing coverage | pending |
| 05-W1-04 | 05-02 Task 2 | 1    | SCAN-04      | T-05-09    | Preview reports health and observed values without catalog writes                                      | endpoint and integration | `cd backend; uv run pytest tests/endpoints/storage/test_mapping_preview.py -x`                     | No, Wave 1               | pending |
| 05-W1-05 | 05-02 Task 2 | 1    | SCAN-05      | T-05-09    | Entry and time budgets produce pending, partial, and complete states while preserving the prior result | unit and endpoint        | `cd backend; uv run pytest tests/handler/storage/test_preview.py -x`                               | No, Wave 1               | pending |
| 05-W1-06 | 05-02 Task 2 | 1    | SCAN-06      | T-05-03    | Changed, removed, or disabled revisions make queued work fail stale without redirection                | queue integration        | `cd backend; uv run pytest tests/tasks/test_mapping_revision_jobs.py -x`                           | No, Wave 1               | pending |
| 05-W1-07 | 05-02 Task 3 | 1    | D-14 to D-20 | T-05-03    | Errors are stable and redacted, and all required files pass preflight before output                    | endpoint and integration | `cd backend; uv run pytest tests/endpoints/roms/test_files.py tests/endpoints/roms/test_rom.py -x` | Extend existing coverage | pending |

---

## Wave 1 Test Foundation Requirements

- [ ] `backend/tests/integration/test_mapped_scan.py` - common mapped-scan fixtures and active revision cases.
- [ ] `backend/tests/integration/test_scan_source_immutability.py` - before-and-after source-tree manifest assertions.
- [ ] `backend/tests/endpoints/storage/test_mapping_preview.py` - endpoint states and no-catalog-write assertions.
- [ ] `backend/tests/handler/storage/test_preview.py` - dual-budget traversal and partial-result behavior.
- [ ] `backend/tests/tasks/test_mapping_revision_jobs.py` - RQ identity, stale mapping, and preserved failure metadata.
- [ ] Shared fixtures for mapping revision replacement, operation handles invalidated at safe boundaries, source-tree manifests, and response capture before download output.
- [ ] Extend watcher and ROM endpoint suites for debounce, preflight, Range/HEAD, source replacement, and Nginx parity.

---

## Manual-Only Verifications

| Behavior                          | Requirement  | Why Manual                                                         | Test Instructions                                                                                                                                             |
| --------------------------------- | ------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Real NAS watcher fidelity         | SCAN-03      | Protocol, mount options, and event delivery vary by deployment     | Deferred to the Phase 9 production-like NAS gate; confirm scheduled reconciliation remains authoritative.                                                     |
| Production Nginx handoff behavior | D-16 to D-20 | Unit clients do not reproduce the deployed internal-redirect stack | Run container integration coverage for preflight-before-headers, Range/HEAD, disconnect, and source replacement; final production-like proof remains Phase 9. |

---

## Required Adversarial Matrix

- Mapping replacement before job start, during scan, before hash open, before response creation, and before Nginx redirect.
- Removed, disabled, unreachable, missing, denied, symlinked, non-regular, and raw `OSError` sources with redacted errors.
- Huge flat directories, deep trees, time-budget and entry-budget exhaustion, unreadable entries, Unicode names, zero-byte files, and no catalog writes.
- Single ISO, 100-part title, failed final part, mutation between preflight and transfer, Range/HEAD, disconnect, and Nginx redirect parity.
- Watch bursts while idle and active, concurrent mappings, missed NAS-style events, and scheduled reconciliation.

---

## Validation Sign-Off

- [x] Task-specific ROM delivery and ZIP-cache suites pass in the disposable MariaDB and Valkey environment.
- [x] The fresh isolated full backend gate passes: 3,141 passed, 10 skipped, zero failures or errors.
- [x] Checkout-bound OpenAPI generation and frontend typecheck pass.
- [x] The exact Phase 5 runtime inventory contains no legacy fixed-layout read authority.
- [x] Non-mutating scoped Trunk format and check gates pass for every applicable 05-07 path.
- [x] Source-manifest evidence remains byte-exact and generated archives stay in RomM-owned cache storage.
- [x] `nyquist_compliant: true` is retained and `wave_0_complete: true` records the completed executable validation foundation.

**Approval:** complete, 2026-08-12
