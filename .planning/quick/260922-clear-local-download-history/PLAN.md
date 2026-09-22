---
title: Clear local terminal download rows with server history
type: quick
status: complete
---

# Clear Local Terminal Download Rows with Server History

Keep the enhanced browser queue and persisted transfer history consistent after the user removes all completed download entries. Preserve active, paused, and transferring entries.

## Verification

- Reproduce the stale-row condition in Chromium after a successful server delete.
- Add a component test for the server-clear to local-queue clear boundary.
- Verify a 40-file enhanced DLC transfer disappears immediately after using the clear-all action.
