# Phase 9: Operational Immutability Proof - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the final user directives.

**Date:** 2026-08-27
**Phase:** 09-operational-immutability-proof
**Areas discussed:** Todo scope, production-like proof stack, manifest evidence, browser end-to-end coverage, operator documentation, Team4s safeguards

---

## Todo Scope

| Option                              | Description                                                                                          | Selected |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------- | -------- |
| Fold immutability todo into Phase 9 | Include the pending external-library immutability proof and documentation obligations in this phase. | ✓        |

**User's choice:** Fold the immutability todo into Phase 9.
**Notes:** The matching todo is `.planning/todos/pending/2026-08-04-enforce-external-library-read-only.md`.

---

## Production-like Proof Stack

| Option                                | Description                                                                                                              | Selected |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------- |
| Isolated production-like Docker stack | Use a read-only fixture library, application, worker, nginx, database/queue dependencies, and separate writable storage. | ✓        |

**User's choice:** Require the isolated production-like Docker stack.
**Notes:** No deployment, real NAS access, host-service restart, or Team4s change is authorized.

---

## Manifest Evidence

| Option                                       | Description                                                                                                    | Selected |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | -------- |
| Complete per-workflow before/after manifests | Record paths, exact names, structure, sizes, hashes, and timestamps before and after every supported workflow. | ✓        |

**User's choice:** Require complete before/after manifests for every supported workflow.
**Notes:** Evidence must be exact and machine-verifiable. `noatime` or an equivalent is required when proving access-time invariance.

---

## Browser End-to-end Coverage

| Option                      | Description                                                                                                        | Selected |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------- |
| Full browser workflow proof | Cover mapping, scanning, streaming, downloading, migration, and catalog removal through the production-like stack. | ✓        |

**User's choice:** Require browser end-to-end coverage for all named workflows.
**Notes:** The context also carries forward Phase 8's deferred v2 browser smoke scope and includes mapping removal, hashing, metadata matching, restart persistence, and related Phase 9 requirements.

---

## Operator Documentation

| Option                  | Description                                                                                                                       | Selected |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| Complete operator guide | Document deployment, maintenance window, `:ro`, separate writable storage, `noatime`, workflows, troubleshooting, and safeguards. | ✓        |

**User's choice:** Write a complete operator guide with the full safety checklist and guidance.
**Notes:** The guide must clearly separate application policy from mount-level defense and prohibit unsafe real-NAS activity outside explicit authorization.

---

## Team4s Safeguards

| Option               | Description                                                                                                                   | Selected |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------- |
| Explicit prohibition | Do not change Team4s source, configuration, services, host state, active encode workload, paths, mounts, containers, or data. | ✓        |

**User's choice:** Make Team4s safeguards explicit and binding.
**Notes:** Phase 9 uses synthetic or repository-controlled fixtures only.

## the agent's Discretion

- Exact fixture contents and manifest serialization.
- Docker project naming and CI artifact packaging.
- Playwright spec grouping and operator-guide filename.

## Deferred Ideas

None.
