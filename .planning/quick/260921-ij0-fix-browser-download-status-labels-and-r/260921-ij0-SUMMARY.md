---
quick_id: 260921-ij0
description: Fix browser download status labels and row actions after failed UAT
status: complete
commit: a65bc399624c
---

# Summary

Terminal history rows now expose deletion only when the owning session is terminal; active/queued/paused rows expose cancellation instead. The bulk-delete action is hidden when no terminal history exists, and German `verified` status is rendered as `Abgeschlossen`. Focused DownloadManager/History tests (7/7) and frontend typecheck pass.
