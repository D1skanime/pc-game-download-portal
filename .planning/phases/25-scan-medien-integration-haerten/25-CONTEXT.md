# Phase 25: Scan-/Medien-Integration härten - Context

**Gathered:** 2026-10-07
**Status:** Ready for planning

<domain>
Complete the missing end-to-end integration between mapped scans, provider metadata, PC component discovery, and v2 owned-media surfaces. Preserve PlatformStorageMapping, the read-only PC source boundary, console behavior, shared provider/socket lifecycle, and existing owned-media persistence.
</domain>

<decisions>
- Do not add Rom.metadata_source; resolve provider from existing scan/component metadata authority and pass it explicitly.
- Keep legacy resource paths while filling canonical rom_owned_media idempotently; manual media remains protected.
- One media/provider failure is per-item and retryable; programming errors stay visible.
- DLC and Expansion remain PC components; OST remains a source-backed soundtrack file that can be downloaded and then uploaded through the existing Phase-20 Owned-soundtrack flow; NFO is an ignored sidecar.
- Verify only on Linux Dev services; browser UAT is blocking.
- New production files target at most 500 logical lines; new files above 1,000 are prohibited except approved generated artifacts.
</decisions>

<canonical_refs>

- frontend/src/v2/data/contracts.ts
- frontend/src/v2/composables/useScanLifecycle/index.ts
- backend/endpoints/sockets/scan.py
- backend/handler/metadata/rom_media.py
- backend/models/rom.py
- backend/handler/scan_handler.py
- backend/handler/filesystem/roms_handler.py
- backend/handler/database/roms_handler.py
  </canonical_refs>

<deferred>
No new storage/mapping model, scanner, provider resolver, socket lifecycle, ownership policy, source movement, cleanup, or migration.
</deferred>
