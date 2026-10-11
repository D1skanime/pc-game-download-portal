---
quick_id: 261011-fix-igdb-dlc-cover-fallback
status: complete
---

# Quick Task Summary: Preserve IGDB DLC fallback covers

## Result

When an IGDB DLC/expansion match is hydrated without a cover, the existing
cover supplied by the parent ROM metadata is now retained. A regression test
covers this exact path and verifies that the candidate still exposes the cover
media while hydrated fields are preserved.

## Verification

- python -m compileall -q handler/metadata/pc_match_handler.py tests/handler/metadata/test_pc_match_handler.py passed in the Linux development container.
- git diff --check passed.
- The focused pytest test was attempted, but the repository fixture failed before assertions because the container could not connect to its configured test database at 127.0.0.1:3306.

## Files

- backend/handler/metadata/pc_match_handler.py
- backend/tests/handler/metadata/test_pc_match_handler.py
