# Phase 5: Preview and Read-path Cutover - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 5-preview-and-read-path-cutover
**Areas discussed:** Bounded preview, Scan trigger consistency, Queued mapping identity, Content-read failures

---

## Bounded Preview

| Decision           | Alternatives considered                                                                                | Selected                                |
| ------------------ | ------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| Preview budget     | Combined time and entry budget; entry count only; time only; agent discretion                          | Combined time and entry budget          |
| Reported totals    | Observed lower bounds; extrapolated totals; sample only; agent discretion                              | Observed lower bounds                   |
| Unreadable entries | Continue and summarize; abort immediately; count only; agent discretion                                | Continue and summarize                  |
| Repeated previews  | Explicit refresh retaining stale result; automatic refresh on open; ephemeral result; agent discretion | Explicit refresh retaining stale result |

**User's choice:** Selected the recommended option for all four decisions.
**Notes:** Partial previews must not claim extrapolated totals or expose technical paths.

---

## Scan Trigger Consistency

| Decision               | Alternatives considered                                                                                | Selected                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------- |
| Trigger implementation | Shared pipeline; separate trigger-specific flows; watcher as hint only; agent discretion               | Shared pipeline                             |
| Watcher authority      | Acceleration without completeness guarantee; authoritative watcher; watcher disabled; agent discretion | Acceleration without completeness guarantee |
| Event bursts           | Debounce and coalesce; process every event; periodic evaluation; agent discretion                      | Debounce and coalesce                       |
| Unreachable mapping    | Fail and preserve catalog; automatic retries; treat as empty; agent discretion                         | Fail and preserve catalog                   |

**User's choice:** Selected the recommended option for all four decisions.
**Notes:** Scheduled and manual scans remain authoritative for NAS-backed mappings.

---

## Queued Mapping Identity

| Decision          | Alternatives considered                                                                   | Selected                             |
| ----------------- | ----------------------------------------------------------------------------------------- | ------------------------------------ |
| Captured identity | Mapping ID and revision; mapping ID only; absolute path snapshot; agent discretion        | Mapping ID and revision              |
| Validation timing | Before access and at safe boundaries; job start only; before every file; agent discretion | Before access and at safe boundaries |
| Stale mapping     | Fail visibly; redirect to new revision; await approval; agent discretion                  | Fail visibly                         |
| Retry behavior    | Create a new explicit job; reset the old job; create automatically; agent discretion      | Create a new explicit job            |

**User's choice:** Selected the recommended option for all four decisions.
**Notes:** Original jobs remain immutable and auditable; stale jobs never change targets.

---

## Content-read Failures

| Decision              | Alternatives considered                                                                       | Selected                      |
| --------------------- | --------------------------------------------------------------------------------------------- | ----------------------------- |
| Error classification  | Stable distinct domain errors; one unavailable error; raw filesystem errors; agent discretion | Stable distinct domain errors |
| Mid-transfer changes  | Abort; reopen at current offset; trust existing handle; agent discretion                      | Abort                         |
| Handoff authorization | Authorize before each handoff; trust catalog path; delegate to web server; agent discretion   | Authorize before each handoff |
| Multi-file download   | Preflight all required files; preflight first file only; full hash before download            | Preflight all required files  |

**User's choice:** Selected the recommended option for all four decisions.
**Notes:** The user asked what "preflight" means for one ISO versus a game split across 100 RAR parts. The clarified decision is one quick metadata/access preflight per required file, with no mandatory full read or rehash. Any required-file failure rejects the download before output begins.

---

## Agent's Discretion

- Exact numeric budgets, debounce periods, validation intervals, retention duration, diagnostic caps, error-code names, and internal organization.

## Deferred Ideas

None.
