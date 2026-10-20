---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
reviewed: 2026-10-19T11:13:00Z
depth: standard
scope: "34-15 interim ROM media review, not full Phase 34"
diff_base: f77c723c4
source_revision: 4a05a1b62
summary_revision: de4f755c0
files_reviewed: 17
files_reviewed_list:
  - backend/handler/database/scan_write_fence.py
  - backend/decorators/database.py
  - backend/tests/handler/test_scan_write_fence.py
  - backend/handler/filesystem/scan_media_publication.py
  - backend/handler/filesystem/scan_media_recovery.py
  - backend/handler/filesystem/resources_handler.py
  - backend/handler/filesystem/storage_access.py
  - backend/handler/database/roms_handler.py
  - backend/tasks/scheduled/owned_media_cleanup.py
  - backend/tests/handler/test_scan_media_publication.py
  - backend/handler/metadata/rom_media.py
  - backend/handler/metadata/steam_owned_media.py
  - backend/handler/scan_handler.py
  - backend/utils/audio_tags.py
  - backend/endpoints/sockets/scan.py
  - backend/tools/phase34_fixtures.py
  - backend/tools/tests/test_phase34_runner.py
findings:
  critical: 8
  warning: 1
  info: 0
  total: 9
status: issues_found
---

# Phase 34: Task 15 Interim Code Review

Reviewed at standard depth, against Task 15 GREEN source revision `4a05a1b62`, with `f77c723c4` as the pre-15 comparison base and summary `de4f755c0`. All finding line numbers refer to that pinned source.

## Scope and evidence limits

This report covers only the seventeen explicitly supplied Task 15 files and necessary callers, models and storage/session dependencies. It is not whole-phase approval. The review followed actual publication, association, cancellation and recovery calls and inspected the added tests. Findings below identify changed behavior or newly introduced functions, rather than historical monolith issues.

All project inspection and this artifact write used SSH `team4s-linux`, inside `/home/d1sk/pc-game-download-portal`. The pre-write checks confirmed Linux, that exact Git root, branch `codex/phase-32-pgdp-naming`, origin `https://github.com/D1skanime/pc-game-download-portal.git`, and matching RomM planning identity. The report did not already exist. Explicit paths were validated as relative project paths, present at the pinned revision and not ignored. No additional project skill directories existed under `.codex/skills/` or `.agents/skills/`; canonical CLAUDE instructions and its backend guide were read.

The code-review configuration key is absent, so review defaults to enabled. Standard depth was explicitly requested; the optional structural pre-pass is disabled. No nested agents, implementation changes, tests, application/runtime commands, database access, deployment, commits, STATE edits or ROADMAP edits were performed. The summary's 285 backend and 23 host passes are prior executor evidence, not tests rerun or independently certified by this review.

03 worker/dispatch binding and NON-ROM RA cache/Gamelist/Pegasus fencing remain intentional downstream work. 08 nginx exclusions and actual HTTP privacy remain open gates. Their absence is not counted below. The four inherited static findings named in the Task 15 summary are excluded.

## Summary

Eight BLOCKER findings concern failed refresh data loss, stale-reference resurrection, recovery starvation and permanent limits, valid inventory rejection, optional network failures, compressed-body integrity, and PostgreSQL compatibility. One WARNING concerns malformed manifest isolation. The existing small, successful inventories and direct-manifest tests do not cover these boundaries.

## Critical Issues

### CR-01: Failed non-scan HTTP refresh truncates and removes existing good media

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_publication.py:420-442`
**Cross-links:** `backend/handler/filesystem/base_handler.py:435-466`; `backend/handler/filesystem/resources_handler.py:405-420`; `backend/endpoints/roms/pc_metadata.py:739-758`.

**Issue:** The new non-scan branch opens `write_file_streamed(directory, filename)` before advancing `chunks()`. That helper immediately opens the final file with `wb`. HTTP status and MIME validation occur only when the generator advances at lines 350-357. A 503 or rejected content type therefore arrives after an existing legacy cover, manual or screenshot has already been truncated; the exception handler then unlinks that final path. For example, an explicit PC cover selection with existing `cover/small.png` and `cover/big.png` and a provider 503 destroys both files. `get_cover` can still return the previously captured path as its fallback, leaving the catalog pointing at missing bytes. Before this change, a non-200 response or rejected MIME returned before opening the destination.

**Fix:** Stage non-scan replacements in a separate owned temporary file and validate the response/content before replacing the final object. On failure, abort only that staged object and return the existing authoritative path. Never call partial-file deletion on a pre-existing final path. Add actual-file regressions for overwrite plus 503, invalid MIME and a mid-stream failure, including the endpoint caller's returned paths.

### CR-02: COMPLETE preservation can resurrect a cover already retired and deleted

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_publication.py:487-488`
**Cross-links:** `backend/handler/scan_handler.py:722-729,1419-1421,1500-1502`; `backend/handler/database/roms_handler.py:3841-3859`; `backend/handler/filesystem/scan_media_recovery.py:238-256`.

**Issue:** Reference preservation always copies primary paths from the detached, original `rom`. Earlier in the same scan, `sync_rom_components` can intentionally remove a reviewed local cover when its source member disappears or changes. The new batch commits that detachment and its cleanup intent before provider lookup. While a provider lookup is suspended, the scheduler can legitimately delete the now-unreferenced old cover. The new final preservation step then copies the original cover paths back onto the scanned object, and `_identify_rom` merges them into SQL. A COMPLETE scan can thus restore references to already deleted bytes. Without the cleanup interleaving, it still undoes the intentional source-change invalidation. This is introduced by the unconditional preservation at the final COMPLETE result, not a request to fix unrelated historical scanner behavior.

**Fix:** Carry the reconciled primary-reference state forward after component reconciliation, and preserve from that current state rather than the pre-reconciliation detached object. Coordinate the final reference merge with the same parent lock and never reattach an outbox-retired path without fresh existence/authority checks. Add a real-SQL barrier test: selected local cover, changed/removed source member, completed cleanup during provider lookup, then final COMPLETE association.

### CR-03: A normal scan can permanently disable recovery and all cleanup intents

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_recovery.py:192-201`
**Cross-links:** same file `:36-45,179-188`; `backend/tasks/scheduled/owned_media_cleanup.py:31-37`.

**Issue:** Every hierarchy listing has a hard 512-child limit, and the operation/attempt listings occur outside the per-batch exception handler. Successful publication does not retire its manifest; live-attempt recovery skips it. Consequently, 513 valid batches under one attempt make `_children(parent)` raise before any batch can be reclaimed. This requires only about 257 ROMs when file synchronization and primary-resource publication each create a batch, and fewer when provider/special media creates additional batches. Ending the attempt does not help because the listing still fails. In addition, successful recovery removes only the batch directory, leaving attempt and operation directories forever; 513 distinct operation directories eventually cause the same permanent failure at the root. The task calls receipt recovery before outbox cleanup, so the exception also prevents all ordinary cleanup intents from running.

**Fix:** Enumerate these unbounded hierarchies in bounded pages with progress across pages, rather than rejecting the entire directory at 513 entries. Remove verified empty ancestor directories safely, and isolate recovery enumeration failures from the independent cleanup-intent pass. Keep per-manifest size/output bounds. Add cases with 513 batches in one completed attempt and 513 historical operation directories.

### CR-04: Thirty-two retained receipts can starve every later recoverable batch forever

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_recovery.py:201-219`.

**Issue:** Each invocation starts directory enumeration again and increments `processed` for every batch, including a live batch returning false or an ambiguous manifest retained after an exception. At 32 it returns without a cursor or rotation. Put 32 retained malformed receipts first in a stable directory enumeration and a valid stopped-attempt receipt after them: every scheduled run revisits the same 32 and never reaches the valid orphan. This is indefinite failure to reconcile, not merely slow traversal. The direct `reconcile_manifest(old.manifest_directory)` call in `test_scan_media_publication.py:821-823` bypasses the scheduler traversal and cannot establish eventual sweep progress.

**Fix:** Preserve a bounded traversal cursor or rotate fairly between invocations, so retained/live evidence consumes bounded work but cannot permanently exclude later batches. Do not delete ambiguous receipts to obtain progress. Exercise repeated calls through the actual scheduler with retained/live entries before a valid later orphan, and assert eventual exact cleanup.

### CR-05: Valid badge and Steam inventories exceed the publication batch contract

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/endpoints/sockets/scan.py:915-937`
**Cross-links:** `backend/handler/filesystem/scan_media_publication.py:29,153-155`; `backend/handler/metadata/steam_owned_media.py:114-162`; `backend/handler/metadata/rom_media.py:22,84-91`.

**Issue:** The entire achievement inventory is staged in one batch, but a batch permits only 128 output files. Each achievement normally downloads both normal and locked badges. A valid set of 65 achievements fails on file 129, aborts all previously staged files, and reaches the warning handler without publishing any of the new achievements/badges. The new code also places an entire Steam inventory into one 128-output batch even though discovery accepts up to 500 images per role; a valid forced refresh with 129 downloads returns false before association. Neither is an invalid input according to the existing provider contract. Current tests use one achievement or very small Steam inventories.

**Fix:** Prepare multiple bounded manifests under one coherent inventory transaction and publish/associate them under the existing single fence, or introduce a bounded inventory preparation abstraction that covers the accepted cardinalities. Preserve atomic Steam inventory replacement and old references; do not truncate the provider response or publish partial achievement metadata with missing paths. Test at least 65 two-badge achievements and 129 forced Steam outputs, including cancellation and failure.

### CR-06: Optional media transport errors now escape and fail the scan

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_publication.py:380-419`
**Cross-links:** `backend/endpoints/sockets/scan.py:827-838,903-907,938-941,331-343`; `backend/handler/filesystem/resources_handler.py:366-373,615-625`.

**Issue:** The new scan branch rethrows every download exception. Its primary, special-media and badge callers catch only `ValueError` and `OSError`. HTTPX `ConnectError`, `ReadTimeout` and `ReadError` are transport exceptions, not either of those types. A routine provider disconnect therefore escapes optional-media handling and fails the enclosing scan instead of retaining old media and indexing other games. The DLC import loop also narrows its former generic catch without covering HTTPX transport failures. Legacy cover/manual/badge download methods previously caught these failures locally. This conflicts with context decision D-08, which requires provider failures to leave other readable games indexable.

**Fix:** Treat transport/decoding failures before publication as optional media failures at the new shared boundary or its callers, preserving prior references and a bounded warning. Continue to propagate `ScanWriteRejected`, SQL errors and indeterminate publication/commit outcomes. Use real local HTTPX stream failures through the actual scanner and DLC entry, not only a substituted downloader that raises ValueError.

### CR-07: Gzip streams can be marked complete while truncated or mixed with raw bytes

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_publication.py:360-378`
**Cross-links:** same file `:386-416`; `backend/handler/filesystem/resources_handler.py:615-625,693-703`.

**Issue:** The incremental decoder never checks `decoder.eof` when the HTTP body ends. An HTTP 200 response whose declared body is a truncated gzip member can end normally, yield only a prefix of a manual/video, and still reach `finish` and catalog association. Hashing that prefix proves what was written, not that the compressed response completed. On a later zlib error, the fallback switches to raw compressed bytes after already yielding decoded bytes, potentially creating a mixed, corrupt document. PDFs and videos do not undergo the image validation that might catch this. The protocol promises never to associate partial output.

**Fix:** Use a streaming decoder that enforces member completion and trailer integrity; reject incomplete/corrupt encoding before finishing a prepared output. Do not fall back to raw bytes after emitting decoded data. If supporting mislabeled uncompressed responses is required, decide that before emitting output and retain a separate validation path. Add truncated-member and later-chunk corruption cases for a non-image resource, verifying old references survive and no new association commits.

### CR-08: The new reference lock fails on PostgreSQL because it locks eager outer joins

**Classification:** BLOCKER
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/database/roms_handler.py:1065-1067`
**Cross-links:** `backend/models/rom.py:1029,1080-1082`; `backend/handler/filesystem/scan_media_publication.py:124-126`.

**Issue:** `select(Rom).with_for_update()` includes the model's default joined relationships to platform and the metadata view. Those relationships use LEFT OUTER JOINs, and the unrestricted PostgreSQL FOR UPDATE applies to their nullable sides. PostgreSQL rejects that query with `FOR UPDATE cannot be applied to the nullable side of an outer join`. The new reference helper is called unconditionally while constructing every media batch, so ordinary primary-media/file-sync scans and recovery now encounter this failure on a supported database, even when they did not previously enter the older provider-specific locking helpers. Prior MariaDB test evidence does not establish this PostgreSQL path.

**Fix:** Lock the parent using a table/column-only query, then read the needed reference columns under that lock, or suppress joined eager loading and explicitly restrict the lock to Rom where supported. Avoid locking the derived metadata view. Add an actual PostgreSQL batch/publication and cleanup regression when tests are authorized; schema-parity checks alone do not exercise this query.

## Warnings

### WR-01: Malformed manifest identity types escape per-receipt isolation

**Classification:** WARNING
**File:** `/home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_publication.py:249-257`
**Cross-links:** `backend/handler/filesystem/scan_media_recovery.py:135,206-218`; `backend/tasks/scheduled/owned_media_cleanup.py:33-37`.

**Issue:** The validator passes JSON identity values into UUID before checking their types. A syntactically valid receipt with `operation: 7` causes UUID's string normalization to raise AttributeError. The recovery loop catches ValueError/KeyError/TypeError and storage errors, but not AttributeError. This malformed receipt therefore aborts the scheduler before later receipts and cleanup intents, rather than being retained with the documented bounded diagnostic. Existing unsafe-manifest tests cover path mutations, not malformed identity types.

**Fix:** Validate every schema field's primitive/container type before UUID, regex and path processing and normalize validation failures into a dedicated caught error. Keep recovery failures isolated from the outbox pass. Add malformed identity types, wrong output element types and deeply nested JSON to the receipt parser's negative cases.

## Coverage and decomposition assessment

The tests inspect real SQL associations and real capability publication; the process-crash and lost-acknowledgement tests exercise useful protocol boundaries. They do not establish correctness at the inventory/directory limits, rejected non-scan HTTP replacement, compressed-response integrity, component-invalidation/cleanup interleaving, malformed identity types, or PostgreSQL reference locking described above. These are proposed regression cases, not tests executed during this review.

The three new runtime modules measure 106, 475 and 231 nonblank/non-comment lines respectively. They fit CLAUDE's stated logical production-module target; they are not treated as exempt generated code. The handwritten publication test file is 1,492 physical lines and 1,332 nonblank/non-comment lines. Task 3's diff from Task 2 adds 1,210 lines and removes two. This confirms substantial test growth, rather than assuming the file is a small fixture.

CLAUDE scopes its hard production limits to runtime files and separately calls for decomposing large handwritten helpers when practical; it does not impose an explicit blanket 500-line cap on ordinary test modules. The approved plan explains the seventeen-file boundary and reuse of the existing test file, but does not establish that all of its family orchestration and process/recovery helpers are indivisible. Protocol/crash helpers and family/scanner orchestration are coherent potential extraction boundaries. File length alone is not reported as a bug or blanket test exemption; the concrete missing boundary coverage is attached to the corresponding findings.

---

_Reviewer: gsd-code-reviewer_
_Depth: standard_
_Scope: completed 34-15 ROM media only; interim review, not runtime proof or full Phase 34 acceptance._
