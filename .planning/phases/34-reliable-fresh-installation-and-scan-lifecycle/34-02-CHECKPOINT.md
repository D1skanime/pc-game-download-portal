---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
plan: "02"
status: resolved
resolved: 2026-10-18
resolution_summary: 34-02-SUMMARY.md
subsystem: testing
tags: [alembic, mariadb, mysql, postgresql, isolated-tests]
requires:
  - phase: 34-01
    provides: Guarded disposable SQL and Redis runner
provides:
  - Correct backend import root for the disposable schema parity invocation
  - Actual baseline migration failure evidence for MySQL and PostgreSQL
affects: [34-02, 34-03, 34-04, 34-07, 34-08]
tech-stack:
  added: []
  patterns: [Fail-closed dialect acceptance]
key-files:
  created:
    - .planning/phases/34-reliable-fresh-installation-and-scan-lifecycle/deferred-items.md
  modified:
    - backend/tools/phase34_fixtures.py
key-decisions:
  - Do not bypass failed historical migrations or expand into their repair without scope authorization.
requirements-completed: []
requirements-scoped: ["D-05","D-06","D-07","D-09","D-14","D-15","D-16","SCAN-01","SCAN-06","SAFE-06"]
duration: not-recorded
completed: null
recorded: 2026-10-18
---

# Phase 34 Plan 02: Historical Execution Checkpoint (Resolved)

This checkpoint was resolved on 2026-10-18 after explicit user authorization for bounded historical migration portability repairs. All three 34-02 tasks are implemented and verified. The authoritative completion record is 34-02-SUMMARY.md. The sections below preserve the original pre-authorization checkpoint and its evidence; they do not describe the current execution status.

The disposable schema parity command now imports application configuration correctly; pre-existing MySQL and PostgreSQL migrations block operation-schema acceptance.

This is a committed checkpoint record, NOT a completed plan. Tasks completed: 0/3. Do not advance plan counts or requirements based on this SUMMARY filename. Resume at Task 1 after the baseline portability blockers are resolved. No durable operation contract or persistence implementation is claimed.

## Environment and Scope

Preflight verified Linux through ssh team4s-linux, Git root /home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming, and origin https://github.com/D1skanime/pc-game-download-portal.git. Planning state identifies the RomM PC Library and Phase 34. workflow.use_worktrees=false. No branch switch, worktree, nested agent, deployment, live scan, or application database cleanup occurred.

The user and plan reserve STATE, ROADMAP and REQUIREMENTS for the orchestrator. They were not edited or staged. All pre-existing dirty tracked files and untracked Media/, backend/pgdp_test/ and pgdp_test/ remain preserved.

## Progress and Commits

- Task 1: BLOCKED before operation implementation, by the required three-dialect baseline.
- Task 2: Not started.
- Task 3: Not started.
- Supporting repair: 7e3a212c2, fix(34-02): run disposable schema parity from backend import root.

The repair changes schema_commands to import tools.phase34_fixtures using python -c from the backend root, and changes its guard import to tools.phase34_target_guard. Trunk also normalized one existing CRLF line in this same module. No authentication, scanner, resolver, source-storage or persistence runtime semantics changed.

## Actual Test Evidence

1. Isolated Alembic heads/history on MariaDB:
   - Sole head: 0138_rom_metadata_facet_roles_view.
   - No 0139 filename exists. No new migration was created.
   - Evidence: /tmp/pgdp34-04125eba680b4b4486c2f3e7143d5872-b_0dchsa/evidence/13.log and 14.log.
   - Cleanup receipt reports clean=true and source_unchanged=true.

2. Exact plan command:
   python3 backend/tools/phase34.py schema --dialects mariadb,mysql,postgresql
   - Exit 1. All three independent dialects were attempted.
   - MariaDB upgraded/downgraded/re-upgraded to the existing head, then the original parity script failed with ModuleNotFoundError: config. This is infrastructure failure, not behavioral RED.
   - MariaDB evidence: /tmp/pgdp34-90140410d0134561858713fe0720dac3-g3zg9q7t/evidence, failing log 17.
   - MySQL 8.4 fails upgrade in 0001_initial_models.py:104 with SQL error 1064 on CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username).
   - MySQL evidence: /tmp/pgdp34-3c3748d9193041349ae6a421f1dc4b3b-67w7shzt/evidence/14.log.
   - PostgreSQL 15 fails upgrade in 0134_rom_updated_at_fractional_seconds.py:16 with syntax error near MODIFY in ALTER TABLE roms MODIFY COLUMN updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6).
   - PostgreSQL evidence: /tmp/pgdp34-baefc87ae94542498d4ff15ba2ee61fe-trb02u2b/evidence/14.log.
   - Each dialect's cleanup.json reports no remaining owned resources and unchanged synthetic source.

3. After the supporting import repair, ran Run('mariadb') with host_preflight, start, every schema_commands() command, and finally close, via Python stdin over SSH:
   - Exit 0.
   - Actual Alembic upgrade head, downgrade 0138_rom_metadata_facet_roles_view, re-upgrade head, then PASS schema constraints, lock statement and CRUD: mariadb.
   - Evidence: /tmp/pgdp34-13fa5617b41b49f48473605842ed7151-mp7j4v57/evidence.
   - Cleanup: clean=true and source_unchanged=true.
   - This proves the harness correction and baseline only. With no 0139 yet, downgrade/re-upgrade does not exercise a Phase 34 schema. Generic parity tables do not prove operation constraints or the singleton slot.

4. python3 -m unittest discover -s backend/tools/tests -p 'test_phase34*.py' -v:
   - Exit 0, 19 tests passed, 0.062 seconds.
   - No operation behavior tests exist yet.

5. Scoped Trunk:
   - /home/d1sk/.local/bin/trunk fmt backend/tools/phase34_fixtures.py: passed.
   - /home/d1sk/.local/bin/trunk check --no-fix --no-progress backend/tools/phase34_fixtures.py: passed.
   - Commit hook checked one modified file and passed without bypass.
   - git diff --check: passed before commit.
   - No tracked file deletion in the supporting commit.

Full frontend checks, generated API types, endpoint tests, operation races and cleanup-pair tests were not run because their implementation tasks have not started. Existing RQ/Vue defects and known full TypeScript failures remain open as recorded by 34-01.

## Deviations from Plan

1. [Rule 3 - Blocking] Corrected the parity script's import context.
   Found during Task 1 prerequisite matrix. Script execution placed tools rather than backend on sys.path. The corrected module import was verified on real disposable MariaDB. File: backend/tools/phase34_fixtures.py. Commit: 7e3a212c2.

2. Checkpoint before Task 1 acceptance.
   The required dialect baseline fails in two historical migrations unrelated to this task's changes. The execution scope boundary prohibits fixing unrelated pre-existing failures. Recorded exact failures in deferred-items.md rather than changing historical migrations or bypassing the gate.

## Known Stubs

No stubs were introduced. All three planned operation tasks remain unimplemented. In particular, no claimed complete schema/API contract was created without persistence semantics.

## Authentication Gates

None.

## Orchestrator Handoff

Progress: 0/3 tasks, no requirement completion, no shared tracking updates. Supporting fix committed; blocked summary committed separately. Authorize a bounded repair of historical MySQL/PostgreSQL migration portability or supply a separately verified corrected baseline. Then rerun the exact three-dialect matrix and resume Task 1 TDD. Recheck Alembic head uniqueness before creating 0139.

## Self-Check: PASSED (Checkpoint Record Only)

Verified the changed helper, this summary and deferred-items.md exist, supporting commit 7e3a212c2 resolves, and retained evidence contains actual baseline SQL failures and successful corrected MariaDB parity. This check validates the checkpoint record, not plan acceptance. Plan status remains BLOCKED.
