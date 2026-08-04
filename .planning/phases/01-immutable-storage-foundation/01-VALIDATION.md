---
phase: 01
slug: immutable-storage-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-04
---

# Phase 01 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x, pytest-asyncio 1.x, Hypothesis 6.x |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py tests/models/test_storage.py -x` |
| **Full suite command** | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py tests/handler/database/test_storage_handler.py tests/models/test_storage.py -x` |
| **Estimated runtime** | To be measured during Wave 0 |

## Sampling Rate

- **After every task commit:** Run the narrowest affected test selection from the map below with `-x`.
- **After every plan wave:** Run the full phase command.
- **Before `$gsd-verify-work`:** Run the full phase suite, cross-dialect migration checks, and repository pre-PR verification required by `CLAUDE.md`.
- **Max feedback latency:** 120 seconds for task-level tests; split slower migration checks into the wave gate.

## Per-Task Verification Map

The planner replaces provisional task IDs with final plan/task IDs without changing requirement coverage.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | ROOT-01 | T-01-ROOT-CREATE | Existing roots register without source creation | integration/unit | `cd backend && uv run pytest tests/handler/database/test_storage_handler.py -k register -x` | No, W0 | pending |
| TBD | TBD | 0 | ROOT-02 | T-01-MODE-BYPASS | Only `external_read_only` persists | model/migration | `cd backend && uv run pytest tests/models/test_storage.py -k mode -x` | No, W0 | pending |
| TBD | TBD | 0 | ROOT-03 | T-01-HEALTH-WRITE | Health inspection is bounded and non-mutating | filesystem unit | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py -k health -x` | No, W0 | pending |
| TBD | TBD | 0 | ROOT-04 | T-01-PATH-LEAK | Mapping persists only root identity plus relative path | model/migration | `cd backend && uv run pytest tests/models/test_storage.py -k mapping -x` | No, W0 | pending |
| TBD | TBD | 0 | PATH-01 | T-01-TRAVERSAL | Lexically unsafe path forms fail closed | property/unit | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py -k normalize -x` | No, W0 | pending |
| TBD | TBD | 0 | PATH-02 | T-01-ESCAPE | Canonical target cannot escape the root | filesystem unit | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py -k containment -x` | No, W0 | pending |
| TBD | TBD | 0 | PATH-03 | T-01-INVALID-TARGET | Only active, existing, readable directories resolve | filesystem unit | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py -k target -x` | No, W0 | pending |
| TBD | TBD | 0 | PATH-04 | T-01-NAME-CONFUSION | Valid Unicode and nested names resolve exactly | parameterized unit | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py -k valid_names -x` | No, W0 | pending |
| TBD | TBD | 0 | PATH-05 | T-01-SYMLINK | Root, intermediate, and leaf symlinks fail closed | filesystem unit | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py -k symlink -x` | No, W0 | pending |
| TBD | TBD | 0 | TEST-01 | T-01-MATRIX | Complete adversarial matrix and before/after manifest pass | suite gate | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py -x` | No, W0 | pending |

## Wave 0 Requirements

- [ ] `backend/tests/handler/filesystem/test_storage_resolver.py` - lexical, containment, health, target, Unicode, symlink, overlap, and immutability tests.
- [ ] `backend/tests/handler/database/test_storage_handler.py` - root registration and mapping transaction tests.
- [ ] `backend/tests/models/test_storage.py` - enum, constraints, relationships, and portable schema tests.
- [ ] Cross-dialect migration gate - upgrade, downgrade one revision, and re-upgrade on MariaDB and PostgreSQL without touching library fixtures.
- [ ] Recursive before/after fixture manifest helper that records names, kinds, sizes, non-access timestamps, and hashes where applicable.
- [ ] Mutation tripwires for `Path.mkdir`, write-mode `open`, temporary-file creation, rename, move, copy, unlink, and removal helpers during root and mapping operations.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real NAS permission and access-time behavior | ROOT-03 | NAS protocol, mount flags, and active encode window are environment-specific and intentionally deferred to Phase 9 | Do not run in Phase 1. Phase 9 validates the approved `:ro` mount and `noatime` or NAS equivalent during a maintenance window. |

## Validation Sign-Off

- [ ] All tasks have automated verification or Wave 0 dependencies.
- [ ] Sampling continuity has no three consecutive tasks without automated verification.
- [ ] Wave 0 covers all missing test references.
- [ ] No watch-mode flags are used.
- [ ] Task-level feedback latency remains below 120 seconds.
- [ ] Cross-dialect migration verification passes at the wave gate.
- [ ] `nyquist_compliant: true` is set after final plan task IDs replace provisional entries.

**Approval:** pending plan verification
