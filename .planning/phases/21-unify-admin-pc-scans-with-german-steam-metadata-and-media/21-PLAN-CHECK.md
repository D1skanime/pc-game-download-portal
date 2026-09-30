# Phase 21 Plan Check

**Checked:** 2026-09-30
**Verdict:** Revision required
**Plans checked:** 21-01 through 21-04

## Goal-backward result

The four plans cover the intended backend seams: one pure Steam patch boundary,
provider-owned media reconciliation, scan orchestration, and focused pytest
coverage. The dependency graph is acyclic and correctly ordered:
`21-01` and `21-02` are Wave 1, `21-03` depends on `21-02`, and `21-04`
depends on `21-01` and `21-03`.

However, execution as written cannot safely satisfy all locked decisions. Two
blocking planning defects must be corrected before execution, followed by the
high-severity gaps below.

## Coverage summary

| Required truth                                                        | Planned coverage        | Assessment                                                              |
| --------------------------------------------------------------------- | ----------------------- | ----------------------------------------------------------------------- |
| Shared ID-first, German-first, same-ID text patch                     | 21-01, 21-04            | Covered                                                                 |
| New, update, and complete eligible PC scan parity                     | 21-04                   | Covered in intent                                                       |
| Manual text and provider-authority protection                         | 21-01                   | Covered in intent                                                       |
| Provider-owned Steam catalog, upload safety, unclaimed-only placement | 21-02, 21-03, 21-04     | Covered in intent, but idempotent owned-storage lifecycle is incomplete |
| Failure isolation and excluded scan gates                             | 21-01, 21-03, 21-04     | Covered in intent                                                       |
| Existing Media UI remains the review surface                          | 21-04                   | Covered                                                                 |
| Isolated Witcher browser UAT and source-library proof                 | Verification prose only | Not executable or recordable                                            |

## Findings

### BLOCKER: 21-02 overwrites an existing Alembic migration filename

`21-02-PLAN.md` names
`backend/alembic/versions/0130_steam_scan_owned_media_state.py`. The canonical
checkout already contains `0130_local_background_audio.py`, with a later
`0131_owned_background_audio.py`. Creating the planned path would overwrite an
unrelated migration, while setting its revision below the current head would
also create a broken graph.

**Repair:** Change the plan artifact and task to a new unique migration, for
example `0132_steam_scan_owned_media_state.py`, with a unique revision and
`down_revision = "0131_owned_background_audio"` (or whatever is the verified
head at execution time). Require upgrade and downgrade coverage against both
supported database dialects.

### BLOCKER: Nyquist validation artifact is absent

Nyquist validation is enabled for this phase, the research contains a
`Validation Architecture` section, and no `21-VALIDATION.md` exists. The plans
therefore have no phase-level evidence matrix for the new tests, migration
gate, source immutability test, or deferred browser evidence. This fails the
required validation-artifact gate before task-level automated-check sampling is
considered.

**Repair:** Create `21-VALIDATION.md` before execution. Map each D-10 behavior
to the exact test file and command, include the migration upgrade/downgrade
evidence, include `backend/tests/integration/test_scan_source_immutability.py`,
and mark the authorized Witcher browser scenario as a manual checkpoint with
blocked-infrastructure handling.

### HIGH: Locked D-11 browser UAT is not an executable plan task

`21-04` only mentions the Witcher-style browser check in phase-level
verification prose, conditional on an environment being available. No task or
checkpoint records the required new-game and existing-refresh flows, German
text, automatic media, manual override protection, and source-library
immutability. An executor can complete every auto task and still omit the
locked UAT decision.

**Repair:** Add a final `checkpoint:human-verify` task (or a separately
dependent verification plan) that records an isolated-fixture result in
`21-UAT.md`. It must explicitly prohibit NAS, Team4s, Docker Compose, and
external-source-library writes, and must record unavailable authorized
infrastructure as blocked evidence rather than silently skipping the check.

### HIGH: Steam-media retry is not idempotent at the owned-storage layer

`21-03` downloads and stores every complete candidate inventory before calling
the new batch repository method. `21-02` only specifies candidate-row upsert.
For an unchanged candidate, a new owned path can be written on every scan;
the batch then points the existing row to the new path without a planned rule
to reuse the prior bytes or clean the superseded path. The database may avoid
duplicate rows, but owned storage leaks and retry is not idempotent as D-07
requires.

**Repair:** Specify one complete lifecycle contract across 21-02 and 21-03:
either identify unchanged active Steam candidates before download and reuse
their owned paths, or have the locked batch return superseded paths and create
cleanup intents only after a successful commit. Add tests for two identical
successful scans asserting one catalog row, no orphan owned path, stable
placements, and no cleanup of a path still referenced by another row.

### HIGH: The roadmap still has no Phase 21 goal, requirements, or plan index

`ROADMAP.md` still says `Goal: [To be planned]`, `Requirements: TBD`, and
`Plans: 0 plans`. The plan front matter lists `STEAM-02` and `STEAM-05`, but
those requirements remain mapped to completed Phase 18 and the phase itself
has no canonical trace from roadmap goal to its four plans. Context and design
make the intended goal clear, but the planning source of truth remains
incomplete.

**Repair:** Update the Phase 21 roadmap section before execution with the
approved admin-scan parity goal, the intentionally reused Steam requirements,
and the four plan entries/waves. Keep the wording aligned with D-01 through
D-12, especially the owned-media and no-source-write boundary.

### MEDIUM: Source-library immutability is not in the planned automated suite

Research identifies the existing
`backend/tests/integration/test_scan_source_immutability.py` as the automated
source-boundary proof. No plan modifies or runs it, and the final focused
command in 21-04 excludes it. Mocking storage calls in handler tests is useful,
but does not independently prove the scan integration leaves the source
library unchanged.

**Repair:** Add that integration module to 21-04's phase-focused verification
and to `21-VALIDATION.md`, or add focused assertions there for the new Steam
scan branch. Preserve its isolated fixture and do not replace it with a real
library or NAS check.

### MEDIUM: Some locked failure modes are named but not individually derived

D-10 requires unavailable, malformed, ambiguous, invalid, and rate-limited
Steam behavior to be non-destructive. The plans broadly test exceptions,
malformed URLs, HTTP/size failure, and mismatched IDs, but no task specifically
derives assertions for ambiguous name resolution and rate-limit response at the
shared-boundary level. Generic exception handling might cover both, but the
required regression evidence would be indirect.

**Repair:** In 21-01, add explicit async cases for an ambiguous/no-match name
lookup and a provider rate-limit exception, each asserting `{}` and no second
search. In 21-04, assert the resulting empty patch never invokes media
reconciliation or clears existing catalog/placement state.

## Checks that passed

- All four plans have complete task structure: files, concrete action,
  automated verification, and measurable done criteria.
- Each plan has two tasks and a narrow file set, within the scope budget.
- The backend tier allocation follows the responsibility map: pure provider
  resolution in metadata handlers, persistence in `DBRomsHandler`, storage in
  owned-resource helpers, and no new client/API transport.
- No planned task introduces deferred Steam login, ownership synchronization,
  non-Steam translation, DLC-rule changes, NAS access, Docker Compose,
  Team4s operations, or external-source-library writes.
- The plans preserve the critical data contract that an empty or failed Steam
  patch is not an empty remote inventory, so a failure cannot trigger a
  tombstone batch.

## Required revision sequence

1. Fix the migration artifact name and revision ancestry in 21-02.
2. Add `21-VALIDATION.md` and an explicit D-11 UAT checkpoint/evidence path.
3. Define the successful-retry owned-path lifecycle across 21-02 and 21-03.
4. Update the roadmap Phase 21 source-of-truth fields and add the two focused
   verification gaps.

After those changes, rerun plan checking before executing Phase 21.
