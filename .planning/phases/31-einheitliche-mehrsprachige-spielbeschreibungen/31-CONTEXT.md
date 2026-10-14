# Phase 31 Context

## Goal

Preserve provider-supplied descriptions per locale for ROMs, expose them through the existing response metadata, and resolve the active UI locale without mutating Rom.summary or triggering a scan.

## Constraints

- Reuse manual_description.py and Steam text_variants.
- Do not add a translation table or automatic translation.
- Keep Rom.summary as a legacy fallback.
- ScreenScraper may persist only synopsis values it actually returns.
- Keep PC and console detail resolution on the same frontend resolver.
