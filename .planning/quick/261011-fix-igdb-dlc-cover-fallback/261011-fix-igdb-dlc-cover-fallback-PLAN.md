---
quick_id: 261011-fix-igdb-dlc-cover-fallback
status: complete
---

# Preserve IGDB DLC fallback covers

## Task 1: Preserve an existing related-game cover during IGDB enrichment

- Files: backend/handler/metadata/pc_match_handler.py
- Action: When hydrating a related IGDB DLC/expansion, retain the candidate's existing cover media if the detail response omits or returns an empty url_cover.
- Verify: Candidate media still contains the related cover while hydrated metadata fields are retained.
- Done: The DLC match card receives a usable IGDB cover whenever the parent metadata already supplied one.

## Task 2: Add regression coverage

- Files: backend/tests/handler/metadata/test_pc_match_handler.py
- Action: Add a focused async test for a related IGDB candidate whose hydration has no cover.
- Verify: The focused test was added; syntax compilation passes. The pytest fixture is currently blocked before assertions because its test database connection targets unavailable 127.0.0.1:3306.
- Done: The previously observed placeholder regression is covered by the new assertion.
