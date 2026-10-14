---
name: fix-enhanced-folder-picker
status: complete
---

# Summary

The enhanced folder download no longer silently exits when the browser cannot return a writable directory handle. Missing picker support now raises an explicit error, and picker cancellation or unavailability is mapped to the localized folder-access message so users can retry the folder selection or use the standard browser download.

## Verification

- Focused frontend tests: 20/20 passed.
- Frontend typecheck: passed.
- Production build: passed; existing lightningcss, eval, and chunk-size warnings remain.
- Backend tests: not run; this was a frontend-only change.
- Dev stack: HTTP 200 at http://127.0.0.1:3100/.
