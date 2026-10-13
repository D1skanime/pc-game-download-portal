---
quick_id: 261013-safety-test
slug: fix-safety-test-existing-mapping
status: executed
---

# Fix safety test for existing mappings

## Goal

Allow the storage safety test to validate an existing active mapping during edit mode without weakening overlap and duplicate protection for new mappings.

## Tasks

- Add an optional mapping identity to the safety-test request.
- Exclude only that mapping from self-overlap and duplicate checks.
- Send the identity from the edit UI and cover it with backend and frontend verification.

## Verification

- Existing-mapping safety test succeeds in the UI.
- Frontend unit test, typecheck, and production build pass.
- Backend compile and diff checks pass; DB-backed handler test is blocked by the test fixture connecting to host 127.0.0.1:3306.
