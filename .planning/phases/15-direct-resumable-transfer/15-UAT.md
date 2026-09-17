---
status: complete
phase: 15-direct-resumable-transfer
source: automated local loopback transfer validation
started: 2026-09-17
updated: 2026-09-17
---

# Phase 15 UAT: 30 GiB Direct Transfer

## Test

Created one temporary sparse source member with the logical size `30 GiB`
(`32,212,254,720` bytes), then transferred the complete original byte stream
through a local HTTP `StreamingResponse` using the production Phase-15
verified transfer lease. The receiver wrote only to `/dev/null` while hashing
every received byte.

## Result

- Result: pass
- Source logical size: `32,212,254,720` bytes
- Received bytes: `32,212,254,720` bytes
- Source disk allocation: `0` bytes (sparse test file)
- SHA-256: `977bf5033165994e1d6837b65d66ac29093bfcfb1e49b4b828387b35cc830673`
- Cleanup: pass, the unique temporary source directory no longer exists.

## Scope

This did not access Team4s, a NAS, or a deployed instance. It validates the
actual Phase-15 verified transfer lease and HTTP streaming data path locally.
The separate endpoint suite covers authorization, ownership, visibility,
lifecycle, ETag, and range protocol handling.
