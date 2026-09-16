---
phase: 15-direct-resumable-transfer
verified: 2026-09-16T22:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 15: Direct Resumable Transfer Verification Report

**Phase Goal:** The server transfers each manifest file directly and safely resumes large partial files without packaging or extracting content.
**Verified:** 2026-09-16T22:00:00Z
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                                                                | Status   | Evidence                                                                                                                                                                                                                                                                                                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | A 100-GB-class original member is delivered as itself, without a whole-game ZIP, ZIP part, extraction, directory response, or source path.                                                           | VERIFIED | The only new public route is the opaque member route in `backend/endpoints/download_manifests.py`. It returns `StreamingResponse` over `DownloadManifestTransferLease.iter_chunks`; it has no archive or path input. The direct endpoint regression asserts original bytes and a non-ZIP content type.                                                                                        |
| 2   | Every request is authenticated with `ROMS_READ`, then constrained to the current owner, the requested opaque member under that manifest, current ROM visibility, and manifest lifecycle.             | VERIFIED | The route has unconditional `@protected_route(..., [Scope.ROMS_READ])`, invokes `get_transfer_manifest_member(manifest_id, request.user.id, public_id)`, applies `assert_rom_visible`, then the closed lifecycle envelope. The handler query constrains manifest ID, user ID, and `DownloadManifestMember.public_id`; focused foreign-owner, foreign-member, and hidden-ROM regressions pass. |
| 3   | Before any stream exists, the member is freshly HASH-verified and its recomputed Phase-14 strong snapshot exactly matches the persisted quoted snapshot.                                             | VERIFIED | `open_verified_download_manifest_member` obtains a `HASH` capability, checks regular-file identity before and after SHA-256, recomputes `_download_manifest_snapshot(public_id, destination, size, sha256)`, and compares size, digest, destination, identity indicators, and snapshot before constructing a lease. Mismatch produces `SOURCE_CHANGED` with no lease.                         |
| 4   | A valid range continuation is unambiguously partial, with exact offsets and totals; malformed, multi-range, overflow, inverted, and unsatisfiable inputs cannot fall back to an appendable response. | VERIFIED | `_transfer_range_bounds` accepts one ASCII decimal `bytes` range only, explicitly bounds values to u64, and sends 416 plus `Content-Range: bytes */total` for all invalid cases. The route returns 200 only for no Range and 206 with exact `Content-Range` and `Content-Length` for a valid range.                                                                                           |
| 5   | Resume requires exactly the stored strong quoted `If-Match`; weak, missing, wildcard/list, stale, and altered validators fail before transfer verification or source streaming.                      | VERIFIED | The route compares `If-Match` byte-for-byte to the persisted Phase-14 snapshot and requires it whenever `Range` is supplied. The invalid-validator regression covers missing, `W/`, wildcard, list, and stale forms and proves the transfer opener is not called. Phase 14 constructs snapshots as quoted SHA-256 validators, never weak validators.                                          |
| 6   | Concurrent source verification and long-lived streams are bounded, cleaned up on normal, early-close, and read-error exits, and do not mutate the external source.                                   | VERIFIED | `DOWNLOAD_MANIFEST_TRANSFER_MAX_CONCURRENCY` is positive and process-local. The lease acquires before HASH and releases exactly once from its iterator/close path after closing the descriptor. Isolated tests prove blocked capacity and release after early close and read error, plus byte-for-byte source-tree preservation.                                                              |
| 7   | Size and offset accounting remains exact above 4 GiB without allocating large files.                                                                                                                 | VERIFIED | Filesystem and endpoint regressions use synthetic 5 GiB, 80 GiB, and 120 GiB totals and exact terminal offsets. The focused test run passed all of them.                                                                                                                                                                                                                                      |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact                                                            | Expected                                                            | Status   | Details                                                                                                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/handler/database/download_manifests_handler.py`            | Owner- and member-scoped transfer resolution                        | VERIFIED | Substantive eager query rooted at persisted opaque member identity, with expiry transition only and no normal GET light revalidation.           |
| `backend/config/__init__.py`                                        | Validated transfer concurrency limit                                | VERIFIED | `DOWNLOAD_MANIFEST_TRANSFER_MAX_CONCURRENCY` uses `safe_int` and `max(1, ...)`.                                                                 |
| `backend/handler/filesystem/roms_handler.py`                        | Read-only strong verification and descriptor-backed lease           | VERIFIED | Implements typed transfer state/result/lease, HASH verification, exact snapshot comparison, sequential bounded reads, and idempotent cleanup.   |
| `backend/endpoints/download_manifests.py`                           | Protected opaque direct single-range endpoint                       | VERIFIED | Registered API router exposes the Phase-14 member URL and has concrete authorization, precondition, range, response-header, and cleanup wiring. |
| `backend/tests/handler/database/test_download_manifests_handler.py` | Lookup/lifecycle regressions                                        | VERIFIED | Covers owner, manifest, opaque member, internal ID, lifecycle, and absence of light revalidation.                                               |
| `backend/tests/handler/filesystem/test_roms_handler.py`             | HASH, snapshot, large-value, source-safety, and limiter regressions | VERIFIED | Covers matching/mismatching evidence, 5/80/120 GiB metadata, early cleanup, read-error cleanup, and immutable fixtures.                         |
| `backend/tests/endpoints/test_download_manifests.py`                | HTTP protocol and disclosure regressions                            | VERIFIED | Covers exact full/range bytes and headers, validators, invalid ranges, source change, foreign/hidden access, and large u64 bounds.              |

### Key Link Verification

| From            | To                         | Via                                                                    | Status | Details                                                                                                                                        |
| --------------- | -------------------------- | ---------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Transfer route  | Owner-scoped lookup        | Manifest ID, `request.user.id`, public member UUID                     | WIRED  | `get_transfer_manifest_member` is invoked before visibility, headers, filesystem verification, or bytes.                                       |
| Transfer lookup | Phase-14 durable topology  | ORM joins through selected component, manifest, ROM, and source member | WIRED  | No filename, internal ID, client path, or source path participates in lookup.                                                                  |
| Verified lease  | Phase-14 snapshot contract | Fresh HASH and `_download_manifest_snapshot`                           | WIRED  | Snapshot is recomputed from persisted opaque ID and trusted stored topology before lease creation.                                             |
| Transfer route  | Lease iterator             | `StreamingResponse(_lease_chunks(...))` plus background cleanup        | WIRED  | The response uses the verified descriptor-backed iterator, while close is idempotent across iterator finally and Starlette background cleanup. |

### Data-Flow Trace

| Artifact        | Data                                | Source                                             | Produces Real Data | Status  |
| --------------- | ----------------------------------- | -------------------------------------------------- | ------------------ | ------- |
| Transfer lookup | Authorized persisted member         | Owner-scoped SQLAlchemy query                      | Yes                | FLOWING |
| Verified lease  | Size, SHA-256, snapshot, descriptor | Trusted HASH capability and fresh `fstat` evidence | Yes                | FLOWING |
| HTTP response   | Body and range headers              | Verified lease plus validated request headers      | Yes                | FLOWING |

### Behavioral Spot-Checks

| Behavior                                                                                                                                   | Command                                                                                                                                                                                                                | Result                                                                                                                                                                                       | Status |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Owner/member lookup, fresh snapshot verification, direct bytes, range protocol, validators, lifecycle masking, u64 accounting, and cleanup | `cd backend && uv run pytest tests/handler/database/test_download_manifests_handler.py tests/handler/filesystem/test_roms_handler.py tests/endpoints/test_download_manifests.py -k 'transfer or download_manifest' -q` | 43 passed, 80 deselected in 11.86s. Only pre-existing Alembic/HTTP deprecation and pytest-cache permission warnings.                                                                         | PASS   |
| Planned artifacts and key links                                                                                                            | `gsd-sdk query verify.artifacts` and `verify.key-links` for all three Phase-15 plans                                                                                                                                   | 7/7 artifacts passed; 5/5 declared links verified.                                                                                                                                           | PASS   |
| Phase diff whitespace integrity                                                                                                            | `git diff --check 846861428..HEAD`                                                                                                                                                                                     | No output, exit 0.                                                                                                                                                                           | PASS   |
| Async source-HASH review regression                                                                                                        | Same focused command after `45080ee72` and review fix `98dbbc386`                                                                                                                                                      | 44 passed, 80 deselected in 11.65s. The new regression blocks `source.hash()` and proves an independent coroutine still runs promptly, while the lease and limiter are cleaned up afterward. | PASS   |

### Review Follow-up

The review follow-up split the blocking descriptor HASH work into
`_open_verified_download_manifest_member_source` and executes it through
`asyncio.to_thread`, while retaining the transfer slot from before verification
through stream cleanup. Cancellation waits for the shielded worker, closes any
returned descriptor, and releases the slot. The targeted regression and the
combined focused suite both pass. Code review of this change found no remaining
Phase-15 defect.

The verified snapshot boundary is deliberately the fresh, pre-transfer
full-HASH check specified for Phase 15. A stronger whole-transfer source-version
guarantee would require later source-snapshot architecture, not a missing
Phase-15 server-contract behavior; it is therefore not a gap in this phase.

### Probe Execution

No Phase-15 probe is declared and the repository has no applicable `scripts/*/tests/probe-*.sh` probe. SKIPPED.

### Requirements Coverage

| Requirement | Source Plans        | Description                                                                    | Status    | Evidence                                                                                                                  |
| ----------- | ------------------- | ------------------------------------------------------------------------------ | --------- | ------------------------------------------------------------------------------------------------------------------------- |
| XFER-01     | 15-01, 15-02, 15-03 | Direct source-file transfer without whole-game ZIP, part ZIP, or extraction    | SATISFIED | Opaque one-member descriptor stream, no archive route/path, and original-bytes endpoint regression.                       |
| XFER-02     | 15-03               | Authenticated exact-offset HTTP Range resume                                   | SATISFIED | Unconditional `ROMS_READ`, owner/visibility checks, strict one-range parser, 206 response and exact metadata regressions. |
| XFER-03     | 15-01, 15-02, 15-03 | Snapshot-bound continuation that safely fails after source or manifest changes | SATISFIED | Exact quoted validator precondition, fresh HASH/snapshot comparison, bounded `source_changed` 412 with no lease/body.     |
| XFER-04     | 15-02, 15-03        | Correct above-4-GiB accounting and bounded concurrency                         | SATISFIED | Synthetic 5/80/120 GiB regressions and transfer limiter held through stream cleanup.                                      |

### Anti-Patterns Found

No `TBD`, `FIXME`, `XXX`, placeholder implementation, hardcoded empty delivery result, auth bypass, path-bearing route input, ZIP invocation, or source-mutation operation was found in the Phase-15 code paths.

`backend/handler/filesystem/roms_handler.py` contains pre-existing archive support elsewhere in the general ROM handler. The new verified-transfer method does not call that code, and the transfer endpoint has no ZIP/archive imports or archive control flow.

### Human Verification Required

None. This phase is a deterministic backend protocol boundary. The later desktop client and live NAS behavior are explicitly Phase 16 and Phase 17 work, not prerequisites for verifying this server contract.

### Gaps Summary

No blocking gaps found. The actual route is wired to owner-scoped persisted identity, current visibility, lifecycle checks, strict snapshot and range preconditions, fresh descriptor-backed verification, and bounded cleanup. The targeted test suite independently passed the protocol's expected direct-transfer and failure behavior.

---

_Verified: 2026-09-16T22:00:00Z_
_Verifier: the agent (gsd-verifier)_
