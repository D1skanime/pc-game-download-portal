# Phase 34 UI Behavior Contract

Source: 34-01-PLAN.md ui_behavior_contract. Locked decisions D-01 through D-16
remain authoritative. This artifact declares downstream behavior; it does not
claim that the runtime implements or passes these obligations yet.

## Authoritative contract

This section is the Phase 34 UI behavior contract and plan input artifact because no Phase 34 UI-SPEC exists. Implementation preserves PGDP v2 RAlert/RBtn/RForm/RProgressLinear, semantic tokens, existing navigation and responsive/input composables. Do not introduce a new visual system.
Setup: server-confirmed enrollment, saved assignments and root health determine the step. Anonymous post-enrollment users log in before resumption. Preserve saved assignments; uncertain saves reconcile. Show persistent root failure with localized cause and Retry check. Completion shows a separate Start first scan CTA; finishing setup never submits a scan.
Scan: local checking-start disables repeated action; accepted/queued/running/stopping/cancelled/interrupted/recovering/blocked/failed/completed/completed-with-warnings labels project versioned server snapshots. Disconnect/reconciling is orthogonal. Show no determinate 0/0 running fiction. Acceptance request timeout is 10 seconds, followed by same-key lookup with a 30-second reconciliation budget; exhaustion retains request identity and persistent Retry status action, never blind resubmission. Poll one awaited request every 2 seconds while active, 5-second timeout and backoff capped at 10 seconds during outages. Socket reconnect triggers immediate snapshot refresh; stale versions/attempts cannot regress the display. Timers/subscriptions dispose with their owner and reinstall exactly once.
Persistent inline causes and next actions accompany unavailable-worker, blocked-source/mapping, failure and warning states. Stop means stopping until confirmed; closing the window or disconnecting never cancels. Cancelled work requires explicit Resume. Metadata warnings list affected games/providers and target only failed items on retry. Auth/permission denial offers login or permitted navigation without leaking another user's operation.
Translate setup.json/scan.json keys into every existing locale. Keep field errors in place, critical operation errors inline plus canonical snackbar where appropriate. Mouse, touch, keyboard and gamepad work in both themes from 320px through 4K; live status uses accessible announcements without moving focus. Tests exercise mounted UI, events, timers and server counts, not source strings.

## State and action obligations

| Situation | Confirmed presentation | Allowed action |
| --- | --- | --- |
| Administrator enrolled, setup incomplete | Login before recovery, retained assignments | Resume missing steps |
| Games root unavailable | Persistent localized cause at the affected step | Retry check |
| Assignment response uncertain | Reconcile server state with existing identity | Repeat missing work only |
| Setup complete | Explicit completion screen | Start first scan separately |
| Submission pending or uncertain | Checking start, then same-key reconciliation | Disable repeat submission, retain Retry status |
| Accepted, queued or running | Versioned server state, meaningful progress | Observe or request Stop |
| Connection lost | Disconnected/reconciling alongside operation state | Reconnect and refresh, zero cancellation |
| Stop requested | Stopping until server confirmation | Observe, retain committed results |
| Intentionally cancelled | Confirmed cancellation | Explicit Resume only |
| Restarted worker or server | Recovering only after source/mapping proof and fencing | Resume once or show blocked cause |
| Metadata failures | Completed with affected game/provider warnings | Retry failed metadata only |
| Auth or permission denial | Login or permitted navigation, masked foreign operation | No unauthorized command or enumeration |

## Ownership and timing obligations

- One shared Socket.IO client, Axios/CSRF client, scanner and storage resolver.
- Snapshot versions and attempts fence stale replies and callbacks.
- One awaited poll at a time: 2 seconds active, 5-second timeout, outage backoff
  capped at 10 seconds. Reconnect refreshes immediately.
- Acceptance timeout is 10 seconds. Same-key reconciliation lasts 30 seconds;
  exhaustion retains identity and offers persistent Retry status.
- Owners release timers, observers and debounced callbacks on disposal.
  Remount installs exactly one listener set. Concurrent owners retain one set
  until the final owner leaves.
- Closing a view or browser never cancels server execution.

## Localization and accessibility obligations

- Keep PGDP v2 primitives, semantic tokens, navigation, input and responsive
  composables. Use RAlert, RBtn, RForm and RProgressLinear.
- Translate setup.json and scan.json recovery text across all eighteen locales.
  Field errors stay in place, critical causes remain inline, and significant
  errors also use the canonical snackbar.
- Verify mouse, touch, keyboard and gamepad in both themes from 320px to 4K.
- Announce live status accessibly without moving focus or trapping navigation.
- Tests mount UI, dispatch events, advance timers and assert server command
  counts. Source-string assertions cannot prove lifecycle or recovery behavior.

## Evidence and boundaries

34-01 reproduces source defects with real Vue scope disposal and real RQ callable
identity. It does not establish the live 0/0 incident's route or root cause.
34-03 owns job recognition repair; 34-11 owns listener/status repair.
34-08 must trace setup-to-AppLayout in the actual browser and retain production
worker/Portainer evidence before recommending Phase 33 acceptance closure.
Games remain read-only and all generated outputs remain application-owned.
