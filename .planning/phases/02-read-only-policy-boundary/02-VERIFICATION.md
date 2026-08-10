---
phase: 02-read-only-policy-boundary
verified: 2026-08-10T11:49:49Z
status: gaps_found
score: 4/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "Caller-supplied path text cannot create or alter a trusted external classification"
  gaps_remaining:
    - "Every existing filesystem mutation and read seam is governed by the central policy or structurally unable to address an external root"
  regressions: []
gaps:
  - truth: "Every existing filesystem mutation and read seam is governed by the central policy or structurally unable to address an external root"
    status: failed
    reason: "The independent AST authority discovery is not closed. It misses an aliased import/call of _create_external_descriptor and misses a StorageRoot.container_path accessor whose function name is not one of open/access/authorize/descriptor. A verifier-seeded pair of these mutants produced an empty discovered seam set, so the equality gate can pass while parallel authority seams exist."
    artifacts:
      - path: "backend/tests/handler/filesystem/test_storage_inventory.py"
        issue: "_authority_seams() searches only the literal function-local name _create_external_descriptor and gates raw StorageRoot detection on selected function-name substrings; it does not resolve import aliases and does not inspect every typed raw-root accessor."
      - path: "backend/handler/filesystem/storage_inventory.py"
        issue: "The declared composition-only provider is sound for current production source, but its independent discovery enforcement is incomplete."
    missing:
      - "Make AST discovery resolve ImportFrom aliases and calls through those aliases, rejecting private-factory imports/calls outside trusted composition."
      - "Detect StorageRoot parameters that branch on the model or access container_path regardless of function naming."
      - "Add seeded alias-import/call and neutrally named raw-root mutants, then rerun focused inventory and full Phase 2 gates."
---

# Phase 2: Read-only Policy Boundary Verification Report

**Phase Goal:** Every operation addressing an external root is authorized by one deny-by-default policy before filesystem access.
**Verified:** 2026-08-10T11:49:49Z
**Status:** gaps_found
**Re-verification:** Yes, after gap-closure plan 02-10

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                                         | Status   | Evidence                                                                                                                                                                                                                                                                                                            |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Users can perform the closed external read set while RomM-owned output remains outside the root.                                                                              | VERIFIED | The exact read allowlist remains RESOLVE/LIST/STAT/READ/SCAN/HASH/STREAM/DOWNLOAD. The full Phase 2 suite passed, and the dual-mount verifier confirmed unchanged external manifests plus writable owned output.                                                                                                    |
| 2   | External create/upload/write/overwrite/rename/move/copy/delete/extract/patch/mkdir/sidecar/cover attempts deny before filesystem access, including API and internal channels. | VERIFIED | Policy/access and endpoint/job tests passed in the 865-test full gate. The dual-mount verifier observed identical typed pre-I/O denials on writable and read-only mounts.                                                                                                                                           |
| 3   | Writable and container-mounted read-only fixtures produce identical application-level denials.                                                                                | VERIFIED | `python3 backend/tools/verify_read_only_policy.py` exited 0 with its PASS marker for denial parity, unchanged manifests, and writable owned output.                                                                                                                                                                 |
| 4   | Caller input cannot create or alter trusted external classification.                                                                                                          | VERIFIED | The public `create_external_descriptor` surface is absent. `open_storage_access()` accepts only `ExternalStorageDescriptor`, rejects raw/unsaved `StorageRoot` before authorization, normalization, or I/O, and descriptor construction is token-gated. Focused tests passed 297/297.                               |
| 5   | The post-enforcement inventory closes every external read/mutation and authority seam.                                                                                        | FAILED   | Current production source has only the composition call, but `_authority_seams()` misses aliased private-factory calls and neutrally named raw `StorageRoot.container_path` accessors. An independent seeded probe returned `[]` for both mutants, contradicting the plan's every-import/call/raw-seam requirement. |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact                                                     | Expected                                             | Status   | Details                                                                                                                             |
| ------------------------------------------------------------ | ---------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `backend/handler/filesystem/storage_policy.py`               | Closed policy and non-public external construction   | VERIFIED | Public model factory removed; external descriptor constructor requires the private token; `_create_external_descriptor` is private. |
| `backend/handler/filesystem/storage_access.py`               | Descriptor-only operation capabilities               | VERIFIED | Raw `StorageRoot` support is removed; type check at lines 246-247 precedes policy, normalization, and target opening.               |
| `backend/handler/filesystem/storage_composition.py`          | Sole current runtime external descriptor constructor | VERIFIED | The only current runtime call to `_create_external_descriptor` is in `build_storage_composition`, after disjoint-root validation.   |
| `backend/handler/filesystem/storage_inventory.py`            | Closed authority inventory                           | PARTIAL  | Declares composition as the authority provider, but enforcement depends on incomplete test-side AST discovery.                      |
| `backend/tests/handler/filesystem/test_storage_inventory.py` | Independent fail-closed authority discovery          | FAILED   | Literal-name and function-name heuristics allow simple alias and raw-root mutants to evade detection.                               |
| `backend/tools/verify_read_only_policy.py`                   | Writable/read-only parity proof                      | VERIFIED | Independently executed and passed. The private factory use is isolated under excluded `backend/tools`.                              |

### Key Link Verification

| From                         | To                         | Via                                   | Status        | Details                                                                                       |
| ---------------------------- | -------------------------- | ------------------------------------- | ------------- | --------------------------------------------------------------------------------------------- |
| `storage_composition.py`     | `storage_policy.py`        | private `_create_external_descriptor` | VERIFIED      | Exactly one current runtime factory call was found, in `build_storage_composition`.           |
| `storage_access.py`          | `storage_policy.py`        | descriptor authorization before I/O   | VERIFIED      | Runtime type rejection precedes `StoragePolicy.authorize`, normalization, and `_open_target`. |
| caller-created `StorageRoot` | external access            | raw model input                       | VERIFIED SAFE | Regression tripwires establish rejection before authorization and filesystem access.          |
| inventory AST gate           | production authority seams | syntax-derived equality               | NOT CLOSED    | Alias imports/calls and neutrally named raw-root accessors are not discovered.                |

### Data-Flow Trace (Level 4)

Security flow is `trusted_storage_config` -> `build_storage_composition` -> `_create_external_descriptor` -> `ExternalFSHandler.storage` -> `open_storage_access` -> `StoragePolicy.authorize` -> descriptor-relative `os.open`. No current production `StorageRoot.container_path` path reaches `open_storage_access`. The failed independent mutant probe shows the inventory cannot guarantee this remains exclusive.

### Behavioral Spot-Checks

| Behavior                             | Command                                                                                                                | Result                                            | Status |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ------ |
| Focused authority and inventory gate | containerized pytest for policy/access/inventory                                                                       | 297 passed, 1 existing Alembic warning            | PASS   |
| Full Phase 2 regression              | exact 02-10 Phase 2 test list in repository image with MariaDB namespace and disposable Valkey                         | 865 passed, 8 skipped, 1 existing Alembic warning | PASS   |
| Raw unsaved model rejection          | focused `test_raw_storage_root_is_rejected_before_authorization_or_io` within gate                                     | passed                                            | PASS   |
| Independent AST evasion probe        | seed aliased factory call plus `resolve_root(root: StorageRoot)` reading `container_path`, invoke `_authority_seams()` | returned `[]`                                     | FAIL   |

### Probe Execution

| Probe                       | Command                                            | Result              | Status |
| --------------------------- | -------------------------------------------------- | ------------------- | ------ |
| Phase 2 dual-mount verifier | `python3 backend/tools/verify_read_only_policy.py` | PASS marker, exit 0 | PASS   |

### Requirements Coverage

| Requirement | Source Plans                      | Status    | Evidence                                                                                                                              |
| ----------- | --------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| ROOT-05     | 02-01, 02-03, 02-06, 02-09        | SATISFIED | Closed owned kinds remain disjoint; dual-mount proof confirms owned output remains writable.                                          |
| SAFE-01     | 02-01, 02-04, 02-08, 02-09, 02-10 | SATISFIED | External allowlist and descriptor-only access are enforced and tested.                                                                |
| SAFE-02     | 02-01, 02-03, 02-05..02-09        | SATISFIED | Mutation attempts deny before I/O in full regression and mount probe.                                                                 |
| SAFE-03     | 02-05, 02-09                      | SATISFIED | Bounded HTTP/internal denial tests pass.                                                                                              |
| SAFE-04     | 02-03..02-10                      | BLOCKED   | Current seams are governed, but the promised fail-closed inventory does not discover all parallel factory/import/call/raw-root forms. |
| SAFE-05     | 02-09                             | SATISFIED | Writable and `:ro` parity verifier passed.                                                                                            |
| SAFE-06     | 02-02..02-09                      | SATISFIED | External manifests remain unchanged and owned output stays separate.                                                                  |
| TEST-03     | 02-01..02-10                      | SATISFIED | Focused, full, and dual-mount suites pass; the additional adversarial inventory probe exposes the remaining coverage gap.             |

No Phase 2 requirement is orphaned from plan frontmatter.

### Anti-Patterns Found

| File                                                         | Line    | Pattern                                                                      | Severity | Impact                                                                                    |
| ------------------------------------------------------------ | ------- | ---------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------- |
| `backend/tests/handler/filesystem/test_storage_inventory.py` | 267-304 | AST discovery relies on literal symbol and selected function-name heuristics | BLOCKER  | A parallel authority seam can be introduced while the closed-equality test remains green. |

No unreferenced TBD, FIXME, or XXX markers were found in the six 02-10 policy/access/inventory files.

### Human Verification Required

None. The phase is backend policy/inventory work, and the remaining failure is directly reproducible programmatically.

### Gaps Summary

Plan 02-10 closes the original caller-created `StorageRoot` and selected-path authority bypass. Runtime access is descriptor-only, and all focused, full, and dual-mount tests pass. The second prior gap remains because the new independent inventory does not satisfy its own fail-closed contract: ordinary import aliasing evades private-factory discovery, and raw `StorageRoot.container_path` use is ignored unless the function name contains one of four selected substrings. Since SAFE-04 and truth 5 require every seam to be discovered, this is a blocker rather than a warning.

---

_Verified: 2026-08-10T11:49:49Z_
_Verifier: the agent (gsd-verifier)_
