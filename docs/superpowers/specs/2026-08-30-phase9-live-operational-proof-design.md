# Phase 9 Live Operational Proof Design

## Goal

Replace Phase 9's synthetic operational-immutability evidence with a bounded,
repeatable proof run against an isolated Compose stack. The run must capture
real source manifests around real supported workflows, real nginx and worker
evidence, and real browser evidence from the existing v2 surfaces.

## Scope and Safety Boundary

The proof uses only a fresh copy of the repository fixture. It starts only
Compose resources that carry both Phase 9 ownership labels, binds the fixture
at `/romm/library` read-only, and keeps all RomM-owned paths on labeled
writable volumes. It must never access a NAS mount, Team4s paths, Team4s
containers, or active encode workloads.

## Architecture

`verify_operational_immutability.py` is the sole proof orchestrator. For each
run it creates a unique Compose project and artifact root, validates the
topology, starts the labeled stack, waits for nginx, seeds the isolated
database, runs the required actions, captures logs, and tears down only that
project with volumes.

Every workflow uses the same sequence:

1. Capture and persist a manifest of the mounted fixture.
2. Execute an action against the isolated app, queue, or nginx endpoint.
3. Capture a second manifest and require an unchanged comparison.
4. Persist action-specific, non-synthetic witnesses in that workflow's result
   envelope.

The harness owns the aggregate envelope. The browser suite owns one
`browser.json` per browser-covered workflow. The aggregate gate validates
both before it can report success.

## Real Witnesses

Worker workflows must record a job identifier obtained from the actual queue
or task result, plus matching worker-log evidence collected from the live
Compose project. Delivery workflows must record the actual request URL,
response statuses, relevant response headers, and nginx-log evidence. A
restart workflow must restart only the isolated application service and
re-query persisted state afterwards.

No helper may fabricate a marker, HTTP status, queue state, service log, or
restart outcome. Witness data is accepted only when it can be traced to an
executed command, HTTP response, database query, queue result, or captured
service log from the run's Compose project.

## Browser Contract

The harness invokes Playwright with the dynamically resolved nginx base URL,
a single worker, and the run artifact directory. Browser artifacts are
mandatory for each browser-covered workflow and must contain the run ID,
workflow slug, actual final URL under that nginx base URL, status, and timing.
Skipped tests and missing artifacts fail the aggregate run.

The Playwright cases remain on existing v2 routes. They perform the supported
workflow operation or make an explicit authenticated request to the same
isolated API boundary, then record the observed response or visible outcome.
They do not add a proof-only route or return to v1.

## Failure Handling and Cleanup

The harness records failed run state, available service logs, and cleanup
evidence in the artifact root before propagating the original error. Cleanup
uses the explicit Compose project name and checks ownership labels before
removing resources. No broad Docker prune or host-path cleanup is permitted.

## Testing

Unit tests first reject synthetic witnesses, missing run-bound browser
artifacts, unrelated base URLs, and unlabeled cleanup targets. Integration
tests then run a narrow live workflow against the isolated stack and assert
that it emitted real response, worker, or log evidence as applicable. A full
Phase 9 run must demonstrate every workflow envelope, unchanged manifests,
and required browser artifacts.

## Acceptance Criteria

- `--all` starts and stops a unique Phase 9 Compose project and captures live
  service logs.
- Every claimed workflow action occurs between its persisted manifests.
- nginx, worker, and restart witnesses contain live, run-bound evidence.
- Browser evidence is executed and validated as part of `--all`.
- The final verifier can mark TEST-04, TEST-05, and TEST-06 satisfied without
  touching Team4s or a real NAS.
