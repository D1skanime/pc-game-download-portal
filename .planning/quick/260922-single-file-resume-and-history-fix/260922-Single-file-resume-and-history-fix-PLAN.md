---
quick_id: 260922-single-file-resume-and-history-fix
description: Fix single-file resume, duplicate history rows, and long-list controls
---

# Plan

1. Allow a transfer session to be created for a validated subset of manifest members.
2. Pass the selected member through the enhanced resume flow so one failed ZIP resumes alone.
3. Collapse repeated attempts to the newest file row, remove empty rows, and keep controls visible while scrolling.
4. Verify with focused frontend tests, typecheck, authenticated API checks, and Chromium UI inspection.
