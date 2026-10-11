---
phase: 27-reproduzierbare-portainer-docker-installation-f-r-die-romm-v
plan: 01
subsystem: deployment
tags: [portainer, docker-compose, secrets, deployment]
requires: []
provides:
  - Sanitized Git-based Portainer stack and operator env contract
  - Deterministic compose and secret-safety verification script
affects: [27-02, 27-03]
tech-stack:
  added: []
  patterns:
    [operator-supplied bind paths, named state volumes, read-only library mount]
key-files:
  created:
    [
      examples/portainer-stack.yml,
      examples/portainer.env.example,
      scripts/verify-portainer-stack.sh,
    ]
  modified: [examples/README.md]
key-decisions:
  - "Build the fork source from the Git stack context so main is the deployed code."
  - "Keep ROM/library/media/database contents and credentials outside Git."
patterns-established:
  - "Portainer fills paths, secrets, and optional provider keys through environment variables."
requirements-completed: [DEPLOY-27-01, DEPLOY-27-02]
duration: 45 min
completed: 2026-10-11
---

# Plan 27-01 Summary

Implemented the portable Portainer deployment contract using the existing RomM container architecture. The stack parameterizes paths, image, port, timezone, database credentials, auth secret, and optional provider credentials while retaining the read-only library boundary and named managed-state volumes.

Added deterministic verification that renders the compose file, checks health/dependency/mount semantics, rejects developer-specific paths, and prevents runtime media or secrets from entering the tracked repository. Removed the accidentally tracked runtime MP3 from the Git index while preserving local runtime data.

## Verification

- bash scripts/verify-portainer-stack.sh — passed.
- Compose rendering with the sanitized env template — passed.
- Secret/path safety assertions — passed.

## Commits

- cb4728650 — feat(27-01): add portable Portainer stack contract
- bfa7b66a7 — chore(27-01): exclude runtime media from repository
