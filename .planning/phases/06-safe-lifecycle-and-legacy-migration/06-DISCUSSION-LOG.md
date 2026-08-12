# Phase 6: Safe Lifecycle and Legacy Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-08-12
**Phase:** 6-safe-lifecycle-and-legacy-migration
**Areas discussed:** Mapping removal, Legacy library detection, Migration confirmation and rollback, Conflicts and edge cases

---

## Mapping Removal

| Decision               | Options considered                                     | Selected                                    |
| ---------------------- | ------------------------------------------------------ | ------------------------------------------- |
| Catalog state          | Keep visible/unreachable; hide; delete catalog records | Keep visible and unreachable                |
| Active and queued work | Abort safely; let finish; choose per removal           | Abort at next safe boundary                 |
| Later mapping          | Reconnect automatically; preview/confirm; treat as new | Reconnect unambiguous matches automatically |
| Confirmation           | Normal confirmation; typed platform name; none         | Clear normal confirmation                   |

**Notes:** Metadata, saves, history, and catalog identity remain. Source content is never changed.

---

## Legacy Library Detection

| Decision            | Options considered                                         | Selected                                 |
| ------------------- | ---------------------------------------------------------- | ---------------------------------------- |
| Trigger             | Explicit command; once after upgrade; every startup        | Explicit administrator command only      |
| Search scope        | Known standard paths; whole library; selected start folder | Exact canonical standard paths only      |
| Result detail       | Compact safe summary; full file list; minimal identity     | Compact safe summary                     |
| Unusable candidates | Show/block; still propose; hide                            | Show bounded problem and block selection |
| Similar names       | Exact canonical folder; historical aliases                 | Exact canonical folder only              |

**Notes:** The user requested an example for multiple old folders. After clarification, names such as `ps3_old` are explicitly ignored instead of being treated as candidates.

---

## Migration Confirmation and Rollback

| Decision          | Options considered                                    | Selected                        |
| ----------------- | ----------------------------------------------------- | ------------------------------- |
| Mutation scope    | Database/config only; reorganize files; mapping only  | Database and configuration only |
| Preview           | Per-platform impact; mapping only; technical row list | Per-platform impact summary     |
| Confirmation unit | Per platform; all together; both                      | Each platform separately        |
| Rollback window   | Until first productive use; time-limited; permanent   | Until first productive use      |

**Notes:** Rollback affects only RomM-owned state. Migration never changes source files.

---

## Conflicts and Edge Cases

| Decision                   | Options considered                                      | Selected                    |
| -------------------------- | ------------------------------------------------------- | --------------------------- |
| Existing active mapping    | Block; replace automatically; ignore legacy             | Block migration             |
| Overlapping mapping ranges | Block; allow nested; resize existing                    | Block migration             |
| Unmatched catalog entries  | Keep unreachable; block platform; delete                | Keep unreachable            |
| Failure during migration   | Full rollback; save partial progress; interrupted state | Full transactional rollback |

**Notes:** The user requested concrete Game Boy/PlayStation examples before confirming the conflict rules. RomM never merges or automatically rewrites sources.

## the agent's Discretion

- Exact canonical legacy-path table based on verified historical RomM behavior.
- Bounded preview budgets and background execution mechanism.
- Unambiguous catalog matching algorithm and internal rollback representation.

## Deferred Ideas

None.
