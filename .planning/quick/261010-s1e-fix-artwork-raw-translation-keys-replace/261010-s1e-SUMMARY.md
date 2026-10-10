---
status: complete
commit: 407c6b45c
---

# Artwork upload labels

Added the missing rom.upload-artwork translations to every supported locale while preserving the existing ArtworkSubtab i18n calls and upload flow. English locales use Upload artwork; German uses Artwork hochladen. Added a focused regression assertion for all three component call sites and the English/German locale values.

Verification:

- Focused Vitest passed: src/v2/components/GameDetails/ArtworkSubtab.test.ts and src/locales/localeParity.test.ts — 2 files, 6 tests.
- Frontend typecheck passed: npm run typecheck.
- Custom locale coverage/order check passed for all 18 locale files.
- Changed-file diff check passed.
- Repository-wide locale parity/sort scripts still report pre-existing unrelated gaps/order issues in other keys/files; no unrelated locale cleanup was included.
- No deployment performed.
