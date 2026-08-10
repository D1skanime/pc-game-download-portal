---
phase: 02-read-only-policy-boundary
verified: 2026-08-10T13:26:46Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Every existing filesystem mutation and read seam is governed by the central policy or structurally unable to address an external root"
  gaps_remaining: []
  regressions: []
---

# Phase 2: Read-only Policy Boundary Verification Report

**Phase Goal:** Every operation addressing an external root is authorized by one deny-by-default policy before filesystem access.
**Verified:** 2026-08-10T13:26:46Z
**Status:** passed
**Re-verification:** Yes, after gap-closure plan 02-11

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                                                     | Status   | Evidence                                                                                                                                                                                                                                                                                                                                                                                 |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Users can perform the closed external read set while RomM-owned output remains outside the root.                                                                                          | VERIFIED | `EXTERNAL_READ_OPERATIONS` remains exactly RESOLVE, LIST, STAT, READ, SCAN, HASH, STREAM, and DOWNLOAD. The independent 868-test Phase 2 gate passed, and the dual-mount probe proved unchanged external manifests plus writable owned output.                                                                                                                                           |
| 2   | External create, upload, write, overwrite, rename, move, copy, delete, extract, patch, mkdir, sidecar, and cover attempts deny before filesystem access across API and internal channels. | VERIFIED | The policy matrix, access tripwires, endpoint denials, job denials, archive, patch, sync, watcher, and cleanup tests all passed in the independently run full gate.                                                                                                                                                                                                                      |
| 3   | Writable and container-mounted read-only fixtures produce identical application-level denials.                                                                                            | VERIFIED | `python3 backend/tools/verify_read_only_policy.py` exited 0 with identical typed pre-I/O denials, unchanged manifests, and writable owned output.                                                                                                                                                                                                                                        |
| 4   | Caller input cannot create or alter trusted external classification.                                                                                                                      | VERIFIED | `ExternalStorageDescriptor` is token-gated, `_create_external_descriptor` is private, `open_storage_access` accepts the bound descriptor and rejects raw `StorageRoot` before authorization or I/O, and composition derives authority only from trusted configuration. Regression tests passed.                                                                                          |
| 5   | The post-enforcement inventory closes every external read, mutation, and authority seam.                                                                                                  | VERIFIED | Independent focused execution passed 11/11. The AST gate separately discovers an unused aliased private-factory ImportFrom, an alias call in a distinct module/function, a neutral typed StorageRoot branch, and a neutral `container_path` accessor. Live-source equality is exactly `{("handler.filesystem.storage_composition", "build_storage_composition", "descriptor_factory")}`. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                                     | Expected                                                          | Status   | Details                                                                                                                                                 |
| ------------------------------------------------------------ | ----------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/handler/filesystem/storage_policy.py`               | Closed policy and non-public external construction                | VERIFIED | Exact eight-operation allowlist, typed denial, token-gated immutable descriptors, and private external factory are substantive and exercised.           |
| `backend/handler/filesystem/storage_access.py`               | Descriptor-relative operation capabilities                        | VERIFIED | Authorization and descriptor validation precede root/target opens; operation-specific capabilities use descriptor-relative no-follow access.            |
| `backend/handler/filesystem/storage_composition.py`          | Sole runtime external descriptor constructor                      | VERIFIED | Trusted configuration is overlap-checked before the sole live factory call in `build_storage_composition`.                                              |
| `backend/handler/filesystem/storage_inventory.py`            | Closed read/mutation inventory and authority provider declaration | VERIFIED | Every row carries disposition, enforcement, and runnable evidence; the declared authority provider matches independent live-source discovery.           |
| `backend/tests/handler/filesystem/test_storage_inventory.py` | Independent fail-closed seam discovery                            | VERIFIED | Alias resolution and typed-parameter analysis are structural and function-name independent; all four adversarial fixtures and production equality pass. |
| `backend/tools/verify_read_only_policy.py`                   | Writable/read-only parity proof                                   | VERIFIED | Independently executed with a PASS marker and exit 0.                                                                                                   |

### Key Link Verification

| From                     | To                                          | Via                                                | Status   | Details                                                                                |
| ------------------------ | ------------------------------------------- | -------------------------------------------------- | -------- | -------------------------------------------------------------------------------------- |
| `storage_composition.py` | `storage_policy.py`                         | private `_create_external_descriptor`              | VERIFIED | Independent AST equality finds exactly one production provider.                        |
| `storage_access.py`      | `storage_policy.py`                         | descriptor validation and authorization before I/O | VERIFIED | Focused and full pre-I/O tripwire suites pass.                                         |
| External read consumers  | `open_storage_access`                       | operation-specific capabilities                    | VERIFIED | Full consumer suite passes with no raw response adapter for direct downloads.          |
| Mutation consumers       | central policy or explicit owned capability | bounded denial or owned-only grant                 | VERIFIED | Inventory equality, enforcement-symbol resolution, and full mutation regressions pass. |
| Inventory AST gate       | production authority seams                  | alias-aware and typed-parameter discovery          | VERIFIED | All four independent mutants are discovered and live source remains composition-only.  |

### Data-Flow Trace (Level 4)

| Artifact                 | Data Variable                              | Source                                                                                                                                             | Produces Real Data | Status   |
| ------------------------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | -------- |
| External read flow       | trusted descriptor and requested operation | trusted config -> composition -> private factory -> handler -> `open_storage_access` -> `StoragePolicy.authorize` -> descriptor-relative `os.open` | Yes                | VERIFIED |
| Owned output flow        | explicit owned descriptor                  | closed composition-owned path map -> independent owned grant -> owned capability                                                                   | Yes                | VERIFIED |
| Inventory authority flow | AST-derived seam tuples                    | runtime Python source, independent of `INVENTORY`                                                                                                  | Yes                | VERIFIED |

### Behavioral Spot-Checks

| Behavior                      | Command                                                                                                        | Result                                            | Status |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ------ |
| Focused authority inventory   | containerized pytest for `test_storage_inventory.py -x -q`                                                     | 11 passed, 1 existing Alembic warning             | PASS   |
| Complete Phase 2 regression   | exact 02-11 Phase 2 test list in repository image with MariaDB namespace and disposable Valkey                 | 868 passed, 8 skipped, 1 existing Alembic warning | PASS   |
| Four independent AST evasions | focused tests for unused aliased import, distinct-scope alias call, neutral typed branch, and neutral accessor | all four discovered and rejected                  | PASS   |
| Production authority equality | `test_runtime_authority_seams_are_closed_and_composition_only`                                                 | composition-only exact equality                   | PASS   |

### Probe Execution

| Probe                       | Command                                            | Result              | Status |
| --------------------------- | -------------------------------------------------- | ------------------- | ------ |
| Phase 2 dual-mount verifier | `python3 backend/tools/verify_read_only_policy.py` | PASS marker, exit 0 | PASS   |

### Requirements Coverage

| Requirement | Source Plans                             | Description                                                   | Status    | Evidence                                                                                                             |
| ----------- | ---------------------------------------- | ------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------- |
| ROOT-05     | 02-01, 02-03, 02-06, 02-09               | RomM-owned writable storage remains explicit and disjoint     | SATISFIED | Closed composition and dual-mount owned-output proof pass.                                                           |
| SAFE-01     | 02-01, 02-02, 02-04, 02-08, 02-10, 02-11 | External reads use the closed central policy                  | SATISFIED | Exact allowlist and full read-consumer regression pass.                                                              |
| SAFE-02     | 02-01, 02-03, 02-05 through 02-09        | External mutations deny before I/O                            | SATISFIED | Policy, endpoint, job, and dual-mount tripwires pass.                                                                |
| SAFE-03     | 02-05, 02-09                             | Denials are bounded and channel-correct                       | SATISFIED | HTTP and internal denial tests pass without path disclosure.                                                         |
| SAFE-04     | 02-03 through 02-11                      | Every filesystem and authority seam is governed or owned-only | SATISFIED | Independent AST discovery is now alias-aware and function-name independent; production equality is composition-only. |
| SAFE-05     | 02-09                                    | Writable and read-only mount denials are identical            | SATISFIED | Dual-mount verifier passed independently.                                                                            |
| SAFE-06     | 02-02 through 02-09                      | Owned output is separated from immutable source               | SATISFIED | Capability surface, unchanged manifests, and owned-output evidence pass.                                             |
| TEST-03     | 02-01 through 02-11                      | Adversarial policy and inventory evidence                     | SATISFIED | Focused 11-test inventory, full 868-test suite, and dual-mount probe pass.                                           |

No Phase 2 requirement is orphaned from plan frontmatter.

### Anti-Patterns Found

No unreferenced TBD, FIXME, or XXX debt markers and no goal-blocking stubs were found in the policy, access, composition, inventory, inventory-test, or dual-mount-probe artifacts.

### Human Verification Required

None. This phase is a programmatically checkable backend policy and inventory boundary.

### Gaps Summary

No gaps remain. Plan 02-11 closes the prior independent-discovery failure without changing production policy. The four required evasion classes are separately detected, live production authority is exactly composition-only, and the focused, complete, and dual-mount gates all pass independently.

---

_Verified: 2026-08-10T13:26:46Z_
_Verifier: the agent (gsd-verifier)_
