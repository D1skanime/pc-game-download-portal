---
title: Clear local terminal download rows with server history
status: complete
date: 2026-09-22
commit: 7de7744c3
---

# Result

The server endpoint already removed persisted terminal sessions. The visible stale rows came from the in-memory enhanced browser queue. After a successful clear-all request, DownloadManager now emits the exact terminal member IDs and PcComponents removes only those entries from the local queue.

## Evidence

- Chromium on port 3344 reproduced 40 verified rows without a server-history delete button, then showed zero rows after the fixed clear-all action without a reload.
- A follow-up local-session reset prevents a deleted session from being fetched again and avoids a false failure alert (`f81367e08`).
- Chromium final state: zero rows, no empty-history warning, and no error alert.
- Focused frontend tests: 21 passed.
- `npm run typecheck` and `npm run build` passed.
