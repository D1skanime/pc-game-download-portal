---
phase: 04
slug: v2-storage-design-specification
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-11
completed: 2026-08-11
---

# Phase 04 - Validation Strategy

> Plan-aligned validation contract for the documentation-only UI-05 deliverable.

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | Shell documentation contract checks |
| Quick run | `test -f docs/design/v2-storage-administration.md && grep -q "Principles Provenance Matrix" docs/design/v2-storage-administration.md` |
| Full suite | Required sections, D-01 through D-21, disclosure, path, scope, and `git diff --check` gates |
| Runtime | Under 10 seconds |

## Sampling Rate

- After every task commit: narrow section checks and `git diff --check`.
- After Plan 04-02: complete automated matrix and manual semantic review.
- Before verification: repeat the full gate against the committed artifact.
- Stop on the first failing gate.

## Per-Task Verification Map

| Task ID | Requirement | Secure behavior | Automated evidence | Status |
|---|---|---|---|---|
| 04-01-T1 | UI-05 | Scope, route convergence, redacted backend contract, and overview | Scope, Backend Contract, route, `expected_version`, and prohibited-path checks | passed |
| 04-01-T2 | UI-05 | Exact flow ordering, explicit folder boundary, deep and bounded navigation | Guided Mapping Flow, Folder Browser, deep examples, descendant/sibling, and no-recursive-work checks | passed |
| 04-02-T1 | UI-05 | Complete local states, recovery, focus, input, responsive, and v2-system mapping | State Matrix, Universal Input, Responsive, breakpoint, modality, and Token and Primitive Matrix checks | passed |
| 04-02-T2 | UI-05 | Provenance, D-01 through D-21, acceptance, disclosure, and scope gates | Principles Provenance Matrix, Acceptance Checklist, traceability, no-copy, no-runtime, no-em-dash, and diff checks | passed |

## Automated Full Gate

```bash
set -e
f=docs/design/v2-storage-administration.md
for s in "Scope" "Backend Contract" "Guided Mapping Flow" "Folder Browser" "State Matrix" "Universal Input" "Responsive" "Principles Provenance Matrix" "Acceptance Checklist"; do grep -q "$s" "$f"; done
for n in $(seq -w 1 21); do grep -q "D-$n" "$f"; done
grep -q "UI-05" "$f"
grep -q "expected_version" "$f"
grep -q "pending.*partial.*complete" "$f"
grep -qi "at least" "$f"
grep -qi "no-copy" "$f"
! grep -nE '/home/|/volume[0-9]*/|/romm/library|container_path' "$f"
! LC_ALL=C grep -n $'\xE2\x80\x94' "$f"
git diff --check -- "$f" .planning/phases/04-v2-storage-design-specification/04-VALIDATION.md
```

The changed-path gate must show documentation only and must reject runtime UI, backend, generated model, dependency, deployment, and Phase 5 changes introduced by Phase 4.

## Manual Semantic Verification

| Behavior | Evidence reviewed | Result |
|---|---|---|
| RomM-native originality | Every provenance row contains abstract principle, original interpretation, tokens/primitives, and no-copy confirmation | passed |
| Backend fidelity and redaction | Root, health, browse, mapping, conflict, shallow preview, and queued preview fields and null/stale meanings match the live Linux contract | passed |
| Exact ordering | Fast safety test precedes explicit save; overview adopts persisted identity/version before queued preview; preview failure never rolls back save | passed |
| Universal input | Overview, flow, browser, overlays, conflict recovery, and preview changes trace mouse, touch, keyboard, and gamepad behavior | passed |
| Focus continuity | Local updates retain an anchor or move to the affected heading/recovery; overlay scope and Cancel behavior are explicit | passed |
| Responsive composition | xs through xl retain one drill-down model, use mount-gated chrome, full-bleed mobile overlays, 44px targets, and no raw layout media queries | passed |
| Deep subset behavior | Arbitrary-depth Unicode selection includes the chosen folder and descendants while excluding siblings | passed |
| Large-library behavior | Browse is paginated and cursor-bound with no size, recursive walk, scan, hash, or full preview before save | passed |

## Required Adversarial Matrix

- Unmapped, mapped, inactive, unreachable, unreadable, writable warning, unknown non-writability, forbidden, missing, and bounded error.
- Empty, paginated, Unicode, deep breadcrumbs, unsafe symlink, scan limit, and invalid cursor.
- Test failure, stale version, overlap, duplicate, save success, preview missing, pending, partial by time or entries, complete, stale, and bounded problems.
- Focus continuity on local updates, dialog cancel scope, and hidden mobile chrome excluded from navigation.
- No host path, container path, Team4s screenshot, asset, source, identity, branding, or dependency.

## Validation Sign-Off

- [x] UI-05 has automated documentation gates and manual semantic review.
- [x] D-01 through D-21 are objectively traceable.
- [x] Current Linux API contracts are the only field and state authority.
- [x] UI-01 is resolved in favor of D-08 without exposing a path.
- [x] No runtime UI, backend, generated model, dependency, deployment, or Phase 5 artifact was changed by Phase 4.
- [x] No em dash appears in the specification.
- [x] `nyquist_compliant: true` and `wave_0_complete: true`.

**Approval:** passed
