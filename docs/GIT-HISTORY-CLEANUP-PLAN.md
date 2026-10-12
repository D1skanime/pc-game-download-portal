# Git History Cleanup and GitHub Migration Plan

## Status

Prepared only. No history rewrite and no force-push has been performed.

The current cleanup is isolated on branch codex/repository-cleanup. The final
migration requires explicit review and approval.

## Current ref inventory

The canonical checkout currently contains:

- 12 local branches.
- 5 remote-tracking refs under pc-romm.
- 217 local tags.
- 5 remote branches visible from pc-romm, including main and existing
  archive/codex branches.

Refresh the exact remote ref list immediately before migration. Do not change
branch protection or pull requests automatically.

## Historical paths to remove

Remove only paths proven to be local or obsolete:

- .codex/
- .tmp/
- .github/resources/
- .github/screenshots/ (historical upstream screenshots and previews)
- Docker/
- Games/
- RomM-phase*.zip
- config/databases/
- Historical backend/tasks/Metadata.zip

Preserve application source, migrations, workflows, issue/PR templates,
.planning documentation and state, own docs screenshots, frontend assets,
backend/frontend tests, database fixtures, and the explicitly maintained
archive fixtures under backend/tests/tasks/fixtures/ and tests/fixtures/.

No suffix-only deletion rule is allowed.

## Backup and restore

1. Announce a maintenance window and stop pushes to affected branches.
2. Fetch all refs with git fetch --prune --tags pc-romm.
3. Create a timestamped mirror backup outside the working checkout.
4. Export a bundle of every ref before filtering.
5. Record SHA-256 checksums for the mirror and bundle.
6. Verify that the backup can be cloned and that main, release refs, and the
   archive ref resolve.
7. Keep the backup read-only until migration acceptance.

Record the backup path and checksum in the final report, never credentials.

## Isolated rewrite

Use a fresh mirror clone, never the active development checkout:

```bash
git clone --mirror https://github.com/D1skanime/pc-romm.git pc-romm-history-cleanup.git
cd pc-romm-history-cleanup.git
git filter-repo --force \
  --path .codex/ \
  --path .tmp/ \
  --path .github/resources/ \
  --path Docker/ \
  --path Games/ \
  --path-glob 'RomM-phase*.zip' \
  --path config/databases/ \
  --path backend/tasks/Metadata.zip \
  --invert-paths
```

This is a proposal only. Run it first on a disposable copy and inspect
filter-repo ref handling before touching any approved mirror.

After filtering:

- Run git fsck --full --no-reflogs.
- Recompute largest blobs and source archive size.
- Confirm forbidden paths are unreachable in selected refs.
- Verify all required refs and tags resolve.
- Clone the filtered mirror into a new empty directory.
- Run the repository hygiene check from that clone.
- Run backend, frontend, build, and relevant tests.
- Compare commit chronology and merge topology for kept application history.

The filter must not rewrite refs outside the approved set. Tags and legacy
branches with meaningful releases require an explicit inclusion decision.

## Pull requests and local clones

Before force-push:

- List open pull requests and record their base/head refs.
- Mark each PR obsolete, to recreate, or to keep on an untouched ref.
- Notify collaborators that local clones must re-clone or reset after migration.
- Do not merge old pre-rewrite branches into the rewritten main.
- Recreate required PRs because commit hashes change.

## GitHub cutover

1. Present dry-run metrics, affected refs, backup checksum, and exact commands.
2. Obtain explicit approval for named refs and the force-push.
3. Confirm branch protection permits it without disabling protection.
4. Push rewritten main with lease protection where supported.
5. Push only explicitly approved release and development refs.
6. Push rewritten tags only after the tag list is approved.
7. Verify GitHub heads and tags against the rewritten mirror.
8. Document GitHub support/cache follow-up for unreachable objects.

## Rollback

If validation fails before cutover, discard the disposable mirror and restore
from the verified backup.

If cutover fails, stop pushes, restore original refs from the verified backup,
and report the exact remote state. Never mix old and rewritten histories.

## Acceptance gate

The rewrite is ready only when backup and checksum are verified, dry-run and
filtered-clone metrics are recorded, refs/tags/code/tests/fixtures pass, PR
effects are documented, and the user explicitly approves the named force-push.

## Review addendum evidence

The non-destructive preparation was completed on 2026-10-12 in the canonical
Linux checkout.

- The exact local and remote refs, tags, and GitHub pull-request ref were
  inventoried. PR #1 is merged; refs/pull/1/head is a GitHub-managed ref and
  is not included in ordinary branch deletion commands.
- A full remote mirror and an all-local-ref bundle were created under
  /home/d1sk/backups/pc-romm-history-cleanup-20261012T083849/.
- git bundle verify, restore-clone creation, and git fsck --full
  --no-reflogs completed. SHA-256 manifests are stored in SHA256SUMS.
- The rewrite was run only in the disposable mirror rewrite-dry-run.git. The
  tested --path-glob "RomM-phase*.zip" rule completed successfully.
- The candidate set includes .github/screenshots/ because an historical
  m_gallery.png remained reachable there even though the current cleanup
  already removed .github/resources/. This path is unreferenced by the
  current tree and is now covered by the hygiene rules.
- The filtered dry-run reduced the mirror object database from about 772 MiB
  to about 130 MiB. It removed the approved obsolete path classes while
  retaining the application tree and maintained fixtures.
- No GitHub ref was force-updated, deleted, or rewritten as part of this
  review work. The exact cutover commands remain proposals until approval.
