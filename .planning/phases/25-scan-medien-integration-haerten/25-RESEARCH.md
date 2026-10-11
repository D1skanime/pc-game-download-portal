# Phase 25: Scan-/Medien-Integration härten - Research

**Researched:** 2026-10-07
**Confidence:** HIGH for the confirmed runtime failure

Live Dev evidence: Socket.IO reaches the backend and mixed mapping scans execute. Each PC ROM logs 'Rom' object has no attribute 'metadata_source'. The bridge in backend/endpoints/sockets/scan.py calls refresh_provider_owned_media(_added_rom, _added_rom.updated_at); backend/handler/metadata/rom_media.py reads rom.metadata_source, but backend/models/rom.py stores metadata_source on RomComponentMetadata.

Reuse PlatformStorageMapping and mixed-scan orchestration for scope/read-only behavior; v2 operation contracts and useScanLifecycle for operation identity/events; scan_handler.py and filesystem/roms_handler.py for PC discovery; database roms_handler.py and reconcile_provider_owned_media for persistence/version checks.

The same scan warns unresolved PC component layout: OST. Existing DLC/Expansion behavior must remain intact; OST must be classified as audio media and NFO as an ignored sidecar.

Risks:

- Adding a parent metadata_source duplicates component provenance.
- Blanket exception handling hides programming errors.
- Broad pytest used deleted test Docker databases; use focused fixtures and canonical Dev services.

Recommended order: provider-aware reconciliation and real-model tests; per-item media results; OST/DLC/Expansion/NFO parser tests; Linux gates and browser UAT.

Anti-duplication: no second scanner, storage mapper, provider resolver, socket lifecycle, or ownership policy; new modules stay below 500 logical lines.

## Supplemental gap audit

The deeper audit found four planning gaps that the original three plans did not make executable:

- The backend exposes aggregate scan results while the v2 contract already has item-level outcome vocabulary. Results must be correlated by operation ID plus persisted ROM/component identity, never by event arrival order, and existing scan:* events must remain additive and backward-compatible.
- Component enumeration, provider linking, and optional media imports still share broad failure boundaries. One failed component or provider item must produce a retryable diagnostic while preserving ROM identification and sibling success.
- MariaDB-backed persistence and source-digest evidence are required gates, not interchangeable with source-mocked tests. Unavailable MariaDB must remain an explicit blocking result.
- The final Linux/browser matrix must cover classic, PC parent, DLC, Expansion, OST, NFO, localized metadata, targeted retry, manual-media protection, source immutability, both themes, responsive viewports, and mouse/touch/keyboard/gamepad input.

The existing Phase-24 frontend result/lifecycle work is prior art, not new Phase-25 scope. For OST, the supported boundary is source-backed soundtrack download followed by the existing Phase-20 user upload/player flow; the scan must not silently copy source audio into RomOwnedMedia. The existing Phase-20 owned soundtrack catalog is upload/provider-owned and does not provide a source-OST copy operation.

Plan 25-04 closes these gaps before the final 25-03 verification gate. It must reuse the existing provider resolver, useScanLifecycle, PC/DLC matcher, owned-media persistence, and storage/read-only boundaries. It must not add a parent metadata_source field, second socket lifecycle, generic component scan path, or parallel media catalog.
