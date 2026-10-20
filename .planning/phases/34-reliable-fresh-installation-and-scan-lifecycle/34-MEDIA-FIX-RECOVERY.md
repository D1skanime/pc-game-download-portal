# Phase 34 Media Fix: Recovery Group 2

Date: 2026-10-19. Assigned scope: corrective 34-15, CR-03, CR-04 and WR-01 only.
Original findings: 34-REVIEW.md at da362317b, reviewing 4a05a1b62.
Resume baseline: c4200ddc9. Verified implementation: 152519529.

## Result and open gates

Executor verification is complete for CR-03, CR-04 and WR-01. The final combined
guarded run passed 401 tests, with zero failures, errors or skips. This includes
the unchanged original 285 media tests, 77 Group 1 tests and 39 Group 2 cases.
The fresh focused recovery run passed all 39 cases.

Independent Group 2 review remains OPEN. CR-02, CR-05 and CR-08 belong to future
Group 3 and remain OPEN. The original review is not rewritten or declared clean.
Group 1's independent clean verdict remains limited to CR-01/06/07.

This additive note does not replace 34-15-SUMMARY.md, redo plan 15, complete another
plan, or close Phase 34 or Phase 33. Five existing summaries remain five.
Parent-owned STATE, ROADMAP and requirement completion were not updated.

## Canonical environment and containment

Preflight repeatedly confirmed Linux over ssh team4s-linux, canonical Git root
/home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming, origin
https://github.com/D1skanime/pc-game-download-portal.git and matching RomM planning
identity. workflow.use_worktrees=false was honored. No branch switch, worktree,
nested agent, push, restart or deployment occurred.

The prior source-bind exposure is preserved in
34-MEDIA-RECOVERY-SAFETY-CHECKPOINT.md. It cannot be described as an isolated
historical execution: the dev app had reloaded pending recovery code and created
two host Media control files. Parent-approved containment is recorded in
34-MEDIA-RECOVERY-RESUME.md. At this resume and before every test, pgdp-dev was
verified exited with running=false. It stayed stopped through handoff.

No host pytest, storage-initializer import, live SQL, dev.env, database reset,
live scan or host Media write was used during this resume. The approved dev
database rebuild remains reserved for later fresh-install UAT. pgdp-db-dev and
pgdp-valkey-dev remain running and were not reset. Other projects were untouched.

Only the existing guarded Phase 34 backend runner executed tests. It provisioned
its own labelled SQL/Redis/network/owned volumes and read-only synthetic Games.
All edits used unified git apply on Linux through SSH stdin; no project copies or
writes occurred on Windows. Repository backend-development and pre-pr-verification
guidance informed capability reuse, session ownership and scoped verification.

## WR-01: Bounded malformed-evidence validation

Retained the existing RED/GREEN commits 4089bb52c / d6cfb9476. The implementation
was inspected and regression-tested, not reimplemented.

Manifest parsing bounds input bytes and nesting before JSON decoding, validates
primitive and container types before UUID/path operations, and normalizes invalid
evidence to ManifestValidationError. Wrong identity types, output elements,
path/digest/container fields and deeply nested JSON remain retained with safe
type-only diagnostics. A real malformed receipt cannot prevent an independent
exact cleanup intent from completing.

All 18 existing validation cases passed in both fresh final runs.

## CR-03: Bounded hierarchy traversal and independent outbox cleanup

Operation, attempt and batch hierarchies no longer use the old 512-child rejecting
list. A private recovery traversal uses a bounded Linux directory-cookie page
through the existing descriptor boundary. It never materializes the hierarchy,
raises its cardinality ceiling, or scans a whole directory merely to choose the
next sorted page.

Each call performs at most 512 traversal steps and processes at most 32 receipts.
A directory read uses a 4096-byte buffer. Receipt directory enumeration remains
bounded at 512 children, manifest bytes retain MAX_MANIFEST_BYTES, and output
count retains MAX_OUTPUTS. The bounded per-receipt contract is separate from the
unbounded historical hierarchy.

Empty attempt and operation ancestors are removed only with descriptor-relative
rmdir under the existing slot-then-operation lock order. A currently leased
operation protects its ancestors. Concurrent new-first and prune-first cases use
real repository transitions/CAS, separate execution threads, propagated worker
results, deadlines and actual capability I/O. If pruning wins first, the new
attempt recreates its own hierarchy. Nonempty and missing ancestors are harmless;
unexpected storage and SQL failures still propagate.

The existing cleanup task runs its independent outbox pass in finally, even if
recovery raises an I/O or SQL error. The error is not silently converted to
success. The tests demonstrate real exact file deletion while the original
recovery error remains observable.

Final real scheduler tests recover 513 batches in one completed attempt and 513
historical operation hierarchies, including empty ancestors, through bounded
repeat calls. No database authority, reference lock or attempt predicate is mocked.

## CR-04: Durable fair progress, ownership and cursor semantics

The advisory cursor and its lock live only under RESOURCES/.scan-media-staging:

- .recovery.lock is opened with the existing owned capability and no-follow path
  traversal, and protected by nonblocking flock.
- .recovery-cursor.json is bounded to 4096 bytes and at most three strict frames.
  Each frame records a reserved generated path, device, inode and opaque cookie.
  Frames must form one exact root/operation/attempt chain.
- A different directory device/inode resets that frame's cookie. End of traversal
  persists an empty stack; the next invocation starts another sweep.
- Retained or live receipts advance the cursor. They consume bounded work without
  indefinitely excluding later recoverable receipts.
- Cursor replacement reuses OwnedReplace.binary_file: complete temporary bytes
  are flushed/fsynced before atomic replacement, then the reserved parent is
  fsynced. No new writer or storage authority is introduced.
- The traversal lock remains held through cursor save. A concurrent recovery walk
  returns busy and cannot overwrite progress. Initialization and save failures
  release the descriptor lock.
- Process death before save leaves the prior checkpoint and replays a bounded
  page. File deletion remains idempotent. Atomic replacement failure retains the
  previous cursor bytes. Cursor progress never grants deletion authority.
- Invalid advisory cursor JSON resets traversal only. Malformed receipts remain
  unchanged; missing, inaccessible and symlinked directories are isolated.
  A disappearing or unreadable individual child now preserves its parent's
  cursor so later siblings are still visited.

Deletion continues to require a valid bounded receipt, exact generated ownership,
existing attempt checks, SQL catalog reference locks and digest/inode checks.
SQL/fence/unknown-commit failures are not broadened into optional-error catches.
No second lifecycle, resolver, scanner, client, lease authority or queue was added.

Private cleanup now uses the exact recorded private path instead of enumerating
the final media directory, which can itself exceed 512 entries. A receipt with an
unrecorded private path is conservatively retained with a safe diagnostic. This
keeps ambiguous crash evidence instead of deleting possible foreign temporaries.
Existing capability replacement temporaries remain within the reserved namespace;
they are not treated as receipt deletion authority.

Actual tests retain the first 32 malformed receipts byte-for-byte while reaching
a later stopped orphan. Separate repeated scheduler calls traverse a live page
before reclaiming an old-attempt orphan and preserve all live files. Symlink,
listing-failure, cursor read/save-failure, concurrent-walk and process-exit tests
use real owned storage. The original 1,492-line publication test was not enlarged.

Linux directory cookies are treated as opaque values, not numeric byte positions.
The narrow helper supports the verified 64-bit Linux runtime and fails closed
elsewhere. API references:
[Linux getdents64](https://man7.org/linux/man-pages/man2/getdents.2.html),
[readdir cookies](https://man7.org/linux/man-pages/man3/readdir.3.html) and
[flock](https://man7.org/linux/man-pages/man2/flock.2.html).
This is an advisory local-filesystem traversal contract, not cross-filesystem or
Windows cursor portability.

## Commit trace

Six Group 2 source/test commits, plus this separate additive evidence commit.
The first four predate this resume and were preserved. This resume adds one RED
commit, one coherent GREEN commit and this note's metadata commit. Parent
containment commits 57b73b060, 81e7a84ac and c4200ddc9 are not counted as test proof.

| Finding or unit | RED | GREEN |
| --- | --- | --- |
| WR-01 schema/type isolation | 4089bb52c | d6cfb9476 |
| CR-03 hierarchy/outbox limits | bfdea2e0d | 152519529 |
| CR-04 retained receipt starvation | 9e2f1a28a | 152519529 |
| Child disappearance continuity | 4915e3744 | 152519529 |

CR-03/04 share one coherent GREEN because bounded traversal, fair cursor state and
ancestor cleanup are the same recovery unit. Normal hooks passed on every new
commit. Only exact scoped files were staged; no tracked files were deleted.

## Commands, outcomes and retained evidence

Every backend invocation had this exact prefix from the verified repository:

    PYTHONDONTWRITEBYTECODE=1 python3 backend/tools/phase34.py backend

Each root below contains evidence/ with commands.json, backend.xml, redacted logs,
source-before.json, source-after.json and cleanup.json. Prior receipts are retained.

| Stage | Outcome | Linux root |
| --- | --- | --- |
| Existing WR-01 behavioral RED | 17 failed, 1 passed | /tmp/pgdp34-0fefe762dae4469187a2e63ff296b8ca-1s_5aic1 |
| Existing WR-01 GREEN | 18 passed | /tmp/pgdp34-96e68d44105f41559404e087fe3ec6a7-e_9k8lza |
| Existing CR-03 RED | 4 failed | /tmp/pgdp34-25f837e561a348459fefbd79d3793caf-swskqt7b |
| Existing CR-04 RED | 1 failed, 1 passed | /tmp/pgdp34-ce36c49318ac400ea710cc0339c875e8-i5jb5xhz |
| Prior safety checkpoint | 30 passed, active-ancestor fixture failed | /tmp/pgdp34-7f2c3b05bb5a4414953fe2b6e2cdcc50-oiqol2wb |
| Resume fixture correction | 31 passed | /tmp/pgdp34-b7cfa3a582b0459ba79b8c764baca885-6engjq5k |
| Fresh disappearing-child RED | 1 behavioral failure, 5 passed | /tmp/pgdp34-c9cbacea308a4f2d8790d6b4c08e20c0-471k9ee4 |
| Intermediate combined run | 36 passed, live-page fixture positioning failed | /tmp/pgdp34-4c0eed915a714cc982d7676f6e8ddfd8-ddod0x3x |
| Intermediate combined run | 38 passed, child-race fixture positioning failed | /tmp/pgdp34-7389119d85b44238889ea44fcb19fbcf-qoxyvfld |
| Final focused recovery | 39 passed, zero failed/errors/skips, 26.944 seconds | /tmp/pgdp34-b6f8b5363093485b9bc2b768ca33d906-wfws0mwu |
| Final full media regression | 401 passed, zero failed/errors/skips, 91.882 seconds | /tmp/pgdp34-e10efdf1efd14ef4a9bdcc7031d71a25-s1nwqlyl |

The inherited active-ancestor fixture tried claim_dispatch while resume remained
source-verification-required. Its correction uses the repository's legal
recovering-to-queued transition and claim_attempt CAS. No authority mock or direct
SQL authority rewrite was used. Page-positioning fixtures now traverse bounded
cursor sessions to reach their own newly created hierarchy despite prior tests'
retained directories. All original assertions remain. Infrastructure or fixture
failures above are not counted as RED/PASS gates.

Exact final focused arguments after the prefix:

    tests/handler/test_media_recovery_validation.py tests/handler/test_media_recovery_hierarchy.py tests/handler/test_media_recovery_fairness.py tests/handler/test_media_recovery_cursor.py tests/handler/test_media_recovery_continuity.py -q

Exact final full arguments after the prefix:

    tests/handler/filesystem/test_resources_handler.py tests/handler/filesystem/test_storage_access.py tests/tasks/test_owned_media_cleanup.py tests/handler/metadata/test_steam_owned_media.py tests/handler/metadata/test_rom_media.py tests/handler/test_persist_soundtrack_cover.py tests/handler/test_scan_write_fence.py tests/handler/test_scan_media_publication.py tests/handler/test_media_download_replacement.py tests/handler/test_media_download_transport.py tests/handler/test_media_download_gzip.py tests/handler/test_media_recovery_validation.py tests/handler/test_media_recovery_hierarchy.py tests/handler/test_media_recovery_fairness.py tests/handler/test_media_recovery_cursor.py tests/handler/test_media_recovery_continuity.py -q

Both final runs retain the two existing Alembic/SQLAlchemy warnings. No test was
excluded. There is no new host-runner, frontend, PostgreSQL or browser acceptance
claim. CR-08's actual PostgreSQL runtime proof remains Group 3 work.

## Static checks and decomposition

Scoped Trunk fmt, check --no-fix --no-progress --color=false --upstream c4200ddc9,
git diff --check and normal source hooks passed with no new diagnostics.
Four inherited F401/F811 fixture-import findings in the fairness test remain
outside the changed lines. The final static log is additive at the focused run's
evidence/group2-static-final.log. New test import/type diagnostics were corrected
before both final runs.

Logical counts use nonblank, noncomment lines. All paths below are under backend/.

| File | Logical lines |
| --- | ---: |
| handler/filesystem/scan_media_publication.py (existing WR-01) | 420 |
| handler/filesystem/scan_media_recovery.py | 243 |
| handler/filesystem/scan_media_traversal.py | 226 |
| tasks/scheduled/owned_media_cleanup.py | 33 |
| tests/handler/media_recovery_helpers.py | 47 |
| tests/handler/test_media_recovery_validation.py | 118 |
| tests/handler/test_media_recovery_hierarchy.py | 59 |
| tests/handler/test_media_recovery_fairness.py | 99 |
| tests/handler/test_media_recovery_cursor.py | 242 |
| tests/handler/test_media_recovery_continuity.py | 159 |

The new runtime helper owns only confined advisory enumeration. Existing owned
capabilities and SQL remain authoritative. No endpoint, schema, external trust
surface or goal-blocking stub was added. The two private cursor controls extend
the existing reserved owned-storage surface. Their serving privacy remains the
separate 34-08 nginx/HTTP gate.

## Cleanup and preservation receipts

Both final cleanup.json receipts report clean=true, source_unchanged=true and
empty remaining container/volume/network lists. Cleanup used exact run ownership
labels, without global prune.

Full-run exact cleanup removed containers 87fdec672917, c1acd249a3ed and
b7c9b9af0858; volumes pgdp34-e10efdf1efd14ef4a9bdcc7031d71a25_node_modules and
pgdp34-e10efdf1efd14ef4a9bdcc7031d71a25_owned; and network 6d7e2a17e010.
Its source-before and source-after SHA-256 are both
5c9435f4b36dd8615165f06724628675d7a1e28778c69e4651433a49d1c812e1.

Focused cleanup removed containers cf5be6dfa4c2, 376012ac20a2 and 77709080d2ef,
its two exact run-named volumes and network 954c8bf3e59c.
Its source-before and source-after SHA-256 are both
5a7a8e58cdb359c32a126ccdd9b2f3a0342a19fc43ee78485d346c0aac34db82.

Final preservation evidence is additive under the full run's
evidence/group2-preservation-final.log. It verifies unchanged hashes for dirty
STATE, Phase 33 UAT/VALIDATION, setup.py, both Compose files, ROADMAP and
REQUIREMENTS. Original media/fence and Group 1 tests, runner/fixtures, original
review, download fix/review and completed summary have no diff from c4200ddc9.
Untracked backend/pgdp_test/ and pgdp_test/ were not touched.

Host Media controls were not read or written. Their size, modification/change
timestamps and inode match the resume baseline: lock (0, 1792411826, 1792411826,
294876), cursor (2, 1792413626, 1792413626, 294888). No other host Media action was
taken. Final labelled inventory found zero Phase 34 containers, volumes or
networks. pgdp-dev remains exited/false; DB and Valkey remain running.

## Self-check and handoff

All six referenced source/test commits resolve, all ten listed scoped files
exist, final JUnit counts and exact cleanup/source receipts were inspected, and
the committed source passed normal hooks without modification after final tests.
Only this additive note is written after the GREEN source commit. No shared
planning status or existing summary was changed.

Group 2 is ready for independent review. Group 3 CR-02/05/08, 03 worker/non-ROM
fencing, 08 nginx/HTTP/production/browser gates and Phase 33 acceptance remain
open. No further correction group or deployment is started by this executor.
