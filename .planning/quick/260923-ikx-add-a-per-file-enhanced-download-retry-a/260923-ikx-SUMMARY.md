---
quick_id: 260923-ikx
description: Add a per-file enhanced-download retry action
status: complete
commit: d7b7246e9
---

# Summary

Failed enhanced-download members in terminal partial sessions now show a member-scoped `Resume download` action. It reuses the existing secure enhanced resume path, asks the user to choose the permitted destination again, and creates a fresh transfer session for only that manifest member. Verified members remain untouched.

Verification: focused component test passed (9/9), frontend typecheck passed, production build passed, and Chromium File System Access UAT retried `a-woman-s-lot.part13.zip` from 0 bytes to verified checksum equality. The full frontend suite retains two pre-existing source-mutation inventory failures outside this change. The underlying timeout scenario remains separately recorded as a failed member, not a false success.
