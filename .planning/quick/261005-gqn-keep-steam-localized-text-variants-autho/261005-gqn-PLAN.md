---
quick_id: 261005-gqn
description: Keep Steam localized DLC text authoritative after an IGDB metadata selection, while preserving manual-text precedence.
---

# Plan

1. Start with a focused frontend regression in `frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts`. Make the mocked locale controllable per test, then prove that a DLC with `metadata_source: "igdb"`, retained Steam `text_variants` for German and English, and an IGDB summary renders the selected Steam locale text. In the same test surface, prove that `metadata_source: "manual"` still renders the operator-authored summary even when Steam variants exist. Run `cd frontend && npm run test -- PcDlcDetail` and confirm the new assertions fail before production code changes.

2. Update only the DLC detail summary wiring in `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`. Continue using `resolveSteamTextVariant`, but treat a retained Steam variant as authoritative for every non-manual component source, including `igdb`; reserve the legacy component summary for manual metadata and for the resolver's existing malformed or missing-variant fallback. Do not change scan matching, Steam enrichment/assignment, the stored fixture data, backend selection persistence, or parent-game display behavior. Follow the `frontend-v2-components` constitution: preserve the existing feature-composite SFC conventions, generated API types, strict typing, and no v1 changes. Re-run `cd frontend && npm run test -- PcDlcDetail steamTextVariants`, then `npm run typecheck`.
