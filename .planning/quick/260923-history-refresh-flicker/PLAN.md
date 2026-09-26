---
status: complete
---

# Download history refresh flicker

## Objective

Prevent an enhanced queue status change from replacing visible download rows
with the history loading spinner.

## Verification

- Regression test proves a queue status change does not request history again.
- Existing hydration tests remain green.
