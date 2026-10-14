---
quick_id: 261013-enhanced-folder-download
description: Keep enhanced folder downloads alive after directory selection
status: complete
mmit: f1ddefb38
---

# Summary

The enhanced folder download trusts the directory handle returned by the browser read/write picker instead of issuing a second permission request after the user gesture has ended. It also reuses that selected root permission for nested destination directories; asking each child directory for permission could reject with NotAllowedError and leave the file in a failed state. Startup failures from the picker, manifest request, or transfer setup are shown as a localized snackbar. Regression tests cover the root picker, nested directory writes, and picker failure handling.

Verification: focused queue and PC component tests passed (19/19); frontend typecheck passed; production build passed; runtime preflight confirmed the dev stack reachable with HTTP 200. Browser UAT still requires a manual completion of the native Windows folder picker.
