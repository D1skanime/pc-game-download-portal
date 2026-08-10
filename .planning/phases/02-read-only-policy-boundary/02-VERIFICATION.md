---
phase: 02-read-only-policy-boundary
verified: 2026-08-10T10:58:06Z
status: gaps_found
score: 3/5 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Caller-supplied path text cannot create or alter a trusted external classification"
    status: failed
    reason: "The public create_external_descriptor() accepts any caller-constructed StorageRoot, including an unsaved model with an arbitrary container_path and caller-assigned id. open_storage_access() also accepts StorageRoot directly and converts it through that factory. Composition is therefore not the sole authority for external identity."
    artifacts:
      - path: "backend/handler/filesystem/storage_policy.py"
        issue: "Public create_external_descriptor() trusts any StorageRoot instance rather than a composition-owned descriptor."
      - path: "backend/handler/filesystem/storage_access.py"
        issue: "open_storage_access() accepts raw StorageRoot and derives authority from its container_path."
      - path: "backend/tests/handler/filesystem/test_storage_policy.py"
        issue: "Tests normalize the bypass by creating unsaved StorageRoot objects with arbitrary paths and passing them to the public factory."
    missing:
      - "Remove the raw StorageRoot compatibility path from open_storage_access()."
      - "Restrict external descriptor construction to trusted composition or database identity resolution, with a regression test proving arbitrary in-memory StorageRoot/path input cannot gain access."
  - truth: "Every existing filesystem mutation and read seam is governed by the central policy or structurally unable to address an external root"
    status: failed
    reason: "The closed inventory does not classify the public raw-StorageRoot descriptor factory/access path, so its discovery-equality claim is incomplete and SAFE-04 is not established."
    artifacts:
      - path: "backend/handler/filesystem/storage_inventory.py"
        issue: "Inventory lists build_storage_composition as the identity provider but omits create_external_descriptor and the raw StorageRoot branch in open_storage_access."
      - path: "backend/tests/handler/filesystem/test_storage_inventory.py"
        issue: "The AST gate passes by construction without rejecting this alternative classification/access seam."
    missing:
      - "Extend discovery to reject every external descriptor factory or raw StorageRoot access path outside trusted composition."
      - "Re-run the inventory and full Phase 2 suite after closing the bypass."
---

# Phase 2: Read-only Policy Boundary Verification Report

**Phase Goal:** Every operation addressing an external root is authorized by one deny-by-default policy before filesystem access.
**Verified:** 2026-08-10T10:58:06Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                                         | Status   | Evidence                                                                                                                                                                                                                                                                                        |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Users can perform the closed external read set while RomM-owned output remains outside the root.                                                                              | VERIFIED | `StorageOperation` and `EXTERNAL_READ_OPERATIONS` define RESOLVE/LIST/STAT/READ/SCAN/HASH/STREAM/DOWNLOAD; descriptor-relative capabilities and separately bound owned descriptors are substantive. The dual-mount verifier passed with unchanged manifests and writable owned output.          |
| 2   | External create/upload/write/overwrite/rename/move/copy/delete/extract/patch/mkdir/sidecar/cover attempts deny before filesystem access, including API and internal channels. | VERIFIED | Pure policy/access tests reached 292 passes before the environment-dependent suite setup; code routes mutation operations through `StoragePolicyDenied`, and tests contain pre-I/O tripwires plus bounded HTTP/job assertions.                                                                  |
| 3   | Writable and container-mounted read-only fixtures produce identical application-level denials.                                                                                | VERIFIED | `python3 backend/tools/verify_read_only_policy.py` exited 0: `PASS: writable and :ro mounts produced identical pre-I/O typed denials, unchanged manifests, and writable owned output`.                                                                                                          |
| 4   | Caller input cannot create or alter trusted external classification.                                                                                                          | FAILED   | `storage_policy.py:128-138` publicly converts any caller-created `StorageRoot` and its `container_path`; `storage_access.py:244-253` accepts raw `StorageRoot` and invokes that factory. `test_storage_policy.py:38-56,153` constructs unsaved arbitrary-path roots and treats them as trusted. |
| 5   | The post-enforcement inventory closes every external read/mutation seam.                                                                                                      | FAILED   | The inventory names composition as the trusted provider but does not inventory or reject the public `create_external_descriptor()` and raw-`StorageRoot` branch. Its equality gate therefore cannot prove SAFE-04.                                                                              |

**Score:** 3/5 truths verified

### Required Artifacts

| Artifact                                            | Expected                                             | Status   | Details                                                                                                                         |
| --------------------------------------------------- | ---------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `backend/handler/filesystem/storage_policy.py`      | Closed deny-by-default policy and trusted identities | PARTIAL  | Policy matrix is substantive, but external identity construction is publicly forgeable from an arbitrary model/path.            |
| `backend/handler/filesystem/storage_access.py`      | Operation-bound descriptor-relative capabilities     | PARTIAL  | Capabilities are substantive and no-follow, but the public entry point accepts raw `StorageRoot` and creates authority from it. |
| `backend/handler/filesystem/storage_composition.py` | Sole trusted root composition                        | VERIFIED | Builds one legacy external descriptor and ten explicit owned descriptors after lexical overlap validation.                      |
| `backend/handler/filesystem/storage_inventory.py`   | Closed runtime seam registry                         | FAILED   | Omits the alternative descriptor-construction/access seam.                                                                      |
| `backend/tools/verify_read_only_policy.py`          | Writable/:ro parity proof                            | VERIFIED | Executed independently and passed.                                                                                              |
| `backend/docker-compose.policy-test.yml`            | Dual fixture mount contract                          | VERIFIED | Wired to the verifier and used successfully.                                                                                    |
| `examples/docker-compose.example.yml`               | External `:ro`, owned storage separate               | VERIFIED | Deployment example contains separated mounts; verifier confirms the test composition.                                           |

### Key Link Verification

| From                     | To                          | Via                                     | Status           | Details                                                                                              |
| ------------------------ | --------------------------- | --------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------- |
| storage consumers        | `storage_access.py`         | exact operation capabilities            | VERIFIED         | Production consumers call `open_storage_access`; capability classes bind an already-open descriptor. |
| `storage_access.py`      | `storage_policy.py`         | authorize before target open            | VERIFIED         | `StoragePolicy.authorize()` precedes normalization and `_open_target()`.                             |
| `storage_composition.py` | owned/external handlers     | immutable descriptors                   | VERIFIED         | Filesystem singletons receive composition-built descriptors.                                         |
| caller/model path        | trusted external descriptor | public factory/raw compatibility branch | NOT_WIRED SAFELY | This is an unauthorized parallel trust path that bypasses composition ownership.                     |
| inventory tests          | production seams            | AST discovery equality                  | PARTIAL          | Discovery does not identify the parallel descriptor factory/access path.                             |

### Data-Flow Trace (Level 4)

Not applicable to UI rendering. Security data flow was traced instead: `StorageRoot.container_path` -> `create_external_descriptor()` -> descriptor `_root_path` -> `open_storage_access()` -> `_open_root()`/`os.open()`. This is real data flow and demonstrates the gap.

### Behavioral Spot-Checks

| Behavior                                         | Command                                                                             | Result                                                                                    | Status  |
| ------------------------------------------------ | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------- |
| Pure policy/access/owned prefix of Phase 2 suite | canonical pytest list with `-x -q` in `romm-dev`                                    | 292 passed, then database setup attempted `127.0.0.1:3306` and errored                    | WARNING |
| Inventory gate                                   | `uv run pytest tests/handler/filesystem/test_storage_inventory.py -q` in `romm-dev` | 6 setup errors because `backend/pytest.ini` forces DB_HOST=127.0.0.1 inside the container | WARNING |
| Dual-mount parity                                | `python3 backend/tools/verify_read_only_policy.py`                                  | exit 0, identical typed denials and unchanged manifests                                   | PASS    |

The pytest failures are environment/setup failures rather than assertion failures. They do not create the blocker verdict; the source-level trust bypass does.

### Probe Execution

| Probe                       | Command                                            | Result                  | Status |
| --------------------------- | -------------------------------------------------- | ----------------------- | ------ |
| Phase 2 dual-mount verifier | `python3 backend/tools/verify_read_only_policy.py` | exit 0 with PASS marker | PASS   |

### Requirements Coverage

| Requirement | Source Plans               | Status    | Evidence                                                                                                                    |
| ----------- | -------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------- |
| ROOT-05     | 02-01, 02-03, 02-06, 02-09 | SATISFIED | Ten owned kinds are explicitly bound outside the external root; dual-mount verifier confirms owned output remains writable. |
| SAFE-01     | 02-01, 02-04, 02-08, 02-09 | SATISFIED | Exact external allowlist and operation capabilities exist and are exercised.                                                |
| SAFE-02     | 02-01, 02-03, 02-05..02-09 | SATISFIED | Mutation matrix denies external operations before I/O.                                                                      |
| SAFE-03     | 02-05, 02-09               | SATISFIED | Typed bounded `external_storage_operation_denied` translation and route matrix exist.                                       |
| SAFE-04     | 02-03..02-09               | BLOCKED   | Inventory misses the raw model-to-descriptor/access seam, so complete governance is false.                                  |
| SAFE-05     | 02-09                      | SATISFIED | Example uses `:ro`; independent dual-mount verifier passed.                                                                 |
| SAFE-06     | 02-02..02-09               | SATISFIED | Descriptor reads and parity manifest proof show no source-side output.                                                      |
| TEST-03     | 02-01..02-09               | SATISFIED | Mutation/pre-I/O matrices are substantive; 292 tests passed before DB-dependent setup and the mount verifier passed.        |

No Phase 2 requirement is orphaned from plan frontmatter.

### Anti-Patterns Found

| File                                                      | Line | Pattern                                                        | Severity | Impact                                                        |
| --------------------------------------------------------- | ---- | -------------------------------------------------------------- | -------- | ------------------------------------------------------------- |
| `backend/handler/filesystem/storage_policy.py`            | 128  | Public trust factory accepts arbitrary in-memory `StorageRoot` | BLOCKER  | Caller-selected absolute path becomes an external descriptor. |
| `backend/handler/filesystem/storage_access.py`            | 244  | Raw `StorageRoot` compatibility overload                       | BLOCKER  | Parallel authority path bypasses composition ownership.       |
| `backend/tests/handler/filesystem/test_storage_policy.py` | 38   | Test helper assigns id to unsaved arbitrary-path model         | BLOCKER  | Tests endorse rather than reject classification forgery.      |

No unreferenced TBD, FIXME, or XXX debt markers were found in the central Phase 2 policy/access/composition/inventory/verifier files.

### Human Verification Required

None. The blocking gap is directly observable in code, and all Phase 2 behavior is specified as automatable. The database-host setup warning should be corrected or rerun in a properly networked test environment after the code gap is fixed.

### Gaps Summary

The policy denies mutations correctly once given an external descriptor, but the trust boundary that creates that descriptor is not closed. Any caller can construct an unsaved `StorageRoot` with a chosen absolute container path and id, then pass it through the public factory or directly to `open_storage_access()`. The inventory does not detect this alternate seam. Consequently the phase goal, D-04/D-13/D-15, and SAFE-04 are not achieved even though the policy matrix and dual-mount denial verifier pass.
