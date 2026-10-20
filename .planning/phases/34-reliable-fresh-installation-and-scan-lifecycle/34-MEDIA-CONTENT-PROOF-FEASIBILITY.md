---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
status: checkpoint
scope: CR-05 final content verification and exact deletion
evidence: source-and-primary-documentation-only
runtime_proof: false
implementation_authorized: false
corrective_acceptance: open
---

# CR-05 Final Content Proof: Focused Planning Feasibility Checkpoint

Date: 2026-10-19. Inspected working-tree source at HEAD 286fe2712 plus the
preserved uncommitted inventory drafts. This is an additive research supplement,
not an executable plan, accepted technical decision, SUMMARY or GREEN result.

## Result

A read-only verifier subprocess is a defensible candidate for bounding the
caller's wait for content reads. It does not, by itself, establish bounded SQL
lock release, safe publication/abort I/O, or a finite cross-process resource
lifecycle after timeout. Those contracts are not established by the existing
drafts or retained results. Do not turn that candidate into an executable
runtime correction by assuming the missing properties.

This is a missing feasibility contract and proof, not a finding that hashing in
another process is impossible. Expected correction size, if the contracts below
are established: three sequential additive plans, 34-16 through 34-18. No plan
number is consumed here and no executable correction plan was created.

The authorized task was planning only. No implementation, tests, application
imports, SQL/Redis access, live filesystem diagnostic, restart or deployment was
performed. The source-level and documentation findings below are not runtime
certification of a timeout mechanism.

## Preserved authority and historical evidence

The canonical pre-write checks passed: Linux over ssh team4s-linux, repository
/home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming, origin
https://github.com/D1skanime/pc-game-download-portal.git, matching RomM planning
identity, and pgdp-dev exited with Running=false.

34-15-PLAN.md and 34-15-SUMMARY.md remain historical records. Their no-hash-under-
lock contract is not rewritten or silently superseded by this note. Only a
subsequently accepted corrective contract could add narrowly bounded final
verification to the existing fence. Provider/network/initial streaming,
transformation, initial hashing and preparation remain outside SQL.

34-MEDIA-INVENTORY-DESIGN-CHECKPOINT.md and 34-MEDIA-FIX-INVENTORY.md retain
the actual e0491bf0e RED, last 81/83 result, Linux 5.15 same-inode/same-size/
restored-mtime observation, and preserved modified-private failures. These
results were read, not rerun. Five completed summaries remain five historical
summaries; media correction acceptance is OPEN.

34-UI-SPEC.md does not exist. The existing 34-UI-CONTRACT.md is the applicable
UI artifact. This backend correction introduces no UI redesign or new strings.

## Source findings that determine the boundary

| Source | Finding | Consequence |
| --- | --- | --- |
| backend/handler/filesystem/owned_publication.py:29 | _private_metadata compares parent/file identity and optional size/mtime/ctime. | Neither publication nor deletion obtains fresh content proof here. |
| owned_publication.py:125 | _unlink_owned uses that metadata predicate before unlink. abort and _rollback_published reuse it. | Publication-only hashing would leave modified-private abort and rollback unsafe. |
| owned_publication.py:156 | publish performs fsync, close, link, private unlink and parent fsync synchronously. | A deadline around a hash helper does not bound these other calls or revoke a mutation already submitted to the kernel. |
| owned_publication.py:230 | seal hashes in 1 MiB chunks and releases descriptors. | Retain zero descriptors per sealed output; retaining all 1,000 descriptors is not an alternative. |
| owned_publication.py:269 | _reacquire finally invokes publication.abort. | A failed/timed-out verification must not fall through to metadata-only deletion in a finally path. |
| backend/handler/filesystem/scan_media_publication.py:241 | ScanMediaInventory inherits the shared publish_and_associate seam. | Keep the original fatal SQL/badge controls reachable; do not add a parallel publication entry. |
| scan_media_publication.py:256 | _publish_media_batches obtains checked_scan_write and publishes every unit before one association callback. | The final verification exception must cover the complete accepted inventory with one aggregate deadline, not a fresh deadline per file. |
| backend/handler/filesystem/scan_media_recovery.py:92 | _digest_matches hashes final bytes before SQL locks. | Keep useful initial prechecks, but they cannot be the final deletion authority. |
| scan_media_recovery.py:121 | _private_identity can authorize private deletion from metadata alone. | Fresh expected-digest/identity proof is needed at the deletion boundary too. |
| scan_media_recovery.py:195 | _reconcile_manifest locks attempt and catalog references, then checks identities and deletes. | Reference safety and content proof must hold together; retain receipts on uncertainty. |
| scan_media_recovery.py:284 | reconcile_cleanup_intent checks references then deletes an exact path without a digest contract. | A blanket claim that every cleanup now has matching content proof would be false. Distinguish existing retired-path intent authority from receipt-owned output proof and resolve the required boundary explicitly. |
| backend/handler/database/scan_write_fence.py | checked_scan_write checks slot, attempt, owner, state, lease and cancellation; it has no elapsed-time enforcement. | Preserve this authority and lock order; it does not itself provide I/O cancellation or transaction expiry. |
| backend/handler/database/base_handler.py | create_engine has pool_pre_ping; no explicit execution/rollback deadline is configured here. | Do not infer a bounded rollback from the Session context manager. |
| backend/decorators/database.py | begin_session reuses explicit caller sessions and can retain their transaction beyond helper return. | A helper exception or helper return is not proof that the outer transaction released its locks. |

The original tests remain required and unchanged, including
test_sealed_publication_rejects_substitution_before_sql,
test_abort_preserves_substituted_private and
test_recovery_retains_sealed_substitution, including their modified cases.
The existing bound_recovery_hashes_outside_sql_locks test can continue testing
initial prechecks outside SQL; a future additive final verification test must
exercise the newly accepted exception separately.

## Primary documentation and limits

Linux describes coarse timestamp updates and the motivation for multigrain
timestamps. That supports the retained observation, not a proposed new identity
primitive. [Kernel timestamp documentation](https://docs.kernel.org/filesystems/multigrain-ts.html).

Python documents that process creation can exceed a requested timeout.
communicate(timeout) does not kill its child; killing followed by an unbounded
wait is not a hard return deadline. Start/readiness must precede SQL locks and
all post-timeout joins must be bounded.
[Python 3.13 subprocess documentation](https://docs.python.org/3.13/library/subprocess.html).

MariaDB statement timeout checks are cooperative and do not terminate the
surrounding transaction. The documentation explicitly warns against treating
them as a strict resource bound.
[MariaDB statement timeout limitations](https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/query-optimizations/aborting-statements).

MariaDB idle transaction timeouts close idle connections; their separate
read/write settings can override the general setting. They do not establish a
whole-operation deadline for active SQL, client filesystem calls or rollback.
[MariaDB transaction timeouts](https://mariadb.com/docs/server/reference/sql-statements/transactions/transaction-timeouts).

PostgreSQL 15 distinguishes statement execution, lock acquisition, and an idle
open transaction. An idle transaction timeout is not a universal transaction
deadline. Reused/pool sessions also require correct setting restoration or
connection invalidation.
[PostgreSQL 15 timeout documentation](https://www.postgresql.org/docs/15/runtime-config-client.html).

Inference from these sources and the inspected code: none of these mechanisms
alone justifies the combined claim "verification timed out, no publisher can
act later, all SQL locks are released, and cancellation finishes by deadline."
A stopped verifier, rejected verifier result, released SQL transaction and
confirmed operation stop are separate observable outcomes.

## Candidate contract for a bounded feasibility proof

This is a proposed proof target, not approved implementation or evidence.

- The helper only reads and hashes. It never imports/uses publication, deletion,
  association or SQL operations. Do not fork a live SQL connection into a helper,
  launch a publisher in a Future, or depend on a thread timeout for cancellation.
- Establish helper readiness and the trusted owned read authority before SQL.
  Reuse/extract the existing descriptor-relative no-follow traversal; no second
  resolver, raw caller root, privileged seal, notification-only proof or broker.
  The exact descriptor handoff/import boundary still needs a deterministic design.
- Proposed budget: one aggregate 2-second final verification wait for all units,
  with 1 MiB content chunks. A chunk check is only a secondary bound; nonblocking
  IPC and an independently controlled read-only process bound the parent's wait.
  Do not reset the budget for each of 1,000 outputs or extend it after timeout.
- Proposed resource ceiling: zero FDs per sealed output, at most eight extra
  parent FDs and twelve helper FDs, one admitted verifier across overlapping
  publication/recovery callers, 4 KiB IPC frames and 8 KiB buffered IPC per side.
  Stream request/result records with backpressure. Accepted output count and
  expected byte totals bind the transcript; no provider/manifest bound increase.
  These are proof targets, not measured limits.
- Bind each result to its invocation nonce, operation/attempt, receipt/output
  ordinal, expected digest/size and parent/file identity. Missing, duplicate,
  malformed, late or incomplete results confer no mutation authority. Fresh
  SHA-256 comparison is required even if every stat field still matches.
- A timeout permanently invalidates the invocation. Close its acceptance channel,
  request termination and use bounded reaping. An unreaped helper must retain a
  shared admission reservation across worker death/restart so repeated attempts
  cannot accumulate helpers/FDs. Do not assume SIGKILL acknowledgement or bounded
  process exit; no extra privileged host mechanism is authorized.
- The sole publisher remains synchronous with the existing fence and association.
  Verification timeout must prevent association and every later publication or
  compensation action for that invocation. It must not enter the current
  metadata-only abort/rollback finally paths. Retain possibly published output,
  prior good output and recovery evidence until fresh authoritative reconciliation.
- For deletion, obtain fresh matching expected content and identity while current
  SQL references and supported app-owned mutation paths are serialized. A prior
  hash or a new hash of unknown bytes cannot authorize deleting substituted bytes.
  Missing digest, changed bytes, uncertain reference lookup, timeout or uncertain
  SQL outcome retains the object/receipt. Include abort, publication rollback,
  private recovery and final recovery, not just successful publication.
- Supported authority is cooperating application-owned mutation of generated
  immutable media through the existing capability/fence boundaries. SQL locks
  cannot serialize arbitrary privileged host writes. Observe and reject tested
  substitutions; do not claim an atomic SQL/filesystem operation or guaranteed
  protection against a host write after observation.

## Unresolved feasibility gates

1. Define the exact timeout scope and lock-release protocol for the native
   MariaDB and psycopg drivers, including explicit caller sessions, rollback
   failure, connection invalidation and outer-session reuse. Session timeouts
   may help under a responsive database but their documented limits must remain
   explicit. No new grants, global DB settings or administrative kill authority
   are approved. A caller wait bound cannot be presented as a confirmed stop.
2. Prove the deadline path cannot invoke blocking or destructive compensation,
   and distinguish final-verifier wait from publication/link/fsync/unlink and SQL
   acknowledgement latency. Current synchronous mutation syscalls are outside a
   read-only helper's control. Moving mutations into a timed-out child merely
   recreates the prohibited late-publisher problem.
3. Specify a finite helper/admission lifecycle that remains safe after worker
   kill/restart and delayed exit, including bounded IPC and no inherited SQL FDs.
   This is not solved by a per-process counter or an unbounded join in finally.
4. Resolve expected-content authority for every cleanup boundary in scope.
   Receipt-owned sealed outputs have expected hashes. Unfinished staging,
   fsync-failure aborts and legacy retired-path intents cannot silently acquire
   digest authority from current bytes. Preserve the unchanged storage regressions,
   especially exact cleanup on seal-fsync failure, while specifying safe retention.

Because these gates affect the central safety contract, they cannot be buried
as executor discretion in tasks 17 or 18. No blanket exception to plan 15 is
accepted. This checkpoint does not require new UI research or phase replanning.

## Concrete routes back to planning

A. Parent authorizes a focused disposable feasibility proof as a separate next
task. Use only the existing Phase34 harness, actual SQL/filesystem capabilities,
MariaDB and PostgreSQL, and test-owned blocking-I/O/process barriers. Establish
the four contracts above before runtime correction plans are finalized. This
route is not executed or newly authorized by this note.

B. Parent clarifies that the numeric deadline applies to verifier-result waiting,
with failed SQL/OS infrastructure reported as uncertain until lock release and
stop are confirmed. Evaluate that narrower timing contract explicitly; do not
silently interpret it as the current requirement or relax content preservation.

If neither route resolves the gates within the existing authority, retain this
checkpoint. Privileged filesystem sealing, new host/kernel dependencies and a
broker remain excluded alternatives, not proposed work.

If feasible, the natural three-plan decomposition is:
16, bounded read-only proof primitive and deadline/resource evidence;
17, shared fenced inventory publication plus exact prepared abort/rollback;
18, final-boundary recovery deletion and full compatibility/proof acceptance.
These are tentative responsibilities only, not file manifests or scheduled waves.
All three would precede 03; same-file overlap would make them sequential.
Original 15 and completed artifacts remain untouched.

## Required future evidence, never implied by this note

Preserve e0491bf0e and every original assertion. Add a timestamp-independent
same-inode/same-size/restored-mtime substitution fault at publication and exact
deletion boundaries. Include a real blocking syscall in the verifier, bounded
timeout/cancel observation, late result rejection, worker/verifier kill and
restart, delayed helper exit/admission refusal, and both SQL lock orderings.
Retain modified private bytes and unknown possibly committed old/new outputs.
A mocked monotonic clock, source grep or Future timeout alone cannot pass.

Demonstrate 1,000 valid Steam outputs and 65 two-badge achievements, original
fatal SQL/indeterminate badge controls, one association transaction, receipt
schema compatibility and unchanged bounds, zero per-sealed-output FDs, and the
unchanged 96 soft-FD-limit control. Measure aggregate final-verification latency
and the actual separate lock-release/cancellation observations on both databases.

Use no new runner. Run every existing media/storage/fence/recovery regression
without exclusions, plus additions, with explicit paths through
PYTHONDONTWRITEBYTECODE=1 python3 backend/tools/phase34.py backend
(and --dialect postgresql for actual PostgreSQL proof). Record complete counts,
RED assertion versus infrastructure failures, exact run cleanup, source-before/
after equality and actual static results. Preserve original evidence and source
drafts. New runtime modules, if approved, stay within 500 logical lines.

After implementation and GREEN evidence, a separate independent code review
is required. Parent owns that review route, exact commits, shared planning state
and acceptance. No nested agents or commits are requested here.

## Four-source coverage and independent gates

This targeted checkpoint preserves the existing full audit in 34-VALIDATION.md;
it does not replace its phase plan set or mark implementation covered by success.

| Source | Item | Existing or proposed owner | Status |
| --- | --- | --- | --- |
| GOAL | Reliable first/normal scan, safe restart/cancel, immutable source | Existing 01-15; CR-05 supplement before 03 | Existing coverage retained; correction blocked |
| REQ | SCAN-02, SCAN-06, SAFE-02, SAFE-06 | Existing 15/03/08; tentative 16-18 correction | Acceptance OPEN |
| RESEARCH | One fence/session, owned capabilities, manifests/outbox, SQL/FS non-atomicity, serving boundary | Existing 15/03/08 and this candidate | Reuse retained; feasibility gates above |
| RESEARCH | Real I/O deadline, finite helper lifecycle, final deletion proof | Tentative 16-18 | UNPLANNED pending feasibility, not silently dropped |
| CONTEXT/REQ | D-01 enrolled admin, D-02 root retry, D-03 uncertain save, D-04 explicit scan CTA | Existing 05/06/09/10/08 | Coverage unchanged |
| CONTEXT/REQ | D-05 confirmed start, D-06 replay-safe acceptance | Existing 01/02/03/07/11/12/13/14/08 | Coverage unchanged |
| CONTEXT/REQ | D-07 actionable failure | Existing 03/04/11/12/13/14/08; corrective failure handling | Correction OPEN |
| CONTEXT/REQ | D-08 provider warnings/targeted retry | Existing 04/12/13/14/08 | Coverage unchanged |
| CONTEXT/REQ | D-09 reload same job, D-10 disconnect/reconcile | Existing 01/02/07/11/12/13/14/08 | Coverage unchanged |
| CONTEXT/REQ | D-11 verified restart, D-12 confirmed cancellation/retained results | Existing 15/03/04/12/13/14/08; tentative correction | Correction OPEN |
| CONTEXT/REQ | D-13 established localized PGDP UI | Existing UI-CONTRACT and 06/09-14/08 | Preserved; no UI work here |
| CONTEXT/REQ | D-14 shared resolver/lifecycle, D-15 module bounds, D-16 Linux/read-only Games | All existing plans and this note | Constraints retained |
| CONTEXT | Deferred recognition/matching/download redesign | Excluded by 34-CONTEXT.md | EXCLUDED, no new task |

CR-10 stale provider JSON, CR-09 production musl compatibility and WR-02 cursor
temporary/PID collision remain separate OPEN findings with their existing review
artifacts. Group 1's clean review is not expanded. No finding is absorbed or
closed by this note. 34-03 cannot begin until the parent accepts the whole media
quality gate, including these independent findings and post-implementation review.
34-08 HTTP/production/worker proof and Phase 33 browser acceptance remain OPEN.

## Write and preservation boundary

Only this new Markdown file is added by unified git apply over SSH on canonical
Linux. STATE, ROADMAP, REQUIREMENTS, all old phase artifacts/summaries, runtime/
test drafts, Compose changes, untracked pgdp_test directories and host Media/
Games remain untouched. No staging, commit, push, branch/worktree change or
resource cleanup occurs. Planning integrity checks are not runtime tests.
