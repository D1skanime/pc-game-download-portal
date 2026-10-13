---
quick_id: 261013-enhanced-folder-download
description: Keep enhanced folder downloads alive after directory selection
status: complete
commit: 20ba994ca
---

# Summary

The enhanced folder download now trusts the directory handle returned by the browser.s read/write picker instead of issuing a second permission request after the user gesture has ended. That redundant request could reject with `NotAllowedError`, causing the dialog to close without creating a manifest or transfer. Startup failures from the picker, manifest request, or transfer setup are now caught and shown as a localized snackbar instead of appearing as no-op behavior. Regression tests cover both the permission-gate scenario and picker failure handling.

Verification: focused queue and PC component tests passed (18/18); frontend typecheck passed; production build passed; runtime preflight confirmed the dev stack reachable with HTTP 200. Browser UAT still requires a manual completion of the native Windows folder picker.
