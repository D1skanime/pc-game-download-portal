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
