---
phase: 08-bounded-v1-removal
verified: 2026-08-27T07:34:00Z
status: passed
score: 4/4 success criteria verified
requirements: [V2-01, V2-02, V2-03, V2-04, V2-05]
human_verification: deferred-to-phase-09
gaps: []
---

# Phase 8: Bounded V1 Removal Verification Report

## Goal Achievement

| #   | Roadmap truth                                                                           | Status   | Evidence                                                                                                                                                                                                                                       |
| --- | --------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Users enter v2 directly with no UI preference, switch, named view, or fallback handoff. | VERIFIED | `RomM.vue` and all v2 layouts use the default router view. Startup removes the obsolete preference key. The selector, `NotReady`, fallback registry, and persisted test-data field are absent.                                                 |
| 2   | Every supported route renders v2 or has an explicit outcome.                            | VERIFIED | The route inventory classifies every `ROUTES` value. Router-record tests verify real default components or redirects, including parameter-preserving console redirects and the retired April Fools outcome.                                    |
| 3   | Required v2 boot dependencies pass a dedicated regression suite.                        | VERIFIED | The boot test proves import loaders for auth, pairing, theme-owning layouts, router, stores, API services, generated types, dialogs, and notifications. Nine focused tests and the required typecheck pass.                                    |
| 4   | Frozen source and compatibility paths are absent.                                       | VERIFIED | All tracked `src/components`, `src/views`, `src/layouts`, and `src/console` files were deleted. The console store, UI-version composable, obsolete console locale namespace, and v1-only test were removed. Filesystem and import guards pass. |

**Score:** 4/4 success criteria verified.

## Requirements Coverage

| Requirement | Status    | Evidence                                                                                                  |
| ----------- | --------- | --------------------------------------------------------------------------------------------------------- |
| V2-01       | SATISFIED | One unconditional v2 boot path and no runtime UI switch.                                                  |
| V2-02       | SATISFIED | Frozen v1 source trees and compatibility artifacts are deleted.                                           |
| V2-03       | SATISFIED | Shared types and EmulatorJS runtime dependencies are v2-owned; boot graph and typecheck pass.             |
| V2-04       | SATISFIED | Explicit route inventory and installed route outcome tests pass.                                          |
| V2-05       | SATISFIED | Focused static regression gate covers routes, boot dependencies, deleted paths, locales, lint, and types. |

## Automated Evidence

- Focused Vitest: 3 files, 9 tests passed.
- Frontend typecheck with `NODE_OPTIONS=--max-old-space-size=8192`: passed.
- Focused Trunk check for the route regression files: passed.
- Locale parity and sorted-key checks: passed.
- `git diff --check`: passed.

## Human Verification

Browser, live NAS, deployment, and service validation were explicitly deferred to Phase 9. Phase 8 requires only the bounded static cutover gate, so this deferral is not a Phase 8 gap.

## Gaps Summary

No Phase 8 implementation gaps remain.
