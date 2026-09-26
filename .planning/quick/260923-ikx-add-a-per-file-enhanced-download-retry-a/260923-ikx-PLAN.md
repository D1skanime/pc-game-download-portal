---
quick_id: 260923-ikx
description: Add a per-file enhanced-download retry action
---

# Plan

1. Expose a retry action only for a failed enhanced-download member that is no longer active, so a terminal partial session can recover one file without requeueing verified members.
2. Reuse the existing member-scoped enhanced resume flow, which requires a newly selected destination and starts a fresh transfer session for the failed manifest member.
3. Add a focused component test, typecheck, production build, and a real Chromium File System Access retry verification.
