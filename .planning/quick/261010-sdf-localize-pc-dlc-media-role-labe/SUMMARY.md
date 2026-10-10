---
status: complete
commit: d52bd8532
---

# Summary

Localized the PC DLC media role selector while preserving backend enum values.

- The selector now derives localized titles from the existing rom.pc-media-role-* translations.
- item-title="title" and item-value="value" keep the visible label separate from the selected enum.
- Filtering continues to compare item.role with the enum model.
- Uploads continue sending the original enum through the role form field.
- The default screenshot role and unrelated media behavior remain unchanged.

## Verification

- Focused Vitest suite passed: PcDlcMediaTab.test.ts — 6 tests.
- Frontend typecheck passed: npm run typecheck.
- No deployment performed.
