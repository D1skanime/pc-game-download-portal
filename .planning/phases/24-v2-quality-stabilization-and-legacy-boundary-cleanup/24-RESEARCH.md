# Phase 24: Unified library operations - Research

**Researched:** 2026-10-06
**Confidence:** HIGH

The current system is a compatibility stack: a ROM-oriented scanner was extended with storage mappings, PC metadata, nested components, and v2 UI surfaces. The backend socket supports several scopes, but v2 callers do not share one request builder.

Findings:

- Full-library Scan.vue resolves provider All-mode and sends filesystem slugs.
- ScanPlatformDialog sends platform IDs and metadataSources directly.
- RefreshMetadataDialog sends platform IDs plus roms_ids and metadataSources directly.
- MatchRomDialog uses separate search/update and PC candidate endpoints.
- SearchCoverDialog changes cover selection only.
- Storage mappings express the desired multi-root model, but the scan and media operations do not consume one authoritative profile.

Safe sequence:

1. define a normalized operation and result contract;
2. resolve storage scope, providers, metadata policy, and media policy centrally;
3. translate to existing socket/API payloads;
4. migrate one entry point at a time;
5. add parity fixtures before write changes;
6. remove duplicated builders only after parity passes.

Risks:

- empty provider arrays from All-mode in platform/ROM dialogs;
- stale progress when scoped scans do not reset common state;
- different scopes for library, platform, and ROM jobs;
- manual metadata/media overwritten by provider refresh;
- bulk partial failures with no per-item retry;
- matching failures closing the dialog and losing user context.

Recommended plans:

- 24-07 normalized storage-aware operation contract and compatibility translation;
- 24-08 shared provider/policy resolver and lifecycle orchestrator;
- 24-09 metadata/media ownership and per-item result ledger;
- 24-10 migrate all UI entry points including PC/DLC and cover-only paths;
- 24-11 automated and browser validation.

## Reuse constraints

Do not create a second repository-contract layer, a second scan socket lifecycle, or a second storage-mutation policy. Extend frontend/src/v2/data/contracts.ts, wrap frontend/src/v2/composables/useScanLifecycle, and preserve sourceMutationInventory/sourceMutationControls plus the existing storage mapping version/preview rules.
