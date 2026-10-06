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

## Mandatory anti-duplication gates

Before implementation, the planner must inventory existing storage mappings, scan lifecycle, provider selection, PC/DLC endpoints, ownership controls, and result events. New abstractions must wrap or extend those seams. If a proposed new database model or backend policy is not required by an identified gap, the plan must stop and reuse the existing model.

The migration must begin with a read-only normalized request and parity tests. Only after request parity passes may a caller change its write path. Metadata and media are separate operations, and bulk results require job correlation or serialization.

## Localization findings and mandatory gates

The existing Steam behavior demonstrates a data-loss risk: a second language can overwrite the same description field. Language must therefore be part of metadata identity, not a UI-only concern.

- Inventory current language fields, Steam language behavior, provider payloads, and any already-added localized columns before changing schema or writes.
- Normalize locale codes and preserve provider/source/manual provenance. Do not create a hardcoded field set for every language.
- UI locale, metadata locale, and provider fallback are separate inputs. Translated labels must never drive matching, persistence, or operation dispatch.
- A metadata update is scoped by field and locale; it cannot overwrite another locale or a protected manual value.
- Fallback is read-only display behavior. Existing values are never rewritten because UI or preferred metadata language changed.
- Media needs its own language/region policy: neutral artwork can be reused, while localized covers and text-bearing media remain distinguishable.
- Existing values may be labeled 'de-DE' only when evidence supports that migration; otherwise preserve them as unknown-language legacy data.
- Add German/English fixtures for metadata, fallback, manual protection, provider precedence, media language/region, and migration before enabling writes.
- Provider precedence must be evaluated per field, locale, and region. Test an IGDB English baseline plus linked Steam German text/media, missing German fallback, and a provider returning an unexpected locale.
- Run a repository-wide file-size inventory before implementation. Prioritize hand-written runtime files above 1,000 logical lines, especially scan, ROM, metadata, storage, and active v2 UI files. Exclude generated files, migrations, fixtures, and verification tools from automatic extraction, but record them separately.
- Refactor only with characterization/parity tests and one responsibility per extracted module. Do not move code across boundaries if that creates a second storage mapper, PC matcher, provider resolver, lifecycle, or ownership policy.
- Treat a file-size reduction as successful only when behavior, imports, route contracts, socket events, and ownership semantics remain unchanged.
