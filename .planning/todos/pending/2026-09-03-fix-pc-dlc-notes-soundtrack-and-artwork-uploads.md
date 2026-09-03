---
created: 2026-09-03T14:39:32.873Z
title: "Fix PC DLC notes and media uploads"
area: backend
files:
  - frontend/src/v2/components/GameDetails/PcDlcMediaTab.vue
  - frontend/src/v2/components/GameDetails/PcDlcNotesTab.vue
  - backend/endpoints/roms/pc_component_resources.py
  - frontend/src/components/GameDetails/NotesTab.vue
  - backend/endpoints/roms/notes.py
---

## Problem

Phase 12 UAT found that soundtrack upload is unsupported for component-owned DLC media: the UI offers no soundtrack role and the only component-media endpoint accepts only PNG, JPEG, and WebP images. Artwork upload was reported as failing, but the exact browser response was not captured; image artwork is accepted by the existing role model and may instead be absent from the presentation layer. Notes cannot be saved for parent ROMs or DLC components. A direct authenticated parent-note diagnostic request was rejected with CSRF 403, while the DLC path may additionally reject a stale `expected_version`; the actual browser requests must be captured before choosing the correction.

## Solution

Create a follow-up phase or plan with separate TDD-backed tracks:

1. Add a bounded component-owned soundtrack upload, persistence, download/playback, and UI flow. Do not weaken the existing image validator to accept audio.
2. Reproduce artwork upload in the browser, capture the response, then correct either image MIME validation or owned-media presentation with a regression test.
3. Capture parent and DLC note save requests, including status/body/CSRF behavior. Fix only the confirmed shared client/CSRF or DLC version-refresh cause, with parent and component regression coverage.

Keep component-owned media isolated from immutable source-library evidence and from parent-ROM media.
