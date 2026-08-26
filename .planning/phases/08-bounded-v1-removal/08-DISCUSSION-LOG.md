# Phase 8: Bounded V1 Removal - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md.

**Date:** 2026-08-26
**Phase:** 08-bounded-v1-removal
**Areas discussed:** Removal scope, route inventory, preference cleanup, regression depth

---

## Removal Scope

| Option            | Description                                        | Selected |
| ----------------- | -------------------------------------------------- | -------- |
| Independent waves | Keep each deletion wave compilable and reviewable. | ✓        |
| Single deletion   | Remove all v1 source in one change.                |          |

**User's choice:** Independent waves, focused check after each wave, physical removal of v1 source, and migration of v2-required dependencies to neutral paths.

## Route Inventory

| Option             | Description                                 | Selected |
| ------------------ | ------------------------------------------- | -------- |
| Explicit inventory | Classify v2 views, redirects, and removals. | ✓        |
| Implicit fallback  | Leave unmatched routes to generic behavior. |          |

**User's choice:** Keep an explicit inventory, redirect legacy routes to functional v2 equivalents, and remove `NotReady`.

## Preference Cleanup

| Option                  | Description                                                          | Selected |
| ----------------------- | -------------------------------------------------------------------- | -------- |
| Silent targeted cleanup | Remove only v1 preference data while preserving neutral preferences. | ✓        |
| User notice or reset    | Show a notice or reset all UI state.                                 |          |

**User's choice:** Silently remove frontend and backend v1 UI-mode data, preserve neutral settings, and provide no fallback flag.

## Regression Depth

| Option                    | Description                                                  | Selected |
| ------------------------- | ------------------------------------------------------------ | -------- |
| Targeted automated checks | Route inventory, mocked v2 boot/import suite, and typecheck. | ✓        |
| Browser smoke now         | Add live browser checks in this phase.                       |          |

**User's choice:** Use targeted automated checks and defer browser smoke testing to Phase 9. Fix regressions before the next deletion wave.

## the agent's Discretion

Deletion-wave boundaries, neutral module locations, route equivalence mapping, and focused test details.

## Deferred Ideas

- Phase 9 owns browser smoke validation.
