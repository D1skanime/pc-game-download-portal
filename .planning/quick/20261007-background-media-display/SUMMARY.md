---
status: complete
---

# Summary

- Replaced the legacy direct resource URL for selected backgrounds with the authenticated owned-media content endpoint.
- Kept background layers visible in reduced-motion mode while disabling blur, transforms, transitions, and rotation as intended.
- Added regression assertions for the endpoint and reduced-motion CSS behavior.
- Verification: 12 GameDetails tests passed in the dev container; git diff check passed.
- Repository-wide typecheck remains blocked by the pre-existing Setup.vue Axios error at line 181 (Property status does not exist).
