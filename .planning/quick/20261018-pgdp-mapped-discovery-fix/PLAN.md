---
name: pgdp-mapped-discovery-fix
status: complete
created: 2026-10-18
---

# PGDP mapped discovery fix

Stop the active PGDP scan flow and startup library probe from invoking legacy
filesystem discovery that assumes a `roms` directory below the mounted Games
root.

## Acceptance criteria

- The v2 scan view does not request legacy filesystem discovery after mapping readiness.
- Heartbeat and setup library discovery do not bootstrap or require a legacy `roms` directory when no legacy structure is detected.
- Existing legacy Structure A/B behavior remains available when detected.
- The dev service returns successfully and emits no missing-`roms` error for the PGDP flat root.

## Decomposition review

No new production file is required. The focused compatibility guard belongs at
the existing heartbeat/setup boundary, while the scan view removes a redundant
legacy request. Existing large files are changed only at those narrow seams.

## Verification

- Frontend scan regression tests.
- Backend syntax compilation.
- Browser reload and recent-container-log check against the live dev stack.
