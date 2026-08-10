# Phase 3: Mapping Administration Contracts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 03-mapping-administration-contracts
**Areas discussed:** Root status and directory browser, Mapping lifecycle, Conflicts and concurrency, Audit contract

---

## Root Status and Directory Browser

Selected: live read-only health checks on retrieval; stable cursor pagination; minimal name/relative-path/navigability entries; stable safe error codes and bounded messages.

Rejected: stored-only or background-only status, unbounded/truncated listings, child counts/size/timestamps, and detailed filesystem diagnostics.

## Mapping Lifecycle

Selected: separate test and save operations; preserve catalog on mapping changes and require explicit rescan; remove mapping only; typed missing-mapping conflict without fallback.

Rejected: test-and-save coupling, automatic catalog deletion/archive behavior, blocking changes when catalog entries exist, HTTP 404, and empty-success responses.

## Conflicts and Concurrency

Selected: optimistic concurrency; path-safe conflict identifiers; active mappings only participate in overlap checks; HTTP 409 with stable code/current version and no automatic retry.

Rejected: last-write-wins, editing locks, disclosure of conflicting paths, inactive-path reservation, HTTP 422, and server-side command replay.

## Audit Contract

Selected: audit durable mapping changes only; old/new root ID, relative path, version and active status; immutable user ID plus display-name snapshot; administrator-only cursor history newest first with safe filters.

Rejected: auditing tests/browse/status reads, mapping-ID-only records, display-name-only identity, and database-only or per-mapping-only history.

## the agent's Discretion

Exact naming, cursor encoding, version representation, schema/module layout, and error-code spelling remain open within the locked contracts.

## Deferred Ideas

None.
