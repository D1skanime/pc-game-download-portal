---
quick_id: 261013-q04
status: complete
commit: 6ffc7429e
---

# Summary

The scan progress Socket.IO serialization path is now non-fatal. Detached/lazy SQLAlchemy or Pydantic errors are logged and skipped so ROM processing continues into cover/manual/media persistence. Simple ROM hydration now eagerly loads PC component-owned media placements.

Verification:

- Focused scan regression tests: 2 passed, 1 existing SQLAlchemy warning.
- Backend modules compiled successfully.
- git diff --check passed.
- Live fresh Windows scan completed: 7/7 ROMs and 7/7 covers visible in the Windows platform view.
- Dev stack: HTTP 200.
