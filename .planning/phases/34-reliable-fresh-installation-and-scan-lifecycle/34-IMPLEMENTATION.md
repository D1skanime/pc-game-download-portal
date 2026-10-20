# Phase 34 Implementation Handoff

The complete primary code implementation is assembled. Phase acceptance remains open for the shared live UAT and the unavailable production Portainer gate. Independent deep code review is deferred until after UAT by the user's explicit instruction.

## Connected behavior

A scan command commits one durable SQL operation before enqueueing its deterministic RQ job. REST submission, startup reconciliation, watcher and scheduled entry points reuse the same scanner. Worker attempts enforce leases, cancellation and fenced catalog/media writes. Internal progress updates no longer invalidate command versions. Fatal per-ROM errors propagate to the durable failure result instead of being logged as successful completion.

Per-game provider outcomes preserve readable indexed games when metadata is temporarily unavailable. The deterministic provider tests exercise actual catch paths, authentication failures and no-match semantics. Retry selects failed targets without replacing unrelated successful provider/media results.

Setup recovery preserves completed assignments through login and reload. The active v2 scan UI reconciles authoritative operations, restores a lost acceptance response, distinguishes confirmed progress from a pending request and supports explicit cancellation/recovery actions. Leaving the page does not cancel a scan. All 18 locale contracts are maintained.

Owned media and stable exports use prepared capabilities, fresh content proof at the final authority boundary, a process writer domain with async task ownership and a minimal-environment read-only child. Uncertain cleanup evidence is retained. nginx denies the reserved staging namespace and exact private sibling temporary pattern, while committed resource URLs retain normal HTTP behavior.

## Verification scope

See [34-ACCEPTANCE.md](34-ACCEPTANCE.md) for receipts and current gate results. Technical evidence includes full MariaDB/PostgreSQL media suites, current focused process/fence hardening, real SQL/RQ worker cases, actual browser setup through eight-platform completion and production-image HTTP requests during streaming, after process death and after nginx restart.

The production-image HTTP receipt predates the final task-owner and child-environment hardening. Its scope is the unchanged serving boundary. The later hardening has separate current runtime tests on both database dialects. Live Dev uses the verified canonical backend/frontend bind mounts and therefore includes the current implementation.

A source without authoritative immutable generation evidence cannot be safely adopted by an interrupted attempt. Recovery deliberately blocks with a concrete remediation action; it does not silently treat names, sizes or timestamps as proof. The frozen plan 34-16 experiment remains INCONCLUSIVE and is not relabeled.

## Preserved work and operations

Task-related preexisting media drafts and the previously necessary setup platform-option bound are integrated without discarding their content. Unrelated preexisting Phase 33 UAT/validation edits, Compose edits and prototype/test directories remain outside the implementation commits. Games remains read-only. There is no further DB/media reset, production deployment, push or automatic following phase.

## Commits

- f53839847: owned media publication and recovery.
- 6b39d042b: durable dispatch, worker, recovery and provider diagnostics.
- e4b0aafed: guarded integration and private-media HTTP evidence tooling.

- 1c24cdf2e: setup recovery, authoritative frontend state, all locales and browser scenarios.
- 6572d3c0f: bounded complete static-check batches.
- d89f14aa5: existing v2 adapter boundaries and provider-preferences extraction.
- 78204e35a: host HOME propagation required by the isolated lint CLI.

Final quality and live-UAT bookkeeping is recorded in the acceptance record.
