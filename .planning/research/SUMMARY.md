# Project Research Summary

**Project:** RomM PC Library
**Domain:** NAS-first immutable external game-library management
**Researched:** 2026-08-04
**Confidence:** HIGH for roadmap structure, MEDIUM for production NAS details

## Executive Summary

RomM PC Library is a brownfield, v2-only RomM fork that indexes an existing NAS archive without changing its files, directories, or organization. Keep the current Python 3.13, FastAPI, SQLAlchemy, Redis/RQ, Vue 3, TypeScript, and generated OpenAPI modular monolith. Add a narrow storage-domain boundary between every consumer and filesystem I/O. Milestone 1 is secure NAS integration only. PC components, manifests, resumable transfers, the Windows downloader, writable/import storage, and broad visual redesign remain deferred.

Represent one deployment-defined root, permanently `external_read_only`, and map platforms only to normalized relative POSIX paths. A typed resolver canonicalizes and contains every path, rejects traversal and symlink escape, and invokes a central operation policy. Allow list, stat, read, hash, stream, and download. Reject create, upload, write, overwrite, rename, move, copy, delete, extract, patch, and mkdir before filesystem access. Docker `:ro` is defense in depth, never application authorization. All RomM-owned database state, assets, cache, temporary files, hashes, and audit records stay outside the archive.

The largest risks are distributed mutation bypasses, inherited handlers that create directories, path races, previews with hidden side effects, source deletion hidden inside catalog actions, fixed-layout assumptions in workers, and premature v1 deletion. Mitigate them with a sink-based mutation inventory, a non-mutating source adapter, real-filesystem adversarial tests, shared pure discovery for preview and scan, catalog-only removal, staged v1 deletion, and synthetic-to-disposable-to-real rollout. Team4s remains a read-only design reference only. Derive principles, never copy code, assets, branding, or implementation.

## Key Decisions

- Retain the existing stack and add no runtime framework or broad filesystem abstraction.
- First milestone is NAS integration only. Remove v1 in a separate bounded workstream.
- Support only immutable `external_read_only` roots, with no writable toggle.
- Store no host or absolute container paths in mappings.
- Keep `Platform.fs_slug` for metadata and compatibility, not storage mapping.
- Route browser, preview, scan, hash, stream, download, jobs, watchers, and redirects through one resolver and policy.
- Separate source storage structurally from RomM-owned writable storage.
- Make game and mapping removal catalog/configuration-only. Source deletion is unsupported.
- Keep `Rom` and `RomFile` unchanged in milestone 1.
- Treat Team4s as a read-only principles reference and native Vue v2 as the implementation system.
- Do not expose the real NAS until policy and container evidence pass on disposable fixtures.

## Key Findings

### Recommended Stack

Use Python/FastAPI/Pydantic for policy, paths, protected APIs, and OpenAPI; SQLAlchemy/Alembic for portable root, mapping, and append-only audit persistence; Redis/RQ for existing jobs only; Vue 3/TypeScript/Vite/Pinia/Vue Router/Vuetify and v2 `R*` primitives for the sole UI; pytest/Hypothesis/Vitest/Storybook/Playwright/Docker for evidence. No new runtime package is recommended.

### Must-Have Features

- One opaque immutable root and zero or one active relative mapping per platform.
- Canonical containment with path-dialect, traversal, symlink, and race-aware checks.
- Admin-only v2 folder browser, mapping test, bounded non-mutating preview, and audit.
- Mapping-aware read-only scan, hash, stream, play, and download.
- Central denial of source mutations across APIs, sockets, jobs, watchers, migrations, and helpers.
- Catalog-only removal and non-cascading mapping removal.
- Proposal-first legacy Structure A/B bridge with no source writes.
- V2-only routing after staged removal of toggle, named views, fallback, dispatchers, and frozen v1 trees.
- Cross-dialect, concurrency, restart, container, traversal, symlink, API-bypass, and before/after evidence.
- Deployment, migration, security, troubleshooting, and atime guidance.

### Differentiators and Deferrals

Differentiators are defense-in-depth immutability, organization-preserving mappings, preview-before-index using the execution discovery engine, explainable safety states, audited changes, evidence-backed migration, and focused native v2 administration.

Defer PC base/update/DLC/hotfix/extras modeling, manifests and revisions, resumable transfers, Windows downloader, writable external roots, file-manager actions, import into the archive, per-platform mounts, dynamic ZIP redesign, installation planning, and complete v2 redesign.

### Architecture

Add an immutable root/health model; platform mapping plus transactional append-only audit; sole typed path resolver; operation policy; non-mutating source adapter; owned-storage boundary; shared discovery with separate preview and execution effects; narrow FastAPI APIs; and native v2 administration. Mapping removal never cascades to source, platform, or catalog. Migrations are additive and source-safe across MariaDB/MySQL/PostgreSQL.

### Critical Risks

1. **Mount or UI treated as authorization:** deny operations in application policy on writable fixtures, then test `:ro` separately.
2. **Internal bypasses and mutating constructors:** inventory sinks and use a source adapter that cannot mkdir or expose mutation methods.
3. **Traversal, symlinks, and TOCTOU:** reject all dialect escapes, require canonical containment, test real links, and prototype descriptor-relative no-follow reads.
4. **False dry-run:** pure discovery must avoid DB, queue, cache, resource, socket, audit, and provider side effects.
5. **Catalog/source conflation:** remove destructive request shapes and carry storage ownership in typed paths.
6. **Fixed-layout leftovers:** migrate manual, scheduled, socket, watcher, content, and redirect paths to mappings.
7. **Unavailable mistaken for empty:** explicit health states fail closed and preserve catalog data.
8. **Premature v1 deletion:** prove route parity and import reachability, then delete in verified batches.
9. **Unsafe rollout:** align schema, workers, queues, backend, contracts, frontend, and mount activation without touching Team4s.

## Dependencies and Recommended Sequencing

```text
root schema -> resolver -> policy/source adapter -> mapping/audit
-> browser/validation -> shared preview/discovery -> all read paths
-> lifecycle/migration -> release proof -> real NAS
```

The v1-removal workstream can be planned in parallel but code changes and verification remain isolated. Team4s inspection stays read-only throughout.

## Implications for Roadmap

### Phase 1: Immutable Storage Foundation

**Rationale:** All consumers depend on stable root identity and path semantics.
**Delivers:** Additive root/mapping/audit schema, immutable invariants, health states, normalized paths, resolver, adversarial unit tests.
**Avoids:** Generic CRUD, host-path leakage, `fs_slug` overload, cross-dialect failure.

### Phase 2: Policy and Read-Only Adapter

**Rationale:** Prove the boundary before exposing source paths.
**Delivers:** Central policy, non-mutating adapter, mutation inventory/gating, owned-storage separation, writable-fixture and `:ro` tests.
**Avoids:** `EROFS` authorization, constructor mkdir, alternate bypasses.

### Phase 3: Mapping Administration

**Rationale:** Stable schema, resolver, and policy must precede APIs.
**Delivers:** Protected mapping CRUD, conflict/concurrency rules, audit, relative browser, authoritative mapping test, generated contracts.
**Avoids:** Arbitrary path oracle, absolute leakage, unaudited drift.

### Phase 4: Preview and Read-Path Cutover

**Rationale:** Preview and execution require one discovery engine, and mappings must replace layout inference everywhere.
**Delivers:** Pure bounded preview; mapping-aware scan, jobs, watcher, hash, stream, play, download, and redirects; mapping version semantics; fail-closed health.
**Avoids:** Hidden side effects, parser drift, stale jobs, outage-driven cleanup.

### Phase 5: Safe Lifecycle and Legacy Bridge

**Rationale:** Migration and removal are safe only after policy and mapping cutover.
**Delivers:** Catalog-only removal, explicit mapping disposition, proposal-first bridge, ambiguity handling, portable upgrade/downgrade and restart tests.
**Avoids:** Source deletion, cascades, restructuring, silent conversion.

### Phase 6: V2 UI and Bounded V1 Removal

**Rationale:** Land native v2 workflows, then remove v1 only after parity.
**Delivers:** Root/mapping/browser/preview/audit UI using generated types and v2 primitives; principle-only Team4s influence; route/import inventory; v2 rewiring; staged v1 deletion.
**Avoids:** Copied Team4s code, inaccessible UI, broken deep links, hidden v1 dependencies.

### Phase 7: Operational Proof and NAS Enablement

**Rationale:** Production data is last.
**Delivers:** Full bypass matrix, comprehensive before/after manifests, container proof, docs, worker/queue/schema/frontend preflight, approved real-NAS rollout.
**Avoids:** Premature exposure, hash-only proof, atime overclaims, stale jobs, Team4s disruption.

## Research Flags

Needs focused research:
- Phase 1: descriptor-relative Linux no-follow access and residual long-read TOCTOU risk.
- Phase 3: mapping overlap policy. Default is reject equal, ancestor, and descendant overlap.
- Phase 4: actual NAS watcher fidelity. Scheduled/manual scans remain authoritative.
- Phase 5: catalog disposition after mapping changes and legacy ambiguity rules.
- Phase 7: NAS protocol, permissions, stale handles, timeouts, atime, and rollout window.

Standard repository patterns, usually skip separate research:
- Phase 2: backend, policy, pytest, and Docker patterns are well documented.
- Phase 6: v2 primitives, i18n, input, Storybook, and routing guidance are established.

## Confidence Assessment

| Area | Confidence | Notes |
|---|---|---|
| Stack | HIGH | Verified in the canonical repository; no new runtime dependency needed. |
| Features | HIGH | Directly grounded in PROJECT.md and current capabilities. |
| Architecture | HIGH | Boundaries and seams are observed in current code. |
| Pitfalls | HIGH | Risks map to concrete handlers, endpoints, jobs, watcher, cleanup, and router code. |
| Race hardening | MEDIUM | Needs Linux and production-mount prototyping. |
| Operations | MEDIUM | NAS protocol, permissions, watcher, atime, and rollout timing are unconfirmed. |

## Open Questions

- Reject all symlinks, or allow verified in-root leaf links? Default: reject all in milestone 1.
- Can mappings overlap? Default: no.
- Is root registration deployment-only? Default: yes.
- What mapping snapshot/version does a queued scan retain?
- Does mapping removal retain indexed records? Default: yes, until separate catalog-only cleanup.
- What are preview delta rules for moves, renames, and missing items? Reuse scanner reconciliation.
- What audit retention/export policy is required?
- Can nginx satisfy the verified DB-id path contract?
- Which NAS protocol/options are used, and what safe deployment window avoids active Team4s encoding?

## Sources

Primary: `.planning/PROJECT.md`, `STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `CLAUDE.md`, codebase maps, and concrete files cited by the four research reports.

Secondary: production NAS behavior and Linux descriptor-relative race hardening, pending focused validation.

### Safety Boundary

The external library is immutable. External roots are `external_read_only` only. Milestone 1 is NAS integration only. V1 is removed in a bounded, separately verified workstream. Team4s is a read-only design reference and is never modified, copied, restarted, or made a build/runtime dependency. No Team4s service, source file, or active encode workload is changed.

---
*Research completed: 2026-08-04*
*Ready for roadmap: yes*
