# Repository Cleanup Report

## Scope

This report covers the risk-reduced cleanup on branch
codex/repository-cleanup. No application, metadata, download, transfer,
manifest, or authentication logic was changed.

Git history has not been rewritten. The separate migration plan is in
docs/GIT-HISTORY-CLEANUP-PLAN.md and requires explicit approval before any
force-push.

## Before and after

Measurements are from the canonical Linux checkout at /home/d1sk/romm. The
source archive is the gzip-compressed output of git archive.

| Metric                |               Before cleanup |        After cleanup stage |
| --------------------- | ---------------------------: | -------------------------: |
| GitHub source archive | 178,009,729 bytes, 169.8 MiB | 26,112,954 bytes, 24.9 MiB |
| Versioned files       |                        4,205 |                      3,745 |
| Versioned blob size   | 215,681,381 bytes, 205.7 MiB | 59,564,419 bytes, 56.8 MiB |
| Git object database   |            772.16 MiB packed |          772.16 MiB packed |
| History rewrite       |                not performed |  pending explicit approval |

The source archive is within the requested 20 to 40 MB guideline. The Git object
database remains large because historical objects are still reachable.

## Removed from Git tracking

The following were removed with git rm --cached, so local files were not
physically deleted:

- .github/resources/ and the historical .github/screenshots/ path, containing
  original RomM badges, logos, screenshots, and large preview GIF/WebP files.
- .tmp/, temporary MP3 files and local runtime configuration.
- .codex/, local GSD/Codex installation artifacts and agent state.

The application workflows under .github/workflows/ remain tracked. The complete
.planning/ directory remains tracked so GSD state, architecture decisions,
migrations, and development history stay available.

## Local-only files preserved

The local checkout keeps these classes, now ignored for future commits:

- Docker/ runtime media and container data.
- Games/ local ROM and PC library data.
- RomM-phase*.zip local archives.
- *.orig editor or merge leftovers.
- .codex/, .tmp/, .github/resources/, and .github/screenshots/ local files.

No physical local deletion was performed.

## New ignore rules

.gitignore now covers local runtime data, local GSD/Codex data, original local
GitHub resources, local archives, and *.orig files.

.dockerignore now excludes local runtime data, local agent state, planning
artifacts, local archives, and editor leftovers from Docker build contexts.

The rules do not globally ignore ZIP, ISO, RAR, GIF, WebP, or PNG because the
repository contains legitimate application assets and test fixtures.

## Hygiene automation

Added scripts/check-repository-hygiene.py and
.github/workflows/repository-hygiene.yml.

The check validates tracked paths, rejects local runtime directories, rejects
unapproved large media and archive files, detects common tracked secret markers,
and allows the maintained test-fixture archive directories.

## Historical findings

Reachable history contains large obsolete objects, including:

- RomM-phase17-403c20c24.zip, about 132.9 MB.
- config/databases/ib_logfile0, about 100.7 MB.
- backend/tasks/Metadata.zip, about 90.3 MB.
- Historical original RomM preview GIF/WebP files and duplicate screenshots
  under both .github/resources/ and .github/screenshots/.
- Historical temporary MP3 files.
- Historical local runtime media under Docker/Media.

Legitimate application assets and test fixtures were not removed by extension
alone. The migration plan lists the candidate paths and preservation rules.

## Verification

Passed:

- Linux preflight against /home/d1sk/romm.
- git diff --check.
- scripts/check-repository-hygiene.py.
- scripts/verify-portainer-stack.sh.
- Tracking and relative-path audits.
- Current source archive measurement after index cleanup.

Still required before merge:

- Fresh clone verification.
- Backend and frontend gates appropriate for the repository state.
- Review of the history-rewrite dry run.
- Backup verification before any history rewrite.

## Open risks

- GitHub still contains historical large objects until the separate rewrite.
- Existing local clones and open pull requests need migration guidance after a
  force-push.
- GitHub may retain unreachable objects temporarily after garbage collection.
- Many historical upstream release tags require explicit treatment.

## Review addendum evidence

The requested migration-readiness checks were performed without changing GitHub.

### Reference inventory and decisions

The canonical checkout has 12 local branches, 6 local remote-tracking refs, and
217 local tags. The remote has 6 heads, one annotated release tag, and the
GitHub-managed refs/pull/1/head for merged PR #1.

Proposed decisions, pending approval:

| Reference                              | Decision                                                                                         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------ |
| main                                   | Rewrite to the filtered target containing the cleanup changes, then force-push with lease        |
| codex/repository-cleanup               | Keep for review; delete after accepted cutover                                                   |
| archive/main-before-phase17-2026-09-20 | Preserve only in verified backup, then delete remote                                             |
| codex/pc-module-analysis               | Preserve only in verified backup, then delete remote                                             |
| codex/phase17-release-verification     | Preserve only in verified backup, then delete remote                                             |
| codex/release-phase18                  | Preserve only in verified backup; merged PR #1 makes it redundant; delete remote                 |
| release-phase18-20260926               | Preserve as a rewritten release marker, subject to explicit tag approval                         |
| refs/pull/1/head                       | GitHub-managed merged-PR ref; document and handle through GitHub support if it remains reachable |

No non-pushed local branch or tag is discarded; all are included in the local
bundle backup.

### Backup and restore evidence

Backup directory:
/home/d1sk/backups/pc-romm-history-cleanup-20261012T083849/

It contains the full remote mirror, local-all-refs.bundle, ref SHA lists,
SHA256SUMS, a remote restore clone, and a local-bundle restore clone.
git bundle verify passed. Both restore clones were created and checked with
git fsck --full --no-reflogs. The local restore emitted only Git fsck
informational output; no dangling-object failure was reported.

### Isolated dry-run evidence

The filter was executed only in rewrite-dry-run.git, never in the active
checkout. The exact candidate paths were .codex/, .tmp/, .github/resources/,
.github/screenshots/, Docker/, Games/, RomM-phase*.zip, config/databases/, and
backend/tasks/Metadata.zip. The glob syntax was accepted by filter-repo and
the rewrite completed across 12,451 commits.

The filtered mirror measured 129.87 MiB packed (about 130 MiB on disk) versus about 772 MiB before the
rewrite. The retained application tree comparison found no missing or changed
application files after accounting for the cleanup files and ignore-rule
changes. The current cleanup branch remains about 24.9 MiB as a gzip source archive
with 3,745 versioned files and about 56.8 MiB of versioned blob bytes. The
filtered dry-run source archive is 26,110,222 bytes.

### Validation and fresh clone

Passed: Linux preflight, hygiene script, Portainer stack verifier, git
diff --check, backup verification, filtered-mirror fsck, fresh clone
verification, frontend typecheck, and frontend production build. The frontend
build emitted existing warnings for :deep CSS syntax, large chunks, and a
dependency eval; it completed successfully.

The full frontend Vitest run produced 945 passing tests and 1 failing test in
112 files. The failure is the existing sourceMutationInventory assertion for
the PcDlcMediaTab DELETE placement route, reported as an unclassified
authority route. It is unrelated to this cleanup and remains an explicit
cutover gate. No application code was changed to hide it. Backend gates must
also be run again immediately before cutover on the deployment environment.

### Planned cutover and rollback

The commands below are intentionally not executed:

git push --force-with-lease pc-romm <rewritten-main>:refs/heads/main
git push --force-with-lease pc-romm <rewritten-cleanup>:refs/heads/codex/repository-cleanup
git push pc-romm --delete archive/main-before-phase17-2026-09-20 codex/pc-module-analysis codex/phase17-release-verification codex/release-phase18
git push --force-with-lease pc-romm <rewritten-release-tag>:refs/tags/release-phase18-20260926

For rollback, stop all pushes and restore the original SHA-pinned refs from the
verified remote mirror or bundle, for example:

git push --force pc-romm <backup-main-sha>:refs/heads/main
git push --force pc-romm <backup-release-sha>:refs/heads/codex/release-phase18

After rollback, verify every remote head and tag against the saved SHA lists.
Existing local clones must not merge old and rewritten histories; they should
fetch the approved rewritten refs and recreate local branches, or reclone.
