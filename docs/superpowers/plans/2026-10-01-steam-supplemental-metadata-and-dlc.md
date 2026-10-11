# Steam Supplemental Metadata and DLC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fill missing PC metadata from Steam without replacing IGDB/manual values, show imported Steam media immediately in the game overview, then verify DLC behavior with an isolated Cyberpunk 2077 fixture.

**Architecture:** The Steam adapter normalizes localized genres and categories. The merge layer fills only compatible empty metadata, while Steam DLC IDs are resolved only for filesystem components already discovered under a durable parent ROM. Owned Steam media claims the visible cover and overview gallery only when those surfaces are unclaimed.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, pytest, Steam app-details.

**Spec:** `docs/superpowers/specs/2026-10-01-steam-supplemental-metadata-and-dlc-design.md`

## Global Constraints

- IGDB and operator-authored values are authoritative.
- Provider errors and unmatched DLC IDs are non-destructive no-ops.
- Tags are out of scope because app-details has no stable public tag contract.
- UAT uses synthetic read-only data only, never NAS, Team4s, or a real library.

## Review Focus

- Empty Steam lists cannot clear existing values.
- Existing IGDB or manual values cannot be replaced.
- An operator-selected cover or gallery ordering cannot be replaced by Steam.
- A DLC ID without a filesystem component cannot create a phantom component.
- A failed DLC lookup cannot clear prior component metadata.
- The UAT source hash stays unchanged through new, UPDATE, and COMPLETE scans.

---

### Task 1: Normalize and merge supplemental Steam metadata

**Files:**

- Modify: `backend/adapters/services/steam_types.py`
- Modify: `backend/handler/metadata/steam_handler.py`
- Modify: `backend/handler/metadata/steam_merge.py`
- Test: `backend/tests/handler/metadata/test_steam_handler.py`
- Test: `backend/tests/handler/metadata/test_steam_merge.py`

**Interfaces:** Produces localized `steam_metadata["genres"]` and `steam_metadata["categories"]`, with guarded structured updates for compatible empty PC metadata fields.

- [ ] Write failing tests for German genre/category normalization, empty-field enrichment, and IGDB/manual preservation.
- [ ] Run `cd backend && uv run pytest tests/handler/metadata/test_steam_handler.py tests/handler/metadata/test_steam_merge.py -x` and verify the expected failure.
- [ ] Add minimal typed app-details fields, normalization, and merge behavior. Do not add tags or alter IGDB relationship fields.
- [ ] Re-run the focused tests and commit the implementation and tests atomically.

### Task 2: Safely associate Steam DLC with existing PC components

**Files:**

- Modify: `backend/handler/metadata/steam_handler.py`
- Modify: `backend/handler/metadata/pc_match_handler.py`
- Modify: `backend/handler/scan_handler.py`
- Test: `backend/tests/handler/metadata/test_pc_match_handler.py`
- Test: `backend/tests/handler/test_scan_handler.py`

**Interfaces:** Consumes parent `steam_metadata["dlc_ids"]` and existing `RomComponent` records. Produces localized Steam identity only for matching components.

- [ ] Write failing tests using Cyberpunk 2077 (`1091500`) and Phantom Liberty (`2138330`) for matching, missing-component, and provider-failure cases.
- [ ] Run the focused tests and verify the expected failure.
- [ ] Reuse the existing component matching path to persist provider identity after durable parent persistence. Never create components from Steam data.
- [ ] Re-run the focused tests and commit the implementation and tests atomically.

### Task 3: Project unclaimed Steam media into the visible overview

**Files:**

- Modify: `backend/handler/metadata/steam_owned_media.py`
- Modify: existing owned-media placement and overview read-path modules
- Test: `backend/tests/handler/metadata/test_steam_owned_media.py`
- Test: existing overview/media endpoint tests

**Interfaces:** Consumes reconciled Steam artwork and screenshots. Produces a visible primary cover plus ordered overview-gallery entries only for unclaimed surfaces.

- [ ] Write failing tests for an unclaimed cover, an unclaimed gallery with all screenshots, and preservation of manual cover/gallery choices.
- [ ] Run the focused media and overview tests and verify the expected failure.
- [ ] Reuse the owned-media catalog to project the first artwork to cover and all screenshots to overview without legacy URL duplication or destructive replacement.
- [ ] Re-run the focused tests and commit the implementation and tests atomically.

### Task 4: Add the isolated Cyberpunk 2077 UAT fixture

**Files:**

- Modify: a dedicated isolated-UAT seed tool under `backend/tools/`
- Test: the corresponding test under `backend/tests/tools/`
- Modify: `.planning/phases/21-unify-admin-pc-scans-with-german-steam-metadata-and-media/21-UAT.md`

**Interfaces:** Produces a read-only `win/Cyberpunk2077` source tree with a synthetic `dlc/PhantomLiberty` component and no pre-existing catalog metadata.

- [ ] Write a failing fixture test for fixture contents, source digest stability, and no host-specific paths.
- [ ] Run it with `tests/integration/test_scan_source_immutability.py` and verify the expected failure.
- [ ] Add the synthetic fixture, active `win` mapping, and browser-UAT setup without NAS or Team4s access.
- [ ] Verify new, UPDATE, and COMPLETE scans, record cover, gallery, DLC, manual protection, and PASS/FAIL/BLOCKED evidence in `21-UAT.md`, then commit atomically.
