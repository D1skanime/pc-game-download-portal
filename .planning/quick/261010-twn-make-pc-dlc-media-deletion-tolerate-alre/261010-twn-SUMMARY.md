---
quick_id: 261010-twn
description: Make PC DLC media deletion tolerate already-missing owned files
status: complete
---

# Summary

Implemented the idempotent PC DLC media deletion fix in the canonical Linux checkout.

## Changes

- delete_component_media now treats FileNotFoundError from removing an already-missing owned file as successful cleanup.
- Database deletion remains authoritative and occurs before filesystem cleanup.
- Existing 404 behavior for unknown media, authorization, expected-version checks, placements, and success payload are unchanged.
- Added a regression test proving HTTP 200, media removal, and component updated_at advancement when the backing file is absent.

## Verification

- Focused regression and placement tests: 2 passed.
- Full endpoint file: 3 passed, 2 failed because of the pre-existing unrelated non-DLC masking test (200 instead of expected 404).
- git diff --check passed for the two changed source/test files.
- Repository Ruff command was unavailable in the configured uv environment.
- No deployment performed.
