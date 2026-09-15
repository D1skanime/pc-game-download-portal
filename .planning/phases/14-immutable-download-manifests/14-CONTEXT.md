# Phase 14: Immutable Download Manifests - Context

**Gathered:** 2026-09-15
**Status:** Ready for planning
**Source:** Approved downloader design specification

<domain>
## Phase Boundary

Phase 14 turns an authorized selection of one whole PC game or exact existing
base-game, update, DLC, and extra components into one immutable, hash-backed
download manifest. It uses the PC component model and per-file SHA-256 evidence
already present in RomM. It must not stream data, create ZIP archives, create a
desktop client, write to a source root, or expose NAS paths. Direct HTTP Range
delivery is Phase 15; Tauri/Rust local download work is Phase 16; web handoff and
end-to-end hardening are Phase 17.
</domain>

<decisions>
## Implementation Decisions

### Manifest identity and contents

- A manifest represents exactly one user-authorized whole-game or selected
  component set and has a distinct immutable manifest ID.
- Every member exposes only an opaque file/member identity, safe relative
  destination, `u64` byte size, SHA-256, separate strong snapshot validator,
  and a relative future delivery URL. It never exposes a source/NAS path,
  source-root path, or host structure.
- `snapshot` is a strong ETag/strong validator and never a weak `W/` ETag.
  It identifies the captured source version; SHA-256 remains the independent
  final-content integrity proof.
- Existing PC component/manifests are the sole source for member discovery;
  ambiguous, missing, unsafe, or unready file evidence must fail clearly rather
  than produce a partial or guessed manifest.

### Lifecycle and authorization

- Manifest status is explicitly `VALID`, `EXPIRED`, `REVOKED`, or
  `SOURCE_CHANGED`; expiration/staleness must not be reported as a source change.
- A manifest is created only for the requesting authorized user and selected
  game/components. Phase 15 rechecks authentication and manifest authorization
  on each file request; Phase 14 must establish the required ownership and
  authorization contract without treating a future URL as a durable grant.
- If source identity cannot still match the captured snapshot, the manifest is
  `SOURCE_CHANGED` and no mixed-version member set is authorized.

### Safety boundary

- The external library and NAS remain read-only: manifest preparation performs
  database/read/hash evidence operations only and creates no source files,
  directories, archives, temp files, or metadata sidecars.
- Server-side IDs resolve internally through the trusted component/source-root
  model. Client-facing contracts never accept an arbitrary source path.

### Claude's Discretion

- Persisted schema/API naming, TTL configuration mechanism, response envelope,
  database migration shape, and placement of shared validators follow existing
  RomM patterns.
- How a client selection maps to current component records may reuse the
existing game/component API conventions, provided all selection and safety
rules above remain observable and testable.
</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Downloader contract

- `docs/superpowers/specs/2026-09-15-cross-platform-pc-downloader-design.md` —
  approved cross-platform protocol, immutable-manifest boundary, snapshot and
  source-safety rules.
- `docs/PC_GAME_COMPONENTS_AND_MANIFEST_DOWNLOADS_ANALYSIS.md` — existing PC
  component and manifest analysis; read-only technical basis.

### Project contracts

- `.planning/ROADMAP.md` — Phase 14 goal, dependency, and success criteria.
- `.planning/REQUIREMENTS.md` — DLMT-01 through DLMT-03 and milestone boundary.
- `.planning/STATE.md` — current milestone status and prior decisions.
- `CLAUDE.md` — canonical checkout, architecture, testing, and source-library
  safety requirements.
  </canonical_refs>

<specifics>
## Specific Ideas

- The current UI already supports whole-game and component choices. Phase 14
  provides the stable server-authorized manifest those choices need; it does not
  yet add a client handoff control.
- A 100-GB original EXE/ISO remains one member with its original byte size. No
  ZIP, split archive, extraction, or repackaging is introduced.
- Phase 14 must make later strict resume possible: member snapshot identity is
separate from SHA-256, and the contract carries an opaque member identifier.
</specifics>

<deferred>
## Deferred Ideas

- Phase 15: authenticated direct file endpoints, HTTP Range responses,
  `If-Match`, `206` validation, and resumable streaming.
- Phase 16: Rust core, Tauri app, local `.romm-part-*` state, path resolution,
  hash verification, atomic rename/replace, disk recovery, Windows/Linux tests.
- Phase 17: v2-to-client handoff and end-to-end large-file/failure hardening.
</deferred>

---

_Phase: 14-immutable-download-manifests_
_Context gathered: 2026-09-15 from approved specification_
