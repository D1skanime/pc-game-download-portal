---
status: complete
---

# Summary

Removed the remaining legacy filesystem discovery calls from the active PGDP
scan path and guarded setup/heartbeat discovery when the mounted library has no
legacy RomM structure.

## Verification

- Frontend focused tests: 17 passed.
- Backend syntax compilation: passed.
- Dev service: HTTP 200 on `/scan` after restart.
- Live browser reload: `/api/heartbeat` and `/api/setup/library` returned 200.
- Recent container logs: no `roms`, `MissingStorageTarget`, or `StoragePolicyDenied` errors.
- Full backend endpoint tests remain blocked by the test fixture database being unavailable on `127.0.0.1:3306` inside the container.
