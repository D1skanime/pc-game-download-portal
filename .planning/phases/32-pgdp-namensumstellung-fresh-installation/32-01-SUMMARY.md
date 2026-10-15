---
phase: 32-pgdp-namensumstellung-fresh-installation
plan: 01
subsystem: deployment
tags: [pgdp, compose, mariadb, backend-config, fixtures, naming-inventory]
requires: []
provides:
  - Exact-path PGDP/RomM naming inventory with retained compatibility allowlist
  - PGDP-only Portainer operator wrapper translated to canonical DB_* and ROMM_* runtime keys
  - Fresh-install Compose, MariaDB parity, and isolated synthetic fixture contracts
affects: [32-02, 32-03]
tech-stack:
  added: []
  patterns:
    - PGDP operator inputs translate one-way to canonical DB_* and retained ROMM_* runtime keys.
    - Fresh-install deployment identity uses PGDP services, containers, volumes, and database bootstrap values.
    - Backend collection gates run through the project-provided romm-dev container with an overridden entrypoint.
key-files:
  created:
    - .planning/phases/32-pgdp-namensumstellung-fresh-installation/32-NAMING-INVENTORY.md
    - .planning/phases/32-pgdp-namensumstellung-fresh-installation/32-01-SUMMARY.md
  modified:
    - examples/portainer-stack.yml
    - examples/portainer.env.example
    - examples/docker-compose.example.yml
    - docker-compose.yml
    - docker-compose.override.yml
    - env.template
    - backend/config/__init__.py
    - backend/pytest.ini
    - backend/romm_test/setup.sql
    - backend/docker-compose.test.yml
    - backend/docker-compose.pc-integration-test.yml
    - backend/docker-compose.immutability-test.yml
    - backend/docker-compose.policy-test.yml
key-decisions:
  - PGDP is the sole product-owned operator wrapper surface; canonical DB_* and retained ROMM_* keys remain inside the application boundary.
  - Compatibility-owned /romm paths, /assets/romm wiring, schema/model identifiers, provider contracts, and upstream URLs remain unchanged.
  - Existing romm-dev service names remain in the local dev stack because the authorized collection gate invokes that service; fresh-install and fixture identities use PGDP.
requirements-completed: [PGDP-32-01]
duration: 11 min
completed: 2026-10-15
---

# Phase 32 Plan 01: PGDP Naming Inventory and Fresh-Install Contracts Summary

**PGDP fresh-install naming boundary with PGDP-only operator inputs, DB/MariaDB parity, retained RomM runtime compatibility, and isolated synthetic fixtures**

## Performance

- Duration: 11 min
- Started: 2026-10-15T09:44:43Z
- Completed: 2026-10-15T09:55:00Z
- Tasks: 2
- Files modified: 14 including inventory and summary

## Accomplishments

- Persisted the pre-mutation exact-path naming inventory with disposition counts, D-05 wrapper boundary, retained-name allowlist, and hard-stop rule.
- Aligned Portainer and generic Compose deployment identity to PGDP, with DB_HOST=pgdp-db, matching DB_NAME/MARIADB_DATABASE, matching DB_USER/MARIADB_USER, required secret interpolation, read-only library mount, writable owned mounts, health gating, and PGDP named volumes.
- Changed only fresh-install defaults in backend config and runtime template, and isolated backend tests with synthetic pgdp_test credentials and pgdp_test_db.
- Kept /romm, /assets/romm, canonical ROMM_* runtime keys, phase provenance labels, provider identifiers, and upstream contracts intact.

## Verification

- Inventory acceptance checks: passed.
- docker compose --env-file examples/portainer.env.example -f examples/portainer-stack.yml config: passed.
- docker compose -f backend/docker-compose.test.yml config: passed.
- Bounded fixture Compose rendering with synthetic PHASE9_*, PHASE10_*, and POLICY_* paths: passed.
- Container gate with docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/backend && uv run pytest tests --collect-only -q': passed, 4,056 tests collected.
- PGDP DB/MariaDB parity, PGDP-only wrapper scan, no-migration/old-volume scan, and git diff --check: passed.
- Generated backend/pgdp_test/ runtime output was removed after validation. No database, media, game, NAS, or existing volume was touched.

## Task Commits

1. Task 1: Freeze the rename boundary in an exact-path inventory - 42102ef69 (docs)
2. Task 2: Align fresh-install Compose, runtime config, and fixtures - c30c82521 (feat)

## Decisions Made

- Product-owned deployment identity is PGDP, while compatibility-owned runtime/path/schema/provider/upstream identifiers remain RomM-named.
- The existing local dev service name romm-dev is retained solely to preserve the plan's authorized containerized collection command; it does not change fresh-install PGDP identity.
- gsd-sdk was unavailable on the Linux host, so state and roadmap files were updated using the documented local-file fallback.

## Deviations from Plan

### Auto-fixed Issues

1. Rule 1 - Bug: Corrected generated interpolation and synthetic grant details.
   Found during Task 2. The first transformation left a malformed PGDP_CONFIG_PATH expression and a stale romm_test% SQL grant. Restored valid required Compose interpolation and changed the wildcard grant to pgdp_test%. Files: examples/portainer-stack.yml, backend/romm_test/setup.sql. Verification: Portainer Compose render and backend collection passed. Commit: c30c82521.

2. Rule 2 - Missing Critical: Added an isolated test volume.
   Found during Task 2. The bounded test Compose fixture had synthetic credentials but no explicitly named disposable database volume. Added pgdp_test_db to backend/docker-compose.test.yml. Verification: fixture Compose config passed. Commit: c30c82521.

3. Rule 3 - Blocking: Used the container gate explicit entrypoint override.
   Found during Task 2 verification. The documented romm-dev run first executed the dev entrypoint, started services, and failed DNS resolution for an unavailable Valkey dependency before reaching pytest. Re-ran the same authorized containerized uv/pytest gate with --entrypoint bash and --no-deps, without service startup. Verification: 4,056 tests collected in 10.11 seconds. Commit: c30c82521.

Total deviations: 3 auto-fixed (Rule 1: 1, Rule 2: 1, Rule 3: 1). Impact: All changes were directly required for correctness or for executing the prescribed container gate; no migration, live-volume adoption, or data movement was added.

## Issues Encountered

- gsd-sdk is not installed on team4s-linux; the documented local-file state/roadmap fallback was used.
- Host rg, uv, and Node tooling are unavailable as documented. Docker/Compose checks ran host-side, and the Python gate ran inside the project container.

## Authentication Gates

None.

## Known Stubs

None in files created or modified by this plan.

## Threat Flags

None. The new Compose and environment boundary is covered by the plan threat model T-32-01 through T-32-05.

## Next Phase Readiness

Plan 32-01 is complete and committed. Plan 32-02 can proceed with product branding, locales, assets, maintained documentation, and CI using the inventory allowlist. Plan 32-03 can consume the PGDP Compose parity and fixture contracts for static verifiers and clean-stack proof.

---
Phase: 32-pgdp-namensumstellung-fresh-installation
Completed: 2026-10-15

## Self-Check: PASSED

- FOUND: 32-NAMING-INVENTORY.md
- FOUND: 32-01-SUMMARY.md
- FOUND: task commit 42102ef69
- FOUND: task commit c30c82521
