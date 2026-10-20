# Phase 34: Reliable fresh installation and scan lifecycle - Discussion Log

> Audit trail only. Planning, research and execution use 34-CONTEXT.md.

**Date:** 2026-10-18
**Areas discussed:** Setup recovery and completion; scan start and errors; recovery and cancellation.

The user selected all three areas and explicitly approved context creation.

## Setup recovery and completion

| Question | Selected | Alternative considered |
| --- | --- | --- |
| Partial setup after account creation | Resume incomplete step and preserve saved assignments | Show setup overview |
| Games root missing or unreadable | Keep error and Retry check in current step | Go to storage administration |
| Connection lost during assignment save | Reconcile saved server state and repeat missing steps | Manual status check |
| Successful setup transition | Completion screen with Start first scan | Navigate straight to scan view |

User confirmed proceeding to scan-start discussion.

## Scan start and errors

| Question | Selected | Alternative considered |
| --- | --- | --- |
| Startup presentation | Confirmed checking, queued and running states | Loading start button only |
| Missing acceptance acknowledgement | Bounded reconciliation and safe retry without duplicate work | Manual status check |
| Accepted job cannot execute | Persistent error in scan window with cause and next action | Blocking error dialog |
| Metadata provider failure | Continue readable games and retry affected metadata | Stop at first provider failure |

User confirmed proceeding to recovery discussion.

## Recovery and cancellation

| Question | Selected | Alternative considered |
| --- | --- | --- |
| Reload or later browser return | Automatically restore existing job and server status | Ask before showing ongoing scan |
| Browser disconnection | Continue server work and reconnect automatically | Pause scan |
| Server or worker restart | Automatically resume after unchanged-source/mapping verification | Require Resume on every interruption |
| Deliberate cancellation | Preserve results and await confirmed stop; manual Resume | Automatically resume on next opening |

User confirmed recovery was settled.

## Context approval

The user approved saving all decisions, including retaining PGDP UI, reusing
existing logic, avoiding hardcoded paths and UI text, and applying the 500-line
module limit with justified exceptions.

## Engineering discretion

Transport, persistence, bounded timeout values and retry implementation remain
for evidence-based research and planning. Early-click/disconnected-socket
causality remains unproven. The plan must investigate actual lifecycle and
submission behavior and include meaningful end-to-end failure tests.

## Deferred Ideas

No new feature was requested outside the stability phase. Game recognition
redesign remains outside its boundary. Phase 33 acceptance stays open.
