---
quick_id: 261013-q04
status: executed
---

# Fix scan serialization so identified ROM cover downloads are never skipped

## Goal

Ensure scan progress serialization failures cannot abort ROM processing before cover and media persistence.

## Tasks

1. Add a non-fatal scan-progress emit helper that catches presentation/serialization errors.
2. Route all scan-progress ROM events through the helper.
3. Eager-load PC component owned-media placements for the simple ROM schema.
4. Add a regression test for serialization failure isolation.
5. Verify with focused tests, compilation, diff checks, and a live Windows scan.

## Verification

- Focused regression tests pass.
- Backend module compiles.
- Live Windows scan completes and writes cover files for all seven test ROMs.
