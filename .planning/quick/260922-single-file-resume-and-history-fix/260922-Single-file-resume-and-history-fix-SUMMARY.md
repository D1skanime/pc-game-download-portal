---
quick_id: 260922-single-file-resume-and-history-fix
description: Fix single-file resume, duplicate history rows, and long-list controls
status: complete
commit: 5b787b838
---

# Summary

Resume now creates a new enhanced transfer session containing only the requested manifest member. Repeated attempts are collapsed to the newest file row, empty session rows are hidden, and session/history controls remain visible in the scrollable panel. An authenticated Chromium UAT reproduced the old whole-session restart, verified the backend subset response (`selected_items: 1`), and confirmed the revised layout.

Verification: DownloadTransferHistory/Accessibility tests passed (17/17), frontend typecheck passed, and backend Python compilation passed.
