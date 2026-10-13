---
quick_id: 261013-enhanced-folder-download
description: Keep enhanced folder downloads alive after directory selection
---

# Plan

1. Reproduce the enhanced folder download failure after the browser folder picker returns.
2. Remove the redundant root permission request that can reject after the user gesture has ended.
3. Add a regression test for a selected directory whose second permission request would fail; run focused tests, typecheck, build, and browser verification.
