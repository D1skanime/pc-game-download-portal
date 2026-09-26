---
status: complete
---

# Download history refresh flicker summary

History hydration now observes only ROM, manifest, and session identity.
Per-file queue status is already rendered from the live queue, so it no longer
triggers a full history refresh or spinner replacement for every file.
