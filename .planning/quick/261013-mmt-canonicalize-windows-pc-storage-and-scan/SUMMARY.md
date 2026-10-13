---
quick_task: 261013-mmt
description: Canonicalize Windows/PC storage and scan paths to win with safe pc compatibility
status: complete
commit: b2af59d73
---

# Summary

Implemented the Windows/PC filesystem slug contract with win as the canonical identity.

## Changes

- Added shared canonicalization and legacy fallback helpers.
- Made platform and ROM path builders prefer roms/win.
- Kept an existing roms/pc library usable only when roms/win is absent.
- Normalized selected and automatic scan platform slugs to win, with duplicate alias suppression.
- Updated legacy storage bootstrap to reuse the Windows platform identity instead of rewriting it to pc.
- Added path-builder regression tests.

## Verification

- Python compilation passed for all changed backend modules.
- Pure canonical/legacy path behavior check passed.
- git diff --check passed.
- Focused pytest was attempted in the Linux container but blocked before assertions because the fixture is hard-coded to 127.0.0.1:3306/information_schema; the Compose MariaDB service is network-only.
- Trunk was unavailable in the application container, so Trunk checks were not executable.
- Dev stack remained reachable with HTTP 200.

No external archive directory was renamed, copied, deleted, or rewritten. Fresh mappings use win; legacy pc is read/scan fallback only.
