---
status: complete
commit: pending
---

# Summary

## Completed

- Added a typed `steam_url_cover` field for PC metadata candidates.
- Provider-source rendering now labels Steam media with the Steam logo instead of the IGDB logo.
- Added a regression test for Steam cover attribution.
- Kept DLC safety conservative: IGDB establishes the local DLC/expansion relationship; Steam only enriches a validated identity.

## Verification

- `vue-tsc --noEmit` passed in the Linux dev container.
- Focused Vitest test passed (`types.test.ts`, 1 test).
- Dev service restarted and the live Steam-only candidate search returned two Steam candidates with covers.

## DLC decision

Users do not enter Steam IDs during normal operation. Steam App-ID entry remains an optional expert fallback only. A Steam search result that is a soundtrack, bundle, or unrelated product must never be attached to a local DLC component.
