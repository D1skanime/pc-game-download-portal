---
phase: 27-reproduzierbare-portainer-docker-installation-f-r-die-romm-v
plan: 03
subsystem: deployment
tags: [portainer, documentation, uat, docker]
requires: [27-01, 27-02]
provides:
  - Public GitHub-to-Portainer installation guide
  - Recorded clean-install UAT for the sanitized stack
affects: []
tech-stack:
  added: []
  patterns: [Git-based Portainer stack, operator-owned secrets and bind paths]
key-files:
  created:
    [
      docs/PORTAINER_INSTALL.md,
      .planning/phases/27-reproduzierbare-portainer-docker-installation-f-r-die-romm-v/27-UAT.md,
    ]
  modified: [README.md, examples/README.md]
key-decisions:
  - "Document main as the source branch and keep ROMs, media, database contents, and secrets outside Git."
  - "Use container healthchecks as the authoritative infrastructure smoke evidence."
patterns-established:
  - "Operators provide only their own paths, secrets, and optional provider keys."
requirements-completed: [DEPLOY-27-04]
duration: 35 min
completed: 2026-10-11
---

# Plan 27-03 Summary

Published the GitHub-to-Portainer installation guide and linked it from the fork README. The guide documents the Git stack source, main branch, compose path, required bind paths, generated secrets, optional metadata credentials, health checks, updates, and the boundary that private ROM/media/database data never belongs in Git.

Recorded and passed a disposable clean-install UAT using synthetic values. The fork image built from the canonical Linux checkout, the database and application reached healthy state, the read-only library contract rendered correctly, optional provider keys remained blank, and the disposable project was removed after the run.

## Verification

- `bash scripts/verify-portainer-stack.sh` — passed.
- `docker compose ... config --quiet` — passed.
- `docker compose ... build --pull=false romm` — passed.
- Disposable database/application startup — passed.
- UAT record: `27-UAT.md`.

## Commits

- `ede51a10a` — `docs(27-03): publish Portainer installation guide`
