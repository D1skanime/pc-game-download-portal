---
title: DLC download UAT and selection UI clarity
type: quick
status: complete
---

# DLC Download UAT and Selection UI Clarity

Validate removal controls and a complete enhanced DLC transfer in Chromium. Keep component selection compact while retaining individual file selection, and remove duplicate global transfer actions that conflict with row actions.

## Verification

- Remove one terminal entry and verify it remains absent after reload.
- Remove all terminal entries and verify the empty history after reload.
- Run the 40-file enhanced DLC fixture through Chromium's File System Access API test seam.
- Run focused frontend tests, typecheck, production build, and visual browser inspection.
