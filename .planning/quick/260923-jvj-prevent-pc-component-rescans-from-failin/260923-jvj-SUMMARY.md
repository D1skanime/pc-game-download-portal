---
quick_id: 260923-jvj
description: Prevent PC component rescans from failing when immutable download manifests reference removed source members
status: complete
commit: b05fd4cce
---

# Summary

PC component members referenced by an immutable download manifest are now retained with `missing_from_fs=true` when they disappear during a rescan. They are excluded from PC component responses and from every new manifest selection, while the existing immutable manifest can fail closed against the missing source rather than blocking the scan.

Verification: file-scoped Trunk check passed. The isolated 3344 MariaDB migration reached revision `0125`; a full Windows test-platform scan completed without the former foreign-key error. Chromium showed `Cyberpunk2077-test-2GB.iso` and omitted the removed 30-GB entry. The focused pytest suite is blocked by the checkout's fixed `127.0.0.1:3306` test configuration even from the UAT app container.
