# Phase 15: Direct Resumable Transfer - Context

**Gathered:** 2026-09-16
**Status:** Ready for planning
**Source:** Approved downloader specification and completed Phase 14 contract

<domain>
## Phase Boundary

Phase 15 adds server-side delivery of a single authorized immutable manifest
member as its original bytes. It supports HTTP byte ranges and a strong
snapshot-bound conditional request so an interrupted direct download can safely
continue. It does not create ZIPs, split archives, extract content, create a
desktop client, manage local part files, perform client path validation, or add
v2 client handoff. Those belong to Phases 16 and 17.
</domain>

<decisions>
## Implementation Decisions

### Direct original-file delivery

- `GET /api/download-manifests/{manifest_id}/files/{public_id}` resolves only
  the Phase-14 persisted opaque IDs and server-owned trusted relations. It never
  accepts a source path, downloads a directory, creates an archive, or exposes
  a NAS/container/source path.
- The response streams the one original file directly. A 100-GB EXE, ISO, or
  PAK remains that exact file; no whole-game or part ZIP is created.
- Each member request rechecks authentication, `ROMS_READ`, manifest ownership,
  current ROM visibility, manifest lifecycle, and member authorization. A
  historical relative URL is not a durable permission grant.

### Strong snapshot contract

- The request's `If-Match` must contain exactly the stored quoted strong ETag
  snapshot and must reject weak `W/` validators. A mismatched, missing for a
  resume, expired/revoked, or strongly changed member fails without transfer.
- Before opening a member transfer, Phase 15 performs fresh full HASH-capability
  verification and recomputes the exact Phase-14 `romm-manifest-v1` snapshot
  over the public ID, destination, size, and SHA-256. Any mismatch is
  `SOURCE_CHANGED`/HTTP 412 and no bytes are sent.
- Normal Phase-14 GET remains light STAT-only; this Phase owns the expensive
  strong per-member check immediately before transfer.

### Range protocol

- A no-Range request returns direct `200 OK` with exact `Content-Length`.
- A valid single byte range returns `206 Partial Content`, `Accept-Ranges:
bytes`, and an exact `Content-Range: bytes start-end/total`. It supports
  64-bit offsets and totals above 4 GiB.
- Multi-range requests and malformed/unsatisfiable ranges have explicit bounded
  failures. An unsatisfiable range returns correct `416`/`Content-Range:
bytes */total`; the client later decides whether an exact-size part can hash
  verify or an oversized part is corrupt.
- Range semantics never silently substitute a new source version or send a
  response whose requested start/total differ from the stored/current verified
  member.

### Resource and source safety

- Delivery uses read/HASH capabilities and never changes a source root, writes
  temp files, alters access policy, restarts Team4s, or touches a real NAS.
- Server work is bounded: a documented per-process/per-request transfer limit
  prevents unlimited concurrent expensive source verification/streams. The
  concurrency implementation follows existing RomM patterns.
- All tests use isolated fixtures and synthetic sparse/mocked 5 GiB, 80 GiB,
  and 120 GiB values; no real 100-GB allocation or NAS test is required.

### Claude's Discretion

- Route module placement, response-class implementation, exact status/error
  envelope, configuration key, and bounded-concurrency primitive must follow
  established FastAPI/RomM conventions.
- Support for suffix/open-ended single ranges follows framework-safe HTTP
parsing conventions, provided it remains a single range and validates all
`u64` values.
</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Download protocol

- `docs/superpowers/specs/2026-09-15-cross-platform-pc-downloader-design.md` —
  approved direct-transfer, strong-validator, range, authorization, and
  no-archive contract.
- `.planning/phases/14-immutable-download-manifests/14-VERIFICATION.md` —
  verified manifest identity, snapshot formula, ownership, and read-only
  boundary Phase 15 must consume rather than recreate.

### Phase contracts

- `.planning/ROADMAP.md` — Phase 15 goal, dependency, requirements, success
  criteria.
- `.planning/REQUIREMENTS.md` — XFER-01 through XFER-04.
- `.planning/STATE.md` — current milestone state.
- `CLAUDE.md` — canonical checkout, source-library immutability, and testing
  requirements.
  </canonical_refs>

<specifics>
## Specific Ideas

- Future Phase-16 resume sends `Range: bytes=<offset>-` and `If-Match:
<quoted snapshot>`. Phase 15 must make that safe but does not implement the
  client or its `.romm-part-*` state.
- A response to a resume request must be reliably distinguishable as 206 with
  exact range metadata; it must not turn into an appendable 200 response.
- The client-visible member identifier is the Phase-14 UUID `public_id`, never
the internal row ID or source-manifest-member ID.
</specifics>

<deferred>
## Deferred Ideas

- Phase 16: Rust/Tauri downloader, local path security, job state, part-file
  resume, SHA finalization, disk checks, and atomic replace.
- Phase 17: v2 UI handoff, installed-client launch, and full cross-platform
end-to-end hardening.
</deferred>

---

_Phase: 15-direct-resumable-transfer_
_Context gathered: 2026-09-16 from approved specification and Phase 14_
