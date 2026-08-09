---
phase: 02
slug: read-only-policy-boundary
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-09
---

# Phase 02 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property               | Value                                                                                                                                                                                                                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Framework**          | pytest 9.0.3, pytest-asyncio 1.3.0                                                                                                                                                                                                                                    |
| **Config file**        | `backend/pytest.ini`                                                                                                                                                                                                                                                  |
| **Quick run command**  | `cd backend && uv run pytest tests/handler/filesystem/test_storage_policy.py tests/handler/filesystem/test_storage_access.py -x`                                                                                                                                      |
| **Full suite command** | `cd backend && uv run pytest tests/handler/filesystem/test_storage_policy.py tests/handler/filesystem/test_storage_access.py tests/endpoints/test_storage_policy_denials.py tests/tasks/test_storage_policy.py tests/handler/filesystem/test_storage_inventory.py -x` |
| **Container command**  | `python3 backend/tools/verify_read_only_policy.py`                                                                                                                                                                                                                    |
| **Estimated runtime**  | To be measured during Wave 0                                                                                                                                                                                                                                          |

## Sampling Rate

- **After every task commit:** Run the narrowest affected test file with `-x`.
- **After every plan wave:** Run the full Phase 2 suite.
- **Before `$gsd-verify-work`:** Run the full suite, the writable/`:ro` container verifier, scoped Trunk checks, and review the mutation inventory.
- **Max feedback latency:** 120 seconds for task-level tests; container evidence runs at wave and phase gates.

## Per-Task Verification Map

| Task ID  | Plan | Wave | Requirement      | Threat Ref            | Secure Behavior                                                                                                              | Test Type                   | Automated Command                                                                                                  | File Exists | Status  |
| -------- | ---- | ---- | ---------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------ | ----------- | ------- |
| 02-W0-01 | TBD  | 0    | ROOT-05, SAFE-01 | T-02-MODE-BYPASS      | Owned storage is explicit and the external operation allowlist is exact and closed.                                          | parameterized unit          | `cd backend && uv run pytest tests/handler/filesystem/test_storage_policy.py -x`                                   | No, W0      | pending |
| 02-W0-02 | TBD  | 0    | SAFE-02, TEST-03 | T-02-PRE-I/O          | Every prohibited or unknown operation denies before stat, open, enumeration, temporary-file, or mutation calls.              | adversarial unit            | `cd backend && uv run pytest tests/handler/filesystem/test_storage_policy.py -k 'deny or unknown or tripwire' -x`  | No, W0      | pending |
| 02-W0-03 | TBD  | 0    | SAFE-01, SAFE-06 | T-02-TOCTOU           | Operation-bound capabilities use descriptor-relative/no-follow access and leave source manifests unchanged.                  | filesystem integration/race | `cd backend && uv run pytest tests/handler/filesystem/test_storage_access.py -x`                                   | No, W0      | pending |
| 02-W0-04 | TBD  | 0    | SAFE-03          | T-02-DISCLOSURE       | Direct API denial returns bounded HTTP 403 while jobs and internal callers fail visibly without fallback.                    | API/task                    | `cd backend && uv run pytest tests/endpoints/test_storage_policy_denials.py tests/tasks/test_storage_policy.py -x` | No, W0      | pending |
| 02-W0-05 | TBD  | 0    | SAFE-04          | T-02-BYPASS           | Every existing mutation seam is policy-governed or structurally restricted to RomM-owned storage.                            | contract/inventory          | `cd backend && uv run pytest tests/handler/filesystem/test_storage_inventory.py -x`                                | No, W0      | pending |
| 02-W0-06 | TBD  | 0    | SAFE-05, TEST-03 | T-02-MOUNT-DEPENDENCY | The same denial matrix passes on writable and container-mounted `:ro` fixtures with typed policy errors rather than `EROFS`. | container integration       | `python3 backend/tools/verify_read_only_policy.py`                                                                 | No, W0      | pending |

_Final plan task IDs replace the provisional Wave 0 IDs during planning._

## Wave 0 Requirements

- [ ] `backend/tests/handler/filesystem/test_storage_policy.py` - exact allow/deny/unknown matrix and pre-access tripwires.
- [ ] `backend/tests/handler/filesystem/test_storage_access.py` - capability surface, post-close behavior, unchanged manifests, and coordinated path-swap races.
- [ ] `backend/tests/endpoints/test_storage_policy_denials.py` - bounded HTTP 403 contract without path disclosure.
- [ ] `backend/tests/tasks/test_storage_policy.py` - visible job/internal denial with no fallback or partial-success event.
- [ ] `backend/tests/handler/filesystem/test_storage_inventory.py` - closed inventory of filesystem mutation seams.
- [ ] `backend/tools/verify_read_only_policy.py` - identical writable and `:ro` fixture matrix with deterministic cleanup.
- [ ] Docker fixture or compose profile that mounts the external test library `:ro` while RomM-owned output remains writable and separate.
- [ ] Recursive before/after manifest helper excluding atime and covering names, kinds, sizes, modes, timestamps, links, and content hashes where applicable.
- [ ] Tripwires for `stat`, `scandir`, read/write `open`, `Path` access, temporary files, `mkdir`, unlink, rename, replace, copy, move, extraction, patching, sidecars, and cover writes.

## Manual-Only Verifications

All Phase 2 behaviors are automatable. Real NAS activation, protocol-specific atime behavior, and production operations remain Phase 9 scope.

## Validation Sign-Off

- [ ] All tasks have automated verification or explicit Wave 0 dependencies.
- [ ] Sampling continuity has no three consecutive tasks without automated verification.
- [ ] Wave 0 covers every missing test and fixture reference.
- [ ] No watch-mode flags are used.
- [ ] Task-level feedback latency remains below 120 seconds.
- [ ] Writable and `:ro` fixtures produce the same typed denial outcomes.
- [ ] Final plan task IDs replace provisional validation rows.
- [ ] `nyquist_compliant: true` is set after the plan-task map is final and complete.

**Approval:** pending plan alignment
