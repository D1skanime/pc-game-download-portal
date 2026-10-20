---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
reviewed: 2026-10-19T13:09:09Z
depth: standard
scope: "Independent targeted Group 2 review of original CR-03, CR-04 and WR-01 only"
source_revision: 1525195297dc19dac51b2592bea022bfb3324ab1
recovery_note_revision: 9781cf3e2f47d0d92c859054efd0411d94be2c5d
original_review: .planning/phases/34-reliable-fresh-installation-and-scan-lifecycle/34-REVIEW.md
code_review_enabled: true
code_review_config_basis: "workflow.code_review missing, defaults to true"
structural_prepass: false
evidence: static_source_only
runtime_proof: false
whole_phase_approval: false
files_reviewed: 10
files_reviewed_list:
  - backend/handler/filesystem/scan_media_publication.py
  - backend/handler/filesystem/scan_media_recovery.py
  - backend/handler/filesystem/scan_media_traversal.py
  - backend/tasks/scheduled/owned_media_cleanup.py
  - backend/tests/handler/media_recovery_helpers.py
  - backend/tests/handler/test_media_recovery_validation.py
  - backend/tests/handler/test_media_recovery_hierarchy.py
  - backend/tests/handler/test_media_recovery_fairness.py
  - backend/tests/handler/test_media_recovery_cursor.py
  - backend/tests/handler/test_media_recovery_continuity.py
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
status: issues_found
---

# Phase 34: Independent Group 2 Recovery Review

The targeted result is issues_found: one new BLOCKER and one new WARNING.
Finding IDs continue the original review's numbering to avoid reusing its IDs.
All source and test line numbers below refer to pinned commit
1525195297dc19dac51b2592bea022bfb3324ab1, regardless of concurrent Group 3 edits.

## Scope and evidence limits

This review covers the ten explicit files above for CR-03/04 and WR-01.
Publication review is restricted to manifest validation and necessary recovery
contracts. Storage capabilities, session/fence handling, SQL references,
operation transitions and production image definitions were read as supporting
dependencies at the same pin. The recovery note at 9781cf3e2, safety checkpoint,
resume record, original review and relevant 34-15 plan/summary context were read.

Linux preflight confirmed SSH team4s-linux, root
/home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming, origin
https://github.com/D1skanime/pc-game-download-portal.git and this project's
planning identity. Canonical AGENTS.md, CLAUDE.md and applicable backend/security
guidance were followed. No project skill directories were present under
.codex/skills or .agents/skills. The ten source paths are not ignored.
The missing workflow.code_review key defaults to enabled. Structural pre-pass
was off; depth was standard and targeted.

No agents, tests, application imports, runtime inspections, SQL access, database
changes, deployment, commits or shared tracking writes were performed.
The executor's 401 full / 39 focused passes and cleanup receipts are recorded
claims, not independently rerun or certified here. Reproductions below are
source-derived regression specifications, not executed tests.
Only this additive review artifact is written by this reviewer.

Group 1's clean review remains limited to CR-01/06/07. CR-02/05/08 remain Group 3
work and are not re-reported or evaluated here. This is not approval of 34-15,
Phase 34, Phase 33, HTTP privacy or any deployment.

## Critical Issues

### CR-09: Production Alpine images cannot resolve the traversal's libc symbol

**Classification:** BLOCKER
**File:** /home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_traversal.py:63-68
**Cross-links:** same file :212,233-239; backend/handler/filesystem/scan_media_recovery.py:214-216; docker/Dockerfile:16,28,165,179-188,219-224; .github/workflows/build.yml:109-114,124-129.

**Issue:** Checking Linux and sizeof(long)==8 does not establish that
ctypes.CDLL(None).getdents64 exists. The supported production slim/full images
use Alpine 3.23 and Alpine Python, and are built for both arm64 and amd64.
musl removed the getdents64 compatibility alias in 1.2.4. Resolving the attribute
there raises AttributeError before a directory page can be read. Neither the
walk's storage-error isolation nor the recovery loop catches that exception.
Every receipt sweep therefore fails at its first step on these images, even
with a single valid stopped receipt on an ordinary local filesystem.
The scheduler's finally block can still process independent cleanup intents;
it does not restore receipt traversal.

This is a supported deployment incompatibility, not a request for Windows or
32-bit Linux support. The Ubuntu development Dockerfile and its successful
glibc-based test runs cannot establish production musl compatibility.
The upstream change is visible in the
[musl 1.2.4 source upgrade, src/linux/getdents.c removal](https://android.googlesource.com/platform/external/musl/%2B/de1aff4a6d5ce868deb3cdd1686164fd534bbf2f%5E1..de1aff4a6d5ce868deb3cdd1686164fd534bbf2f/).
The [glibc API documentation](https://sourceware.org/glibc/manual/latest/html_node/Low_002dlevel-Directory-Access.html)
describes the symbol that this implementation assumes.

**New reproduction:** In a disposable build of the pinned production image,
create a normal manifest-backed orphan using the existing real SQL/capability
fixture, stop its attempt, then invoke owned_media_cleanup_task.run().
The first RecoveryWalk.step reaches line 66 and raises AttributeError for
getdents64; the orphan and receipt remain. Repeated runs have the same outcome.
Exercise both production architectures, and retain an independent due intent
to confirm that its finally pass still runs. No live resources are needed.

**Fix:** Keep the existing descriptor confinement and bounded directory-cookie
interface, but implement its native binding against the actual supported libc
and architecture matrix. Use a verified bounded native directory API or a
properly defined getdents64 syscall binding for each supported architecture,
rather than assuming a glibc symbol or hardcoding one architecture's syscall
number. Merely catching AttributeError and skipping every sweep is not a fix.
Add actual Alpine amd64/arm64 scheduler coverage alongside the current glibc
coverage, including more than 32 retained receipts followed by a stopped orphan.

## Warnings

### WR-02: A crash-left cursor temporary prevents saving after PID reuse

**Classification:** WARNING
**File:** /home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_traversal.py:178-185
**Cross-links:** backend/handler/filesystem/storage_access.py:604-634; backend/tests/handler/test_media_recovery_cursor.py:116-146; backend/tests/handler/test_media_recovery_continuity.py:131-152.

**Issue:** The new durable cursor uses OwnedReplace.binary_file, whose exclusive
temporary basename is deterministic:
..recovery-cursor.json.<pid>.tmp. Process death between its os.open and
os.replace leaves that file behind; Python exception cleanup cannot run.
When a later writer has that PID, O_EXCL fails with FileExistsError. Because
created is still false, this path correctly preserves the old temporary but
never resolves the collision. All later cursor saves in that same process
fail, leaving the previous checkpoint unchanged. With 32 retained receipts
after that checkpoint, repeated same-process calls replay them and cannot
persist progress toward a later recoverable receipt. A different writer PID
can save again, so this is not a claim that the default forking RQ deployment
necessarily remains stalled on every subsequent job.

The existing process-exit test dies during traversal before entering cursor
save. The replacement-failure test raises a normal exception, which executes
the helper's temporary cleanup. Neither covers a crash during the cursor
write followed by PID reuse. Persistent storage and PID reuse across container
restarts make the collision a real recovery boundary, not an invalid manifest.

**New reproduction:** On disposable owned storage, save a cursor positioned
before a retained 32-receipt page. Leave an exact cursor temporary for the next
writer's PID, representing a killed previous writer before rename. Invoke the
real scheduler twice in that process. Both exits fail at storage_access.py:612,
the cursor bytes stay at the old checkpoint and the later orphan is not reached.
For end-to-end fault coverage, kill a writer immediately after opening that
temporary and restart it in a controlled PID namespace with the same PID.

**Fix:** Make the existing owned replacement capability tolerate crash-left
temporary collisions, for example with unique exclusive basenames and bounded
retry, while preserving atomic replacement and abort ownership. Alternatively,
reclaim only a proven stale exact cursor temporary while holding the cursor
flock, through existing descriptor-relative capabilities. Do not delete arbitrary
reserved children or change receipt authority. Add a crash-during-save/PID-reuse
case proving that a subsequent save succeeds, retained receipts survive and a
later orphan is eventually reclaimed.

## Targeted source assessment

- The original 513-child hierarchy rejection is removed from operation/attempt
  traversal. _entry reads at most 4096 bytes, the outer loop makes at most 512
  steps and receipt work stops at 32. Batch receipt enumeration retains its
  separate 512-child bound. The fair-progress guarantee is conditional on the
  binding and checkpoint defects above being addressed.
- Paths are restricted to the reserved UUID hierarchy. open_directory reuses
  policy authorization and the no-follow descriptor walk; child stat does not
  follow links. Cursor shape, frame ancestry, integer ranges and dev/inode
  resets are checked. The flock spans load, traversal and save, and read/save
  failures release it. Disappearing child stat advances the parent cookie.
- _prune_ancestor acquires the actual execution-slot then operation-row locks
  through _lock_attempt before checking the current lease and calling rmdir.
  It uses no recursive deletion. Nonempty ancestors survive; the live current
  attempt protects its hierarchy. After prune-first, new batch construction
  recreates ancestors. The tests use real repository transitions and capability
  I/O, but their new-first barrier is before the pruning transaction and their
  prune-first branch waits for pruning to finish. They establish those ordered
  outcomes, not runtime proof of overlapping row-lock contention.
- WR-01's original identity-type failure is addressed at source: primitive and
  container checks precede UUID/path processing; identities must normalize
  exactly; input byte/depth bounds and ManifestValidationError isolate malformed
  evidence. Output ownership, digest/size validation and receipt child checks
  remain. Unknown or unrecorded private evidence is retained conservatively.
- Recovery still checks actual SQL references under catalog locks after hashing,
  rechecks final file identity before exact deletion and skips a live matching
  attempt. This review does not reopen Group 3's known reference-lock issue.
  No new lease, SQL authority, resolver or deletion scope was introduced.
- The scheduler finally pass runs after a recovery exception and does not return
  success in that case. SQL/fence/unknown errors are not added to the optional
  receipt catch. Cursor-save failure adds a note to an existing exception.
  If outbox work also fails, Python propagates that second exception with the
  first in its exception context; this is not proof that the first remains the
  outward exception.
- The new fixtures invoke the actual scheduler, SQL transitions/reference
  checks and owned capabilities. Fault injection wraps listing, stat timing or
  replacement seams; it does not replace SQL authority with string assertions.
  The 513-operation fixtures also include absent operation rows, rather than
  proving 513 persisted historical SQL operations.
- Pinned logical runtime counts are publication 420, recovery 243 and traversal
  226 (nonblank, noncomment lines). They satisfy the 500-line target. Size and
  the executor's reported passing counts do not override the findings.

---

_Reviewer: gsd-code-reviewer_
_Depth: standard, targeted Group 2 only_
_Evidence: static source at 152519529; no runtime proof or whole-phase approval_
