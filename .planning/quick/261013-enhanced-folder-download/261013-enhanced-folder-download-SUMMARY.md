---
quick_id: 261013-enhanced-folder-download
description: Keep enhanced folder downloads alive after directory selection
status: complete
commit: 20ba994ca
---

# Summary

The enhanced folder download now trusts the directory handle returned by the browser's read/write picker instead of issuing a second permission request after the user gesture has ended. That redundant request could reject with `NotAllowedError`, causing the dialog to close without creating a manifest or transfer. A regression test covers the failing permission-gate scenario.

Verification: focused queue and PC component tests passed (17/17); frontend typecheck passed; production build passed; runtime preflight confirmed the dev stack reachable with HTTP 200.
