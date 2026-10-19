# Phase 34 Media Fix: Catalog Group 3 Checkpoint

Date: 2026-10-19. Assigned scope: corrective 34-15, CR-02, CR-05 and CR-08 only.
Baseline: 383b47af5. Original findings: unchanged 34-REVIEW.md.
Status: CHECKPOINT, 2 of 3 findings executor-verified. Group 3 is not complete.

## Result and blocker

CR-08 and CR-02 were reproduced and repaired with committed RED/GREEN proof.
Neither finding was rejected. CR-05 was reproduced and remains OPEN.

Final unfiltered regression: 424 tests, 421 passed, 3 failed, zero errors/skips,
121.956 seconds. This is not GREEN: 399 of the previous 401 cases passed and
22 of the 23 new cases passed. The original test assertions are unchanged.

The accepted 1,000-image Steam inventory (500 images per existing accepted role)
exhausts prepared-file descriptors: StorageResolutionError caused by OSError
errno 24, EMFILE. Each existing PreparedOwnedFile retains both a staging-file
descriptor and a parent-directory descriptor until publish/abort. Splitting
receipts fixes cardinality and byte payloads but does not bound those descriptors.

Further runtime changes stopped at this concrete capability boundary, as requested.
No CR-05 GREEN commit, replacement SUMMARY, shared requirement completion or phase
acceptance was created. Pending source and tests remain intact for continuation.

## Commits

All five task commits resolve on the canonical branch and used normal hooks.

| Scope | RED | GREEN |
| --- | --- | --- |
| CR-08 PostgreSQL parent/reference locks | 4dcdcc11f | 736836a80 |
| CR-02 COMPLETE reconciled references | 029ff8117 | 3e2404aa5 |
| CR-05 accepted output/prior-volume limits | 7ffdfbf1f | none, blocked |

The separate commit containing this additive checkpoint note is metadata only.
No tracked file was deleted. No production draft is committed as a verified fix.

## CR-08: Actual PostgreSQL proof

locked_scan_media_references now selects the parent table directly under FOR
UPDATE, avoiding default ORM platform and derived metadata-view outer joins.
Its existing component/reference-row locks and slot/operation ordering remain.

The existing guarded runner gained a backend --dialect option, selecting only
its already approved SQL_IMAGES. The default remains MariaDB. This is a bounded
Rule 3 runner extension, not another runner, connection authority or schema probe.

Actual PostgreSQL RED: two tests failed with the reported nullable outer-join
FOR UPDATE error. Actual GREEN: two tests passed, proving immutable publication,
catalog association, scheduler cleanup and a real concurrent parent-lock barrier.
The barrier proves cleanup waits and then protects a freshly associated file.
MariaDB compatibility plus the existing fence suite passed all 17 cases.

A later PostgreSQL run against the pending Group 3 tree passed four actual tests:
the two lock/publication/cleanup tests, actual scanner publication of 65 complete
two-badge achievements, and long-path multi-receipt publication plus scheduler
recovery. This is independent PostgreSQL runtime proof, not MariaDB/schema parity.

That isolated runtime uses the runner image's glibc environment. It does not
satisfy the production Alpine gate in the independent Group 2 review.

## CR-02: Current reconciled authority through final merge

The actual mapped scanner reads the immutable synthetic soundtracks directory.
A previously reviewed local cover references a prior changed or removed manifest
member. Real sync_rom_components invalidates the selection and creates cleanup
intents before provider lookup pauses.

The barrier verifies SQL detachment, deletion of the old local-media association,
and both cleanup-intent paths. In the cleanup ordering, the scheduler deletes
both selected cover files before provider lookup resumes. In the other ordering,
the old bytes remain but the intentionally invalidated references must stay absent.
The final COMPLETE result also publishes new pending special-media bytes while
retaining valid manuals/screenshots.

The first run reproduced restoration of the selected generation in both
no-cleanup cases. The new fixture was subsequently corrected to remove unrelated
legacy cover files seeded by the shared helper, so deterministic getter fallback
cannot obscure the selected-generation assertion.

After component reconciliation the scanner reloads current parent state.
preserve_current_scan_media reads authoritative references under the existing
parent lock. merge_scan_rom retains that lock through the final merge, including
the internal Steam merge paths. Pending provider artifacts remain pending until
their own publication. A separate real-SQL stale-session case preserves a newer
committed cover and the pending provider path.

Verified: 120 existing/new publication and transport tests, followed by all five
focused reconciliation tests. The final unfiltered run also passes all five.
Earlier combined attempts put the new tests before the original publication
suite and exposed its single-sweep recovery assumptions. Those unsuccessful
attempts are retained and are not presented as GREEN. No original assertion was
changed; the full regression retains the previous suite order and appends new cases.

## CR-05: Pending implementation and proof

Current uncommitted runtime work:

- ScanMediaInventory prepares multiple existing ScanMediaBatch instances and
  uses one checked transaction for final capability publication and one inventory
  association callback. Its output budget derives from the accepted provider
  candidate count or actual requested badge outputs. No new provider limit,
  output truncation, downloader, storage authority or lifecycle was introduced.
- Each receipt keeps MAX_OUTPUTS=128 and MAX_MANIFEST_BYTES=128 KiB. Preparation
  reserves space for completed digests, sizes and private names before accepting
  another output, rolling a receipt when its byte budget fills first.
- The extracted scan_media_manifest module remains the single parser/validator.
  Existing publication exports remain compatibility facades.
- Schema 2 records a count plus domain-length-prefixed SHA-256 fingerprint of all
  prior reference paths, avoiding repetition of an unbounded catalog list in
  every receipt. This fingerprint is diagnostic evidence, never deletion
  authority. Recovery still reads current SQL references while holding its locks.
- Schema 1 remains accepted. Exact output generation, private ownership, digest,
  primitive/container/depth and per-receipt bounds remain enforced.
- The 1,000-image fixture has valid prior paths whose serialized list exceeds
  128 KiB. Its failure is retained rather than hidden by lowering provider limits.

Passing targeted proof includes actual scanner 65 x 2 badges, forced 129 Steam
outputs, late stream failure, repository cancellation while request 129 is paused,
and SQL failure after real association writes for both inventories. Old inventory
references and bytes remain intact. Aborted private bytes and published rollback
orphans are removed by the existing exact recovery scheduler after stopping.
Cancellation completes through another SQL connection without waiting on streaming.

Schema 1 exact recovery, five malformed schema 2 fingerprints and long-path
byte-budget rollover also pass. The long-path fixture was corrected from eight
to ten directory segments so 150 outputs require at least three receipts before
128 outputs per receipt. No bound or assertion was weakened.

Two existing fatal controls fail in the full run:

- test_actual_scanner_fatal_publication_faults_propagate[sql-badge]
- test_actual_scanner_fatal_publication_faults_propagate[indeterminate-badge]

Their injected callback wraps ScanMediaBatch.publish_and_associate. The pending
inventory override bypasses that existing seam. These failures are not evidence
that real injected SQL errors are swallowed: the new actual inventory association
rollback cases propagate them. They are nevertheless unresolved compatibility/
verification failures. Preserve the original assertions and restore one shared
publication seam in the continuation.

The remaining new failure is:

- test_complete_steam_inventory_replaces_large_prior_atomically[1000]

Its retained diagnostic records errno 24. The 129-output and long-path cases do
not establish acceptance of the full existing provider contract.

## Bounded continuation required

Resolve the prepared-capability descriptor budget within the existing authority.
A concrete candidate is to seal prepared output after streaming, release bounded
descriptor resources, and reacquire only exact capability-owned staging objects
with parent/inode validation before the existing publication operation. Retain
outside-lock streaming, hashing and validation, no-follow/no-clobber behavior,
unknown-publication handling and one atomic catalog inventory association.

This extension has not been implemented or approved as a new capability contract.
Do not substitute a higher process ulimit, larger hardcoded output count, partial
publication or truncated accepted inventories. Keep any extension coherent and
bounded, with actual capability/SQL/filesystem regressions under the existing runner.

Then resolve the two unchanged fatal controls through the shared publication seam,
rerun all 424 cases without exclusions and repeat actual PostgreSQL scan/cleanup
proof. Only after actual GREEN and independent review may CR-05 and Group 3 close.

## Evidence

Each listed Linux root contains evidence/commands.json, redacted logs,
backend.xml, source-before.json, source-after.json and cleanup.json.

| Stage | Actual result | Linux evidence root |
| --- | --- | --- |
| CR-08 RED | 2 failed | /tmp/pgdp34-61cbc2b3f9074db5b5aed4cede5ee655-lcbnyhb6 |
| CR-08 PostgreSQL GREEN | 2 passed | /tmp/pgdp34-fa8999d58cb946898e3370aa562d9bf4-u431rlns |
| CR-08 MariaDB/fence GREEN | 17 passed | /tmp/pgdp34-2d30015b464d4952b2b69e49d40312f9-0k5miib_ |
| CR-02 original RED | 2 failed, 2 passed | /tmp/pgdp34-81c198c78f1243958c222723a84dff42-0cs3ej1m |
| CR-02 combined GREEN | 120 passed | /tmp/pgdp34-c5dfd7820f6e400ea6c98b6678bef091-su341uv0 |
| CR-02 focused GREEN | 5 passed | /tmp/pgdp34-bd34d09ac77845b3b1be9603c83ccac3-qnb0ta4l |
| CR-05 original RED | 3 failed | /tmp/pgdp34-9c472d70e77948a88e3783164652cd07-xawx0txe |
| Initial inventory implementation | 2 passed, 1 failed | /tmp/pgdp34-8deb7cd4d4784aedbfbb72c3bcc2285b-398v3bqa |
| Expanded faults/schema run | 14 passed, 2 failed | /tmp/pgdp34-f6f1db578ed445eb93dfab3edb4667fd-9sjhj0_n |
| EMFILE plus corrected long paths | 1 passed, 1 failed, 8 deselected | /tmp/pgdp34-67c3981d87944370acf2f9a54d527e21-5h46yn5b |
| Actual PostgreSQL pending-tree scan/cleanup | 4 passed | /tmp/pgdp34-876d8b94b22d40ec8ab53712de140b6b-33oq1c6t |
| Final unfiltered regression | 421 passed, 3 failed, no errors/skips | /tmp/pgdp34-b4e04affd9b94827acc6d80262fde078-7am9c06p |

Additional unsuccessful intermediate roots:
pgdp34-975521f870014c1e97e78679a44c881b-gcb89h6o (pre-fix rerun after rejected
atomic patch, 117 passed/3 failed) and
pgdp34-9dc0318bfc0d4f26b2d822ef8570bd08-eccgy1q5 (fixture fallback and suite-order
issues, 115 passed/5 failed). Failed patch attempts applied no partial edits.
Neither root is counted as GREEN. Infrastructure/fixture errors are not proof.

All commands use this exact repository-root prefix:

    PYTHONDONTWRITEBYTECODE=1 python3 backend/tools/phase34.py backend

PostgreSQL additionally uses --dialect postgresql before the test paths.
Focused selectors and full exact paths/options are retained in commands.json.
The final full command has no -k exclusion and contains the original sixteen
media-suite files plus all five new test modules.

## Cleanup, static and preservation

All inspected completed receipts report clean=true, source_unchanged=true and
empty remaining containers/volumes/networks. Final exact cleanup removed
containers 511c587ee0f8, c6f7cb65e295 and f593eb780940, the final run's two labelled
owned/node_modules volumes, and network 5e3decf64265. No global prune was used.
Final run source-before/source-after hashes are both
58a2f3dd5fbacc3034a72d0c07c4c53d3941606b2fcb466bb1e52f38b42c89b8.
PostgreSQL four-case source hashes are both
9cdb15776e31e1cebac21022900df75107f50d292a27884d1734c13806087b0f.

Scoped formatting and Trunk check on all fourteen changed source/test files
pass with no new diagnostics. Eight inherited issues remain; they were not fixed
or claimed absent. Final static output is evidence/group3-static.log. No API
route/response schema changed. No frontend generation/typecheck, host guard-suite,
production image, browser or whole-phase acceptance claim is made.

Logical nonblank/noncomment counts: publication 351, manifest 159, inventory 35;
new locking test 81, reconciliation test 195, inventory helper 83, inventory test
142, failure tests 168 and receipt tests 80. No original monolithic test grew.
The new runtime modules and handwritten test/helpers remain below 500.

Repeated preflight confirmed Linux over ssh team4s-linux, canonical Git root
/home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming, exact approved
origin and RomM planning identity. workflow.use_worktrees=false is unchanged.
Only canonical Linux git apply via SSH stdin performed source/artifact edits.
No Windows project copy/write, branch/worktree, nested agent, stash/reset,
broad staging, hook bypass, live DB/dev.env, live scan, restart or deployment occurred.

Before every test and at handoff pgdp-dev was exited with Running=false.
The separate future dev-DB rebuild permission was not exercised.
Host Media controls were only statted. Their preserved size/mtime/ctime/inode are
lock (0, 1792411826, 1792411826, 294876) and
cursor (2, 1792413626, 1792413626, 294888). Their contents were not read or written.

A process-argv diagnostic mistakenly printed short-lived disposable runner
credentials. These were not real application credentials. Confirmed teardown
removed that isolated SQL/Redis/network and invalidated the credentials. Do not
repeat process argv/environment diagnostics; the retained runner evidence remains
redacted. No secret value is included in this note.

Dirty STATE, Phase 33 UAT/VALIDATION, setup.py, Compose files, ROADMAP, REQUIREMENTS,
original REVIEW and original 15 SUMMARY retain their exact initial SHA-256 values.
Untracked backend/pgdp_test/, pgdp_test/ and Media are preserved.
The parallel Group 2 review remains untouched and unstaged; its SHA-256 is
ae02e430c5ffe700d1a3892560c12c6d758c19241576d8c1cf9c606c59dc4bb7.

## Pending files and remaining gates

Preserve these uncommitted CR-05 runtime files:

- backend/endpoints/sockets/scan.py
- backend/handler/filesystem/scan_media_publication.py
- backend/handler/filesystem/scan_media_inventory.py (new)
- backend/handler/filesystem/scan_media_manifest.py (new)
- backend/handler/metadata/steam_owned_media.py

Preserve these pending test changes:

- backend/tests/handler/test_media_inventory.py
- backend/tests/handler/test_media_inventory_failures.py (new)
- backend/tests/handler/test_media_inventory_receipts.py (new)

Their exact current hashes are retained in evidence/group3-preservation.log.
No source changed after the final regression snapshot.

Independent Group 3 review and cross-group integration remain required. The
Group 2 Alpine libc blocker CR09 and PID-reuse cursor warning WR02 belong to the
parent's serialized follow-up and were not repaired or staged here.
The original review is not declared clean. Plan 03 worker/non-ROM fencing,
plan 08 nginx/HTTP/production/browser proof, the inherited RQ/Vue failures and
later Phase 33 fresh-install acceptance remain open. Five summaries are not
whole-phase acceptance. Parent still owns STATE, ROADMAP and requirements.
