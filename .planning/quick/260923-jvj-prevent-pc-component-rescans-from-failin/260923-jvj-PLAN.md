---
quick_id: 260923-jvj
description: Prevent PC component rescans from failing when immutable download manifests reference removed source members
---

# Plan

1. Reproduce the foreign-key failure created when a scan deletes a PC component member still referenced by an immutable download manifest.
2. Retain a referenced missing member as source-unavailable instead of deleting it, exclude it from component responses and new manifest selection, and preserve it for fail-closed historical validation.
3. Add a portable migration, focused regression test, static checks, and an isolated live MariaDB plus Chromium rescan verification.
