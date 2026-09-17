# Phase 17 Browser Download Manager Source Audit

This audit freezes the implementation boundary before product work begins. It
maps the roadmap, requirements, research, and locked context to plans 17-02
through 17-13. Plan 17-01 corrects the stale records and is the documentation
prerequisite for this audit.

## Roadmap goal and success criteria

| Source item | Required truth                                                                                                                                                                                                                                       | Plan coverage                                          |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Goal        | Browser-only v2 selection of PC components or allowed files, one immutable manifest, original direct member downloads, standard attachment baseline, optional capability-detected File System Access, controlled queues, and unchanged source safety | 17-03, 17-06, 17-07, 17-08, 17-12                      |
| Success 1   | Valid selection creates one immutable manifest and downloads original files without desktop software or ZIP packaging                                                                                                                                | 17-03, 17-07, 17-12                                    |
| Success 2   | Standard browser downloads are universal; File System Access is optional and capability-detected                                                                                                                                                     | 17-07, 17-08, 17-11, 17-12                             |
| Success 3   | Queue, history, source-change handling, Range protocol, and terminology distinguish browser handoff, server delivery, and enhanced verification                                                                                                      | 17-04, 17-06, 17-07, 17-08, 17-09, 17-10, 17-11, 17-13 |
| Success 4   | Large and multi-file evidence is source-safe, path-free, and free of desktop or infrastructure claims                                                                                                                                                | 17-05, 17-08, 17-12                                    |

## Requirement coverage

| Requirement | Obligation                                                                                                                                                                            | Plan coverage                                                               |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| UXDL-01     | Browser-only whole-game, component, or allowed-file flow using one server-validated immutable manifest, direct members, standard attachment delivery, and optional File System Access | 17-02, 17-03, 17-04, 17-06, 17-07, 17-08, 17-09, 17-10, 17-11, 17-12, 17-13 |
| SAFE-01     | Manifest preparation and every transfer leave the NAS and source library read-only and unchanged, with no source paths disclosed                                                      | 17-02, 17-03, 17-04, 17-05, 17-06, 17-07, 17-08, 17-11, 17-12, 17-13        |
| TEST-01     | Coverage for resume, source changes, bad checksums, disk and permission recovery, values above 4 GiB, safe paths, and source before/after evidence                                    | 17-02, 17-03, 17-04, 17-05, 17-06, 17-07, 17-08, 17-11, 17-12, 17-13        |

Phase 15 remains the authority for direct-transfer protocol evidence: original
bytes, strict Range and If-Match behavior, source-change failure, values above
4 GiB, and bounded server concurrency. Phase 17 consumes that authority and does
not create a parallel file route.

## Research coverage

| Research feature or constraint                                                                     | Plan coverage                            |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Replace desktop handoff with browser-only workflow                                                 | 17-07, 17-08, 17-12                      |
| Reuse Phase 14 manifest and Phase 15 direct single-file transfer authorities                       | 17-03, 17-07, 17-08, 17-12               |
| Whole-game and explicit component selection without filename or directory heuristics               | 17-02, 17-03, 17-07                      |
| Persisted explicit required archive sets and optional member selection                             | 17-02, 17-03, 17-07, 17-12               |
| Owner-scoped, path-free transfer sessions and append-only observational history                    | 17-04, 17-05, 17-07, 17-13               |
| One centrally configured queue concurrency limit                                                   | 17-06, 17-07, 17-08, 17-12               |
| Standard browser attachment baseline and truthful handed-to-browser state                          | 17-07, 17-09, 17-10, 17-11, 17-13        |
| Capability-detected directory picker with user activation and fallback                             | 17-08, 17-11, 17-12                      |
| Streamed enhanced writes and incremental SHA-256 without whole-file buffering                      | 17-08, 17-11, 17-12                      |
| Strict enhanced Range, If-Match, 206, and Content-Range validation                                 | 17-08, 17-12                             |
| Terminal source-changed, expired, revoked, cancelled, and failed outcomes                          | 17-04, 17-05, 17-08, 17-11, 17-13        |
| Safe relative destination validation for POSIX and Windows forms                                   | 17-08, 17-11, 17-12                      |
| v2 primitives, semantic tokens, locale parity, and universal input                                 | 17-07, 17-08, 17-09, 17-10, 17-11, 17-13 |
| No ZIP fallback, generic ROM bulk route, source-path disclosure, or session-as-credential behavior | 17-03, 17-04, 17-07, 17-08, 17-12        |
| Deterministic isolated tests and source fingerprints before and after transfer                     | 17-02, 17-03, 17-04, 17-05, 17-08, 17-12 |

## Locked context decision coverage

| Locked decision group                                                                                                                                            | Plan coverage                                                 |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Manifest and direct transfer remain the only delivery authorities; members expose opaque IDs, safe destinations, sizes, digests, and snapshots                   | 17-03, 17-07, 17-08, 17-12                                    |
| Large originals stream directly and are never buffered, split, staged, copied, reconstructed, or archived server-side                                            | 17-07, 17-08, 17-12                                           |
| Component-first UX, explicit required sets, optional-file exclusion, and server validation before manifest creation                                              | 17-02, 17-03, 17-07, 17-13                                    |
| Standard mode is browser handoff only; browser safeguards are not bypassed and no unsupported completion or resume claim is shown                                | 17-07, 17-09, 17-10, 17-11, 17-13                             |
| Enhanced mode uses a user-initiated picker, repeated permission checks, destination revalidation, streamed writes, and no whole-file Blob or ArrayBuffer         | 17-08, 17-11, 17-12                                           |
| Enhanced resume accepts only exact snapshot-bound 206 responses and fails closed on source or manifest changes                                                   | 17-08, 17-12                                                  |
| Queue cap is centralized and applies to original files, while pause and cancel are limited to controllable enhanced transfers                                    | 17-06, 17-08, 17-11                                           |
| Session records are owner-scoped, path-free, observational, and retained with bounded cleanup                                                                    | 17-04, 17-05, 17-13                                           |
| `served` means server response delivery, `handed_to_browser` means standard attachment handoff, and `verified` means enhanced local SHA-256 equality             | 17-04, 17-07, 17-09, 17-10, 17-11, 17-13                      |
| Current queue and recent owner-scoped history are presented for the active ROM or selected manifest without source, local path, URL, token, or credential values | 17-07, 17-13                                                  |
| Typed owner-scoped session list and get contracts hydrate the current queue and recent history; stale responses are ignored after selection or unmount           | 17-07, 17-13                                                  |
| Source roots, NAS paths, Team4s, deployment, and restarts remain outside test and runtime scope                                                                  | 17-02, 17-03, 17-04, 17-05, 17-06, 17-07, 17-08, 17-11, 17-12 |

## Explicit exclusions

The following are deferred or cancelled and have no implementation plan in this
phase: desktop cleanup, Windows/Linux/Bazzite installers, Tauri handoff, custom
schemes, local desktop services, archives, ZIP creation, extraction, mounting,
installation, launching, cloud sync, real NAS access, Team4s changes,
deployment, service restarts, and source-root writes. The retained Phase 16
desktop prototype is documentation-only inventory, not an implementation
dependency. No unplanned item is included in the Phase 17 plan set.

## Plan inventory

The complete non-deferred implementation map is 17-02 archive policy, 17-03
manifest validation, 17-04 transfer journal, 17-05 retention cleanup, 17-06
queue configuration, 17-07 standard browser selection and queue, 17-08 enhanced
streaming and resume, 17-09 and 17-10 locale parity, 17-11 accessibility and
truthful-state tests, 17-12 deterministic safety and browser evidence, and
17-13 current queue plus recent transfer-history presentation.

**No unplanned source item remains.**
