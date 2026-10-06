# Phase 24: V2 quality stabilization and unified library operations - Context

**Gathered:** 2026-10-06
**Status:** Ready for planning

<domain>
Complete the existing v2 quality work and unify storage-aware scan, matching, metadata, and media flows for classic ROM roots, PC roots with nested DLC/expansion components, and separate roots such as Nintendo, PC, and Gamebox. Preserve existing records and layouts. Do not move, delete, or rewrite external library files.
</domain>

<decisions>
## Storage is authoritative
- A storage/platform mapping determines scope, layout family, item kind, and component rules.
- Classic ROM layouts remain first-class.
- PC layouts may contain parent games and nested DLC, expansion, update, and extra components.
- Multiple independent roots are supported without a global-root assumption.

## One operation contract

- All scan entry points use one typed operation contract and one request normalizer.
- The contract distinguishes discovery, identification, metadata refresh, media synchronization, hash repair, and manual matching.
- Scope is explicit: library, platform, ROM selection, component, or provider candidate.
- Existing socket/API payloads remain compatible behind an adapter during migration.

## Metadata and media ownership

- Manual metadata and manually owned media are protected by default.
- Metadata-only, media-only, missing-only, provider-replace, and complete-rescan policies are explicit.
- Results identify changed, unchanged, protected, not-found, failed, and retryable outcomes.
- PC endpoints remain, but their results are adapted to the common policy/result model.

## Migration safety

- No destructive database migration and no automatic file movement.
- Add fixtures before changing writes for classic ROMs, PC parents, DLC/expansions, multiple roots, manual overrides, and provider-owned media.
- New requests translate to existing backend contracts until a deliberate backend upgrade.

## Confirmed divergences

- Scan.vue expands provider All through effectiveMetadataSources.
- ScanPlatformDialog.vue and RefreshMetadataDialog.vue build APIs directly from metadataSources.
- Backend scan accepts platforms, roms_ids, and platform_fs_slugs.
- MatchRomDialog, EditRomDialog, bulk refresh, and SearchCoverDialog have different lifecycle and persistence semantics.
</decisions>

<canonical_refs>

- frontend/src/v2/views/Scan.vue
- frontend/src/v2/components/Gallery/ScanPlatformDialog.vue
- frontend/src/v2/components/Dialogs/RefreshMetadataDialog.vue
- frontend/src/v2/components/Dialogs/MatchRomDialog.vue
- frontend/src/v2/components/Dialogs/SearchCoverDialog.vue
- frontend/src/v2/data/contracts.ts
- backend/endpoints/sockets/scan.py
- docs/design/v2-storage-administration.md
  </canonical_refs>

<deferred>
No provider integration, no one-shot legacy rewrite, no NAS or production migration, no automatic file cleanup.
</deferred>

---

_Phase: 24-v2-quality-stabilization-and-unified-library-operations_
_Context gathered: 2026-10-06_
