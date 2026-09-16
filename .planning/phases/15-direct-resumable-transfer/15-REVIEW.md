---
phase: 15-direct-resumable-transfer
reviewed: 2026-09-16T21:27:55Z
depth: deep
files_reviewed: 7
files_reviewed_list:
  - backend/config/__init__.py
  - backend/handler/database/download_manifests_handler.py
  - backend/handler/filesystem/roms_handler.py
  - backend/endpoints/download_manifests.py
  - backend/tests/handler/database/test_download_manifests_handler.py
  - backend/tests/handler/filesystem/test_roms_handler.py
  - backend/tests/endpoints/test_download_manifests.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 15: Code Review Report

**Reviewed:** 2026-09-16T21:27:55Z
**Depth:** deep
**Files Reviewed:** 7
**Status:** clean

## Summary

The owner-scoped lookup, visibility mask, opaque member identifier, strict single-range parser, and lease cleanup wiring were traced across the route, database handler, filesystem handler, and tests. Re-review after `98dbbc386` confirms the hash runs in `asyncio.to_thread` while the process-local transfer slot remains held. The focused verified-member suite passes, including the new proof that an independent coroutine progresses while the source hash is deliberately blocked.

## Narrative Findings (AI reviewer)

## Re-review disposition

### BL-02: Resolved, HASH no longer blocks the async server worker

**Files:** `backend/handler/filesystem/roms_handler.py:414-486`, `backend/tests/handler/filesystem/test_roms_handler.py:2038-2088`

`_open_verified_download_manifest_member_source` now runs in `asyncio.to_thread`, and its descriptor/result is transferred back only after `await asyncio.shield(verification)`. The transfer limiter is acquired before scheduling and released on every non-lease path. The regression blocks `source.hash`, waits for a thread event, and proves an independent event-loop coroutine completes within 200 ms. The focused command `uv run pytest tests/handler/filesystem/test_roms_handler.py -k 'verified_download_manifest_member' -q` passed: 8 passed.

### BL-01: Not a Phase-15 blocker under the approved contract

**Files reviewed:** `backend/handler/filesystem/roms_handler.py:257-275`, `backend/handler/filesystem/roms_handler.py:414-486`; `docs/superpowers/specs/2026-09-15-cross-platform-pc-downloader-design.md`; `.planning/phases/15-direct-resumable-transfer/15-CONTEXT.md`

The implemented and approved Phase-15 contract is: fresh full HASH-capability verification immediately before opening a transfer, exact snapshot comparison, and `412 source_changed` with no bytes on a pre-transfer mismatch. The code does that, keeping the verified descriptor and rejecting failures before it becomes a lease.

The stronger property proposed in the initial review is different: protection against a non-cooperative external writer modifying the already-open inode after the pre-transfer hash has completed, including during a body stream. A descriptor prevents path replacement, not writes to that inode. HTTP cannot change an already-started 200/206 response into a 412. This repository's direct no-copy/read-only delivery design does not establish an immutable source snapshot or cross-platform writer lock for that time window, and the approved Phase-15 requirements do not require one.

**Architecture decision:** Phase 15 guarantees source-version validation before transfer starts. It assumes the source library is stable for the duration of a direct stream, while the Phase-16 client independently verifies final SHA-256 and refuses to complete mixed/corrupt bytes. If the product must defend against arbitrary writers during a stream, that must be a newly approved requirement: either enforce source-root immutability for all writers, use a filesystem-specific snapshot/lock facility, or change the delivery architecture. It is not silently treated as an unfulfilled Phase-15 promise.

---

_Reviewed: 2026-09-16T21:27:55Z, re-reviewed after `98dbbc386`_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
