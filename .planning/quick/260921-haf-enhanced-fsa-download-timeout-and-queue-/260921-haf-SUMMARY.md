---
quick_id: 260921-haf
description: Enhanced FSA Download Timeout and Queue Recovery
status: complete
commit: 5d9dfb11ef4f
---

# Summary

Enhanced queue members now have a bounded 30-second operation timeout. A stalled FSA writable/stream operation aborts its own member, records `enhanced_download_timeout` as a failed transfer outcome, and settles the member promise so later queue windows can continue. Existing pause/cancel handling remains intact.

Verification: focused queue tests passed (4/4); frontend typecheck passed.
