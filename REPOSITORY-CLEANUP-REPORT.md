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
| GitHub source archive | 178,009,729 bytes, 169.8 MiB | 26,109,965 bytes, 24.9 MiB |
| Versioned files       |                        4,205 |                      3,741 |
| Versioned blob size   | 215,681,381 bytes, 205.7 MiB | 59,552,183 bytes, 56.8 MiB |
| Git object database   |            772.16 MiB packed |          772.16 MiB packed |
| History rewrite       |                not performed |  pending explicit approval |

The source archive is within the requested 20 to 40 MB guideline. The Git object
database remains large because historical objects are still reachable.

## Removed from Git tracking

The following were removed with git rm --cached, so local files were not
physically deleted:

- .github/resources/, original RomM badges, logos, screenshots, and large
  preview GIF/WebP files.
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
- .codex/, .tmp/, and .github/resources/ local files.

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
- Historical original RomM preview GIF/WebP files and duplicate screenshots.
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
