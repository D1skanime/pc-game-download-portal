---
status: complete
commit: 8ad7669d0
---

# Summary

The safety-test endpoint now accepts an optional mapping_id. Edit mode sends the active mapping identity, allowing the validator to exclude the mapping itself while still rejecting overlaps with other active mappings. New mapping requests retain duplicate protection.

Live UI verification passed: the existing Windows mapping reached Step 4 and displayed Storage selection passed the safety test.
