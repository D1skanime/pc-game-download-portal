---
status: complete
commit: 38ea5ea92
---

# Steam manual match media

Implemented the narrow backend fix for manual Steam PC matching. Steam name-search results are now hydrated through the existing detailed Steam resolution path, so candidate cover and screenshot URLs reach the review dialog. Invalid storefront types such as music/soundtrack entries are excluded from the candidate list.

Verification:

- Regression test passed: `test_name_search_hydrates_candidates_with_review_media`.
- Python compilation passed for the changed handler and test.
- Pre-commit formatting and checks passed for both changed files.
- Focused Steam/PC metadata suite was attempted; it still contains unrelated baseline failures (locale mock mismatch, missing fixture, and older component mocks).
- Live Dev UI showed a Steam-only candidate with a real cover after the first fix; the service was restarted after the final invalid-type refinement.

Note: `gsd-sdk` was unavailable on the Linux VM, so this quick-task artifact was created manually.
