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

## Localization and language-aware metadata

- UI locale and metadata locale are separate operation inputs; changing the UI language must never overwrite stored game metadata.
- Localized values use stable locale codes ('de-DE', 'en-US', etc.), provider, field, and ownership state. Do not add one hardcoded column set per language.
- Existing Steam German values are migrated conservatively to 'de-DE' only when their provenance is known; unknown-language values are preserved and never guessed destructively.
- Metadata refresh is field- and locale-aware: a provider update for one language cannot replace another language or a protected manual value.
- Metadata fallback is read-time behavior only. An English fallback may be displayed when German is missing, but must not be persisted as German.
- Media is classified separately: language-neutral artwork, language/region-specific covers, and text-bearing screenshots/trailers must not be treated as one overwriteable bucket.
- Provider payloads and manual values retain source/provenance so merge decisions remain explainable.

## Non-negotiable reuse and safety gates

- Before adding any new abstraction, produce a reuse matrix against PlatformStorageMapping, v2/data/contracts.ts, useScanLifecycle, the legacy scan adapter, PC/DLC endpoints, and sourceMutationInventory/sourceMutationControls.
- A new type or service is allowed only when the existing implementation cannot express the requirement. The plan must name the missing capability and the compatibility adapter.
- Do not introduce a second storage profile database model, second socket lifecycle, second provider resolver, or second ownership policy.
- Metadata refresh and media synchronization remain separate operations. A combined UI action must still dispatch two explicit policy dimensions.
- Bulk operations must carry a stable job correlation or run serially. Results may not be matched by arrival order.
- Every write path must calculate a field/media patch first, apply ownership protection, and abort the whole item on policy or validation error. Partial writes require an explicit backend transaction contract.
- Migration proceeds one vertical slice at a time: main scan, platform scan, ROM refresh, then manual/PC/DLC matching. Do not migrate all callers in parallel.
- Every scan UI uses stable operation IDs and translation keys, never translated labels as logic. The canonical operations are library scan, metadata refresh, media refresh, file check, and folder mapping; platform scan is a scoped library scan, not a second implementation.

## Migration safety

- No destructive database migration and no automatic file movement.
- Add fixtures before changing writes for classic ROMs, PC parents, DLC/expansions, multiple roots, manual overrides, and provider-owned media.
- New requests translate to existing backend contracts until a deliberate backend upgrade.

## Existing implementations to reuse

- frontend/src/v2/data/contracts.ts already defines the v2 repository and mutation contracts; new operation types extend this file or live beside it without replacing existing contracts.
- frontend/src/v2/composables/useScanLifecycle/index.ts already owns global socket event wiring and Pinia synchronization; the new operation facade must consume or wrap it.
- frontend/src/v2/sourceMutationInventory.test.ts and sourceMutationControls.test.ts already protect storage mutation and PC/DLC ownership boundaries.
- PlatformStorageMapping.vue and docs/design/v2-storage-administration.md already define the safe mapping draft, version, preview, and no-file-mutation behavior.

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
