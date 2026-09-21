---
quick_id: 260921-haf
description: Enhanced FSA Download Timeout and Queue Recovery
---

# Plan

1. Add a configurable per-member timeout around the enhanced FSA open/write/read pipeline. Abort only the affected member when the timeout expires and classify the outcome as `failed` with a user-visible timeout code.
2. Ensure `runEnhancedItem` always settles its promise, records the failure event without blocking later queue windows, and preserves pause/cancel intent.
3. Add focused tests for a stalled writable/stream, timeout classification, and queue continuation; run Vitest and frontend typecheck.
