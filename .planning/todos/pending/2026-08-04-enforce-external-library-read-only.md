---
created: 2026-08-04T00:00:00+02:00
title: Enforce immutable external game libraries
area: security
files:
  - backend/handler/filesystem/base_handler.py
  - backend/handler/filesystem/platforms_handler.py
  - backend/handler/filesystem/roms_handler.py
  - backend/endpoints/roms/
  - docker-compose.yml
  - docs/PC_GAME_COMPONENTS_AND_MANIFEST_DOWNLOADS_ANALYSIS.md
---

## Problem

RomM currently assumes a library structure it can manage. RomM PC Library must consume an existing NAS games root without copying, restructuring, or mutating it. UI-only restrictions are insufficient because existing backend delete, rename, move, upload, extraction, patch, and directory-creation paths could still be invoked directly.

## Solution

Make external libraries permanently read-only through defense in depth. Require a Docker `:ro` mount, model the root as `external_read_only`, and enforce a central backend storage-operation policy before every filesystem mutation. Store mappings and scan results in the database and all generated resources outside the library. Replace source deletion semantics with a catalog-only removal operation. Audit every mutating filesystem and ROM API path, then add negative tests proving direct API calls cannot change external files. Document `noatime` or the NAS-specific equivalent for deployments that also require reads not to update access-time metadata.
