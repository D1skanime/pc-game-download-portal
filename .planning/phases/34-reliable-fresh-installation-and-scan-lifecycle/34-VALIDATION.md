---
phase: 34
slug: reliable-fresh-installation-and-scan-lifecycle
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-18
---
# Phase 34 Validation Strategy

## Test Infrastructure
- Backend: pytest and pytest-asyncio, existing backend/tests/conftest.py.
- Frontend: Vitest and Vue Test Utils, frontend/vitest.config.ts.
- Integration: Playwright plus disposable production-like Compose/Portainer stack.
- Baseline quick command: docker exec pgdp-dev sh -lc 'cd /app/frontend && npm run test -- --run src/v2/views/Scan.test.ts src/v2/data/operations.test.ts'
- Backend commands must use an explicit isolated test database/network, never the
  application DB. Plan 34-01 must supply exact reproducible test harness commands
  and database-target guard before any destructive fixture runs.

## Sampling Rate
Run meaningful affected behavior tests after each task. Run the complete phase
regression suite after each wave. Before acceptance require frontend typecheck,
build, locale parity, focused backend/API/worker tests and end-to-end fault suite.
Use bounded waits/fake timers; report unavailable infrastructure as blocked.

## Per-Task Verification Map
Planner must expand this map to exact plan/task IDs and commands before approval.

| Behavior | Decisions | Test type | Expected proof | Status |
| --- | --- | --- | --- | --- |
| Scope disposal and remount | D-05, D-09, D-10 | Vue lifecycle | One active subscription set after remount | pending |
| Accepted start and replay | D-05, D-06 | Backend concurrent/API | One operation/job for repeated request; bounded acknowledgement recovery | pending |
| Worker status and failure | D-07 | Worker integration | Queued/running/failure projected from server | pending |
| Setup partial-save recovery | D-01, D-02, D-03, D-04 | API + browser | Same admin and saved assignments; completion CTA | pending |
| Metadata partial failure | D-08 | Provider/worker + browser | Remaining games indexed, failed items identifiable and retryable | pending |
| Reload, reconnect and restart | D-09, D-10, D-11 | Worker/browser faults | Same job restored; checked continuation without duplicates | pending |
| Deliberate cancellation | D-12 | Race/worker/browser | Stop confirmed; results kept; no automatic restart | pending |
| Source/mapping identity and auth | D-11, D-16 | Negative integration | Changed/unsafe scope and unauthorized access fail closed | pending |
| Existing UI/locales and module size | D-13, D-14, D-15 | Static + browser | Existing tokens/components, parity, coherent modules <=500 lines | pending |
| Fresh stack through first scan | D-01 through D-16 | Production-like + browser | Source unchanged, real games indexed, Phase 33 acceptance evidence | pending |

## Wave 0 Requirements
- [ ] Isolated database and Redis fixtures with fail-closed target validation.
- [ ] Deterministic provider stubs and read-only game fixtures.
- [ ] Real component lifecycle and network fault tests.
- [ ] Exact new test paths and commands reconciled against final plan tasks.

## Manual-Only Verifications
Final shared in-app browser walkthrough: fresh setup, first completed scan,
retained PGDP visual language, both themes and supported input modalities.
Automation must cover transport loss and server/worker fault injection.

## Validation Sign-Off
- [ ] Every task has executable verification or prior harness dependency.
- [ ] No three consecutive tasks without automated behavior verification.
- [ ] Missing fixture/test files have explicit creation tasks.
- [ ] No watch-mode commands.
- [ ] Full phase coverage matches final plans.
- [ ] Approval after evidence, not by document creation.
