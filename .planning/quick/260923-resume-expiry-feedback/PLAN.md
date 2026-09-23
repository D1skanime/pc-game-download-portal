---
status: complete
---

# Resume expiry feedback

## Objective

Keep an existing enhanced transfer session intact until its manifest is proven
available, and explain an expired manifest after the user selected a folder.

## Verification

- Focused composable and component tests pass.
- Frontend typecheck passes.
- Live 3344 UI confirms an individual terminal-history deletion returns 204 and
  removes its row.
