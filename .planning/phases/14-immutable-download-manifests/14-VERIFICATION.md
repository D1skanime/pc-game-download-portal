---
phase: 14-immutable-download-manifests
verified: 2026-09-16T12:31:49Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "Every manifest snapshot is the exact strong validator over the public opaque manifest-member ID, destination, size, and verified SHA-256."
    - "The persisted aggregate rejects an invalid source-member-to-selected-component ownership topology."
  gaps_remaining: []
  regressions: []
---

# Phase 14: Immutable Download Manifests Verification Report

**Phase Goal:** A selected whole PC game or component set has one immutable, hash-backed download manifest without changing the source library.
**Verified:** 2026-09-16T12:31:49Z
**Status:** passed
**Re-verification:** Yes, after gap closure

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                          | Status   | Evidence                                                                                                                                                                                                                                                                                                                                                                                                        |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | A signed-in visible user can create a whole-game or exact eligible base, update, DLC, or extra selection and retrieve only their own JSON manifest.            | VERIFIED | `create_manifest` locks and selects only the four eligible kinds. Both routes require `ROMS_READ`; POST checks the requested ROM and GET checks the persisted canonical ROM with `assert_rom_visible`. Focused endpoint and handler tests passed.                                                                                                                                                               |
| 2   | Every manifest member has a path-free safe destination, exact size, SHA-256, and the exact strong snapshot formula using the public opaque manifest-member ID. | VERIFIED | The handler creates `DownloadManifestMember(public_id=str(uuid4()))` before calling capture. `capture_download_manifest_member` passes that ID into `_download_manifest_snapshot`, whose tested NUL-separated input is `romm-manifest-v1`, public ID, destination, decimal size, and verified lowercase SHA-256. The same persisted `public_id` is serialized as `file_id` and is the final future URL segment. |
| 3   | VALID, EXPIRED, REVOKED, and SOURCE_CHANGED remain distinct and prevent partial lists.                                                                         | VERIFIED | The closed status enum is persisted. GET expires before revalidation, sets `SOURCE_CHANGED` on a light-check mismatch, and the route maps expired/revoked to 410 and changed to 409 before serialization. All three state regressions passed.                                                                                                                                                                   |
| 4   | The persisted aggregate is user-owned, path-free, and source-library non-mutating.                                                                             | VERIFIED | Models persist user/ROM/component/member identities and evidence only, with no source path columns. Creation uses the read-only HASH capability; normal revalidation uses STAT. The manifest router has only JSON POST/GET routes and no source mutation or delivery implementation.                                                                                                                            |
| 5   | Invalid source-member ownership topology is rejected at the durable aggregate boundary.                                                                        | VERIFIED | `DownloadManifestMember` carries `component_id` and has composite foreign keys to both selected `(id, component_id)` and source `(id, component_id)` pairs. Migration 0121 adds the corresponding portable constraints. The focused direct ORM/database attack pairing selected component A with a source member from B raised `IntegrityError` at flush without handler validation.                            |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                                                          | Expected                                                    | Status   | Details                                                                                                                                                                          |
| --------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/models/download_manifest.py`                                             | Immutable aggregate, opaque member ID, and durable topology | VERIFIED | Substantive ORM model with unique public ID and paired composite foreign keys. Used by handler and API.                                                                          |
| `backend/models/rom.py`                                                           | Composite source-key target                                 | VERIFIED | Named `uq_rom_component_manifest_members_id_component` supports the portable source composite foreign key.                                                                       |
| `backend/alembic/versions/0121_download_manifest_member_identity_and_topology.py` | Upgrade/downgrade public IDs and ownership topology         | VERIFIED | Substantive revision chained after 0120; it backfills non-null fields, adds named unique/composite FKs, and removes them in downgrade.                                           |
| `backend/handler/filesystem/roms_handler.py`                                      | HASH capture and STAT-only ordinary revalidation            | VERIFIED | Capture computes the canonical strong snapshot after full HASH evidence. Normal light revalidation opens only `StorageOperation.STAT`; its regression makes HASH fail if called. |
| `backend/handler/database/download_manifests_handler.py`                          | Atomic selection, pre-capture ID allocation, lifecycle      | VERIFIED | Generates the public UUID before capture, retains it on the pending member, then flushes the completed aggregate in the transaction.                                             |
| `backend/endpoints/download_manifests.py`                                         | Protected JSON-only creation and retrieval                  | VERIFIED | Registered in `backend/main.py`; serializes public IDs only, applies owner and visibility masking, and provides no file-delivery route.                                          |
| `backend/endpoints/responses/download_manifest.py`                                | Strict path-free UUID manifest response                     | VERIFIED | Schema permits UUID-format `file_id`, safe manifest fields, and only the relative future URL shape.                                                                              |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- |
| Manifest creation | Filesystem capture | preallocated `pending_member.public_id` argument before HASH read | WIRED | Handler creates the UUID at line 145 and passes `pending_member.public_id` at lines 150-151. |
| Filesystem snapshot | API member response | identical public ID in snapshot input, `file_id`, and future URL | WIRED | Filesystem test independently computes the exact NUL serialization; serializer uses `member.public_id` for both public fields. |
| Manifest member ORM | Source and selected component tables | paired `(id, component_id)` composite foreign keys | WIRED | Both target unique constraints and both foreign keys are present in model and 0121 DDL. Direct persistence test proves the database rejects a mismatched pair. |
| API router | Database handler and app | protected POST/GET, handler calls, main router registration | WIRED | Router calls `db_download_manifest_handler`; `backend/main.py` includes it under `/api`. |

### Data-Flow Trace (Level 4)

| Artifact                                         | Data Variable                            | Source                                                          | Produces Real Data | Status  |
| ------------------------------------------------ | ---------------------------------------- | --------------------------------------------------------------- | ------------------ | ------- |
| `FSRomsHandler.capture_download_manifest_member` | size, SHA-256, snapshot, stat indicators | descriptor-backed HASH plus before/after `fstat`                | Yes                | FLOWING |
| `DBDownloadManifestsHandler.create_manifest`     | persisted public ID and evidence         | UUID allocated in the same aggregate before capture             | Yes                | FLOWING |
| `DBDownloadManifestsHandler.get_manifest`        | lifecycle state                          | persisted aggregate plus descriptor-backed STAT-only indicators | Yes                | FLOWING |
| Manifest router                                  | response members                         | persisted component/member fields                               | Yes                | FLOWING |

### Behavioral Spot-Checks

| Behavior                                                                                  | Command                                                                                                                                                                                                                                                                        | Result                                                                                                                                                                                                                                                                                        | Status |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Public-ID snapshot binding, topology, selection, lifecycle, authorization, and disclosure | `cd backend && uv run pytest tests/models/test_download_manifest.py tests/handler/database/test_download_manifests_handler.py tests/handler/filesystem/test_roms_handler.py tests/endpoints/test_download_manifests.py -k 'download_manifest or download_manifest_member' -vv` | 20 passed, 80 deselected in 6.53s                                                                                                                                                                                                                                                             | PASS   |
| Exact canonical snapshot                                                                  | focused filesystem regression in that command                                                                                                                                                                                                                                  | Independently constructs the NUL-separated bytes with the passed opaque UUID and asserts the quoted SHA-256 snapshot                                                                                                                                                                          | PASS   |
| Direct cross-component persistence attack                                                 | focused model regression in that command                                                                                                                                                                                                                                       | Direct insertion of component-B source member under selected component A raised `IntegrityError`                                                                                                                                                                                              | PASS   |
| Alembic CLI inspection                                                                    | `ROMM_AUTH_SECRET_KEY=verification-only-secret uv run alembic heads`                                                                                                                                                                                                           | SKIP: repository config attempted to initialize inaccessible `/romm/assets` before migration inspection. No database migration or source mutation occurred. Model-level direct database constraint regression passed, and 0118 -> 0119 -> 0120 -> 0121 chain and portable DDL were inspected. | SKIP   |

### Probe Execution

No Phase 14 probe was declared. The repository has no `scripts/` probe directory. SKIPPED.

### Requirements Coverage

| Requirement | Source Plan                | Description                                                                                       | Status    | Evidence                                                                                                                       |
| ----------- | -------------------------- | ------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------ |
| DLMT-01     | 14-02, 14-03               | Whole PC game or specific base, update, DLC, and extra selection                                  | SATISFIED | Eligible-kind query, exact-ID validation, protected API, and focused whole-game/exact-selection tests.                         |
| DLMT-02     | 14-01, 14-02, 14-03, 14-04 | Immutable selected manifest with safe paths, sizes, SHA-256, public identity, and strong snapshot | SATISFIED | Exact public-ID snapshot binding, path-free serialization, 64-bit values, durable topology, and direct persistence regression. |
| DLMT-03     | 14-01, 14-02, 14-03        | Expired, changed, or ambiguous manifests fail before mixed versions                               | SATISFIED | Separate lifecycle states, expiry-first light revalidation, and bounded endpoint results.                                      |

### Anti-Patterns Found

No phase-owned file contains `TBD`, `FIXME`, `XXX`, unreferenced placeholder text, empty visible implementation, or hardcoded empty manifest data.

The broader filesystem handler has pre-existing archive-reading code outside the Phase 14 capture path. The manifest router itself has no `StreamingResponse`, `FileResponse`, `Range`, `If-Match`, ZIP, transfer, Tauri, or handoff implementation. The only `/files/{public_id}` value is a future relative identifier; no matching route exists in Phase 14. This preserves the Phase 15 transfer boundary.

### Human Verification Required

None. The phase is backend-only and all roadmap and re-verification truths are deterministically covered by code inspection and focused executable tests.

### Gaps Summary

The two prior blockers are closed. The public opaque UUID is now preallocated and carried unchanged through snapshot construction, durable storage, JSON, and the future URL. The selected-component/source-member relationship is enforced by database constraints, not only by handler selection. Phase 14 remains an immutable JSON-manifest boundary without delivery authority.

---

_Verified: 2026-09-16T12:31:49Z_
_Verifier: the agent (gsd-verifier)_
