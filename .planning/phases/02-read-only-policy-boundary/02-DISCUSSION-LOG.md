# Phase 2: Read-only Policy Boundary - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-08-09
**Phase:** 2-read-only-policy-boundary
**Areas discussed:** Operation Model, Mixed Workflows and Destinations, Denial Contract, Enforcement Coverage

---

## Operation Model

| Decision             | Options considered                                                                              | Selected                    |
| -------------------- | ----------------------------------------------------------------------------------------------- | --------------------------- |
| Granularity          | Fine-grained capabilities; read/write; grouped capabilities                                     | Fine-grained capabilities   |
| Unknown operations   | Always deny; inherit group policy; deny only for external roots                                 | Always deny                 |
| Minimum policy input | Operation and storage class; operation and root ID; operation, source, destination, and purpose | Operation and storage class |
| External allowlist   | Explicit named reads; any operation tagged non-mutating; caller-specific allowlists             | Explicit named reads        |

**User's choice:** Selected the recommended closed, fine-grained model for all four decisions.
**Notes:** The allowlist covers list, stat, read, scan, hash, stream, download, and safe resolution. Unknown operations fail closed.

---

## Mixed Workflows and Destinations

| Decision                  | Options considered                                                                                   | Selected                      |
| ------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------- |
| Read plus write workflow  | Authorize source and destination separately; authorize whole workflow once; check only external read | Authorize separately          |
| Generated output location | Explicit RomM-owned class; anywhere outside root; system temp only                                   | Explicit RomM-owned class     |
| Copy semantics            | Separate read and write; always forbid; broadly allow copying out                                    | Separate read and write       |
| Transformations           | External source as input only; memory only; block entirely                                           | External source as input only |

**User's choice:** Selected the recommended source/destination separation for all four decisions.
**Notes:** No output may be created beside external content. In-place transformations and write-back are forbidden.

---

## Denial Contract

| Decision                  | Options considered                                                  | Selected              |
| ------------------------- | ------------------------------------------------------------------- | --------------------- |
| Internal error            | Typed policy error; reuse filesystem errors; caller-specific errors | Typed policy error    |
| API status                | HTTP 403; HTTP 409; HTTP 400                                        | HTTP 403              |
| Jobs and internal callers | Fail visibly; skip step; redirect automatically                     | Fail visibly          |
| Exposed detail            | Safe identifiers only; include relative path; generic message only  | Safe identifiers only |

**User's choice:** Selected the recommended typed, visible, minimally disclosing denial contract for all four decisions.
**Notes:** No silent fallback is permitted. Absolute and relative paths remain hidden.

---

## Enforcement Coverage

| Decision          | Options considered                                                                   | Selected                          |
| ----------------- | ------------------------------------------------------------------------------------ | --------------------------------- |
| Enforcement point | Lowest common filesystem boundary; each domain handler; outer entry points only      | Lowest common filesystem boundary |
| Authorized result | Operation-bound capability; absolute path; relative path plus root ID                | Operation-bound capability        |
| Legacy paths      | Complete blocking inventory; secure only known consumers; runtime warnings           | Complete blocking inventory       |
| Proof             | Writable and read-only fixtures plus tripwires; manifests only; read-only mount only | Fixtures plus tripwires           |

**User's choice:** Selected the recommended structurally enforced approach for all four decisions.
**Notes:** Unclassified mutation paths block phase completion. Tests must prove denial before any target filesystem access.

## Agent's Discretion

- Concrete symbol names, module layout, capability implementation, stable error-code spelling, and test-file organization.

## Deferred Ideas

None.
