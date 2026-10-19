---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
reviewed: 2026-10-19T13:41:06Z
depth: standard
scope: "Independent targeted Group 3 CR-02 and CR-08 review only"
diff_base: 383b47af59f655a1f00edf4c6a8e5780f2c1868b
source_pin: 3e2404aa57cc4bba8eb9af5463d45d2028e166f6
source_revision: 3e2404aa57cc4bba8eb9af5463d45d2028e166f6
original_review_revision: da362317b
checkpoint_revision: 5cf542a65
code_review_enabled: true
structural_review: false
files_reviewed: 7
files_reviewed_list:
  - backend/handler/database/roms_handler.py
  - backend/handler/filesystem/scan_media_publication.py
  - backend/handler/scan_handler.py
  - backend/endpoints/sockets/scan.py
  - backend/tests/handler/test_media_catalog_locking.py
  - backend/tests/handler/test_media_catalog_reconciliation.py
  - backend/tools/phase34.py
findings:
  critical: 1
  warning: 0
  info: 0
  total: 1
status: issues_found
---

# Phase 34: Targeted Catalog and Reference Locks Review

One BLOCKER remains in the new CR-02 preservation helper when joining a session
that already holds a Rom instance. No additional CR-08 defect was identified
in the reviewed change. This is source review of the seven listed files,
restricted to CR-02/CR-08 changes against the stated base. It does not accept
CR-05, Group 3, all of Task 34-15, or Phase 34.

## Scope and environment

All canonical inspection and this artifact write used SSH team4s-linux in
/home/d1sk/pc-game-download-portal. Preflight confirmed Linux, that exact Git
root, branch codex/phase-32-pgdp-naming, origin
https://github.com/D1skanime/pc-game-download-portal.git, and matching RomM
planning identity. Existing source drafts were excluded. Every source read
used git show or git grep at source pin 3e2404aa5; no working-tree source was
used as implementation evidence.

Canonical AGENTS.md, CLAUDE.md, the applicable backend guide and security
guidance, and pinned backend architecture were read. No .codex/skills or
.agents/skills directories exist. Review configuration is missing its review
key, so enabled defaults to true. Requested depth is standard; structural
review is disabled. All seven source paths are relative, tracked at the pin,
and not ignored.

The exact name-only lists for RED commits 4dcdcc11f and 029ff8117 resolve the
two requested approximate test names to test_media_catalog_locking.py and
test_media_catalog_reconciliation.py. The backend dialect selector is present
in 4dcdcc11f and therefore included. Socket scope covers the actual CR-02
merge call; publication scope covers current preservation and merge helpers.
Other pinned dependencies were inspected only to trace these behaviors.

No tests, application commands, database access, deployment, nested agents,
source edits, STATE edits, original review/checkpoint edits, or commits were
performed. Only this new review artifact was written.

## Critical Issues

### CR-10: Current-reference preservation can copy stale ORM metadata after acquiring the lock

**Classification:** BLOCKER
**Original scope:** CR-02
**File:** /home/d1sk/pc-game-download-portal/backend/handler/filesystem/scan_media_publication.py:439-444
**Related lines:** same file :393-402, :450-455;
backend/handler/database/roms_handler.py:391-445, :508-528, :1067-1082;
backend/tests/handler/test_media_catalog_reconciliation.py:174-207.

**Issue:** locked_scan_media_references obtains a current parent table row,
but preserve_current_scan_media discards its returned values and calls
get_rom with the same session. That ORM query has neither populate_existing
nor an explicit expiration/refresh. A Rom already retained in the session
identity map therefore keeps its previously loaded provider JSON and primary
paths. The parent lock prevents subsequent competing writes; it does not
refresh that cached object.

This can overwrite a newer provider reference, rather than merely return stale
data: retain copies the cached old path into fresh provider metadata. A changed
non-path field makes the JSON attribute dirty, so session.merge writes the
entire JSON document, including that old path, over the newer committed
reference. If cleanup already removed the old generation, the helper restores
a dangling catalog reference. The SQL fence does not correct ORM field values.

**Exact reproduction, not executed in this review:**

1. Extend the existing stale-session test at lines 174-207. Use its two
   published outputs as paths A and B, and seed ss_metadata to
   {"video_path": A, "video_url": "https://fixture.invalid/old"}.
2. In session S, retain stale = S.get(Rom, rom.id), as the test already does.
   Through its separate ThreadPoolExecutor connection, commit ss_metadata =
   {"video_path": B, "video_url": "https://fixture.invalid/current"}.
3. Construct the transient scanned Rom with ss_metadata =
   {"video_path": C, "video_url": "https://fixture.invalid/pending"},
   where C is a new pending provider path. Under the valid attempt context,
   call merge_scan_rom(scanned, session=S), then commit S.
4. Reload using a fresh session. Expected: video_path remains B and
   _pending_scan_media retains C. At this pin, the cached JSON supplies A;
   the changed video_url causes a JSON UPDATE containing A, replacing B.
   To exercise deleted-byte resurrection too, retire A with a cleanup intent
   and finish its scheduler cleanup after step 2 and before step 3.

The current test only checks path_cover_l on a fresh reload. Copying A onto a
target whose cached cover is already A need not mark that scalar dirty, so
the database can retain B and that assertion can pass. It does not prove
that preservation read current values. It also does not assert the returned
merged object or preserved provider JSON. This is one defect, including its
regression blind spot, rather than a separate test-style finding.

Normal scanner call sites currently open fresh sessions. This finding is
specifically the explicit-session path supported by both new helpers and
exercised by their stale-session regression; it is not a claim that every
ordinary scan reaches the failure.

**Fix:** Preserve reference fields from the authoritative column values read
by the parent locking query, keeping those values in the same transaction
through merge. Alternatively, explicitly refresh the required fields using
a table/column locking read that replaces cached ORM state. A plain repeated
get_rom is insufficient; on MariaDB/MySQL an earlier repeatable-read snapshot
also makes a nonlocking reread unsuitable as the authority. Keep fresh
provider data in _pending_scan_media and retain the slot/operation/parent
lock order. Extend the existing real-SQL regression with the provider-JSON
case above, asserting both persisted and returned paths, pending C, and the
cleanup-before-merge ordering when tests are next authorized.

## Remaining reviewed boundaries

CR-02: The changed actual _identify_rom merge and both internal Steam merge
sites use merge_scan_rom. Current parent state is reloaded after component
reconciliation, and both identified/unidentified returns preserve current
references. With a fresh session, the final merge holds the parent lock
through add_rom. A missing parent raises before that merge, preventing this
helper from recreating it. The four changed/removed-source tests use the actual
scanner, real component invalidation, SQL detachment/local-media removal,
cleanup-intent checks, and both cleanup-before-resume and bytes-still-present
orderings. They also inspect retained manuals/screenshots and publication of
pending provider video. Those cases do not cover CR-10.

CR-08: The parent lock selects Rom.__table__, including its primary reference
fields and provider metadata columns. Component IDs, owned/local media paths
and soundtrack cover paths use column-only locking selects; component metadata
uses its table directly. These locking statements do not eager-load platform
or the derived metadata view. Publication retains slot then operation before
parent/component/reference locks; cleanup takes the slot and cleanup intent
before the same parent reference lock. The added tests exercise publication,
association, scheduler cleanup, and reassociation versus cleanup through actual
repository calls. No further defect was identified in these scoped changes.

Runner: backend --dialect accepts only existing SQL_IMAGES keys and defaults
to mariadb. It flows through the existing Run(driver), generated isolated
environment, image selection, host preflight, and target-manifest checks.
The selector does not introduce a target override or bypass those guards.

## Evidence limits

The checkpoint at 5cf542a65 reports two PostgreSQL CR-08 GREEN cases, seventeen
MariaDB/fence cases, and five focused reconciliation cases. Its later four-case
PostgreSQL run used the pending tree, including CR-05 drafts, and its final
421-pass/3-fail result is likewise pending-tree executor evidence. None was
rerun or independently certified here, and pending-tree results are not proof
for the exact reviewed pin.

The reported isolated PostgreSQL runner uses glibc. It does not establish
production Alpine compatibility. The already known Group 2 CR09/WR02 follow-up
remains outside this review and is not rediscovered as a new finding.
CR-05 descriptor/inventory work and overarching acceptance remain outside scope.

---

_Reviewer: gsd-code-reviewer_
_Depth: standard_
_Source pin: 3e2404aa57cc4bba8eb9af5463d45d2028e166f6_
