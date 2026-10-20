---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
reviewed: 2026-10-19T12:06:47Z
depth: standard
scope: "Group 1 targeted re-review of CR-01, CR-06 and CR-07 only"
source_revision: 4d6a076341578543287ed2e09fab70db94072bfe
original_review_source_revision: 4a05a1b62324a1e58c954797f4af31ca66852598
fix_baseline: ccc92d3661fcb9ef50ea0c1660a24190904dc9f5
files_reviewed: 9
files_reviewed_list:
  - backend/handler/filesystem/resource_download.py
  - backend/handler/filesystem/scan_media_publication.py
  - backend/handler/filesystem/resources_handler.py
  - backend/handler/filesystem/storage_access.py
  - backend/endpoints/sockets/scan.py
  - backend/tests/handler/media_download_helpers.py
  - backend/tests/handler/test_media_download_replacement.py
  - backend/tests/handler/test_media_download_transport.py
  - backend/tests/handler/test_media_download_gzip.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
runtime_verification: not_performed
whole_phase_approval: false
---

# Phase 34: Group 1 Download Fix Re-review

## Verdict and scope

No new BLOCKER or WARNING findings were established in the specified Group 1 scope at `4d6a07634`. Static inspection supports the corrections to original CR-01, CR-06 and CR-07. This is a targeted source review, not independent runtime verification or approval of all of 34-15 or Phase 34.

The nine files above were reviewed at standard depth, with caller and dependency tracing where needed. Every application-source read used `git show 4d6a07634:<path>`; comparisons used `ccc92d366..4d6a07634`. Current dirty Group 2 source was not used as implementation evidence. The original review and additive Group 1 fix note supplied the defect and execution context.

Within `scan_media_publication.py`, the review concerns the extracted downloader facade/import bridge and its download callers, not the unrelated existing publication/recovery findings. Within `storage_access.py`, it concerns only `OwnedReplace.binary_file` temporary ownership. Within `scan.py`, it concerns the five optional-media exception boundaries and their relevant callers. Other portions are dependency context, not a whole-file quality approval.

Original CR-02, CR-03, CR-04, CR-05, CR-08 and WR-01 are excluded from these counts and remain outside this verdict. Their status is not changed here. Future 03 worker/dispatch and non-ROM fencing, and 08 nginx/actual HTTP privacy, remain separate acceptance boundaries.

## Findings

Critical/BLOCKER: 0. WARNING: 0. Info: 0. Total new Group 1 findings: 0.

## CR-01: Replacement preservation

At `backend/handler/filesystem/resource_download.py:129-183`, non-scan downloads enter the descriptor-relative replacement capability and write a private file. The HTTP status/MIME checks at lines 78-87, complete streaming, chroma-key rejection, image loading, resizing and any WebP save precede the final context-manager exits. A rejected response, interrupted stream or invalid image therefore unwinds staging instead of opening/truncating the existing final.

For enabled WebP conversion, both PNG and WebP are staged before either replacement exits successfully. A failure while downloading, decoding, validating or transforming leaves existing final PNG and WebP bytes intact. The `publishing` flag is set before publication begins; an OSError during context-manager publication is rethrown rather than returned as an optional download failure. Other fatal exception types are not caught by this optional-error tuple. This is not a claim that two final replacements form an atomic multi-file transaction.

At `backend/handler/filesystem/storage_access.py:604-634`, the new `created` flag remains false if O_EXCL rejects an existing temporary name. The abort path then does not unlink another invocation's private file. Once this invocation has created staging, failures still remove its own temporary.

The real getters retain their fallback contracts: covers capture and return their authoritative prior references (`resources_handler.py:376-422`), manuals validate their direct-child persisted reference before fallback (`:555-664`), and a failed non-scan screenshot store now returns the prior inventory (`:544-552`). The latter avoids manufacturing a deterministic `0.jpg` reference when the committed screenshot uses a scan generation name. The explicit PC metadata-selection caller persists these returned paths (`backend/endpoints/roms/pc_metadata.py:739-762`).

The extracted facade is the existing `store_resource` export at `scan_media_publication.py:19`. Lazy imports in the new module preserve the resource-handler/publication import bridge, existing HTTPX client, ScreenScraper slot, mapped scan-source reader and local-file resolution. No duplicate downloader or storage authority was introduced by this extraction.

## CR-06: Optional transport errors and fatal boundaries

At `backend/endpoints/sockets/scan.py:345,835,864,904,939`, the optional-media boundaries now include HTTPX TransportError and DecodingError. These cover the actual primary download, parent provider catalog, special-media, badge and DLC paths, allowing provider transport/decoding failures to leave old references and continue the scanner.

The exception classes were traced rather than inferred from their names. `ScanWriteRejected` inherits RuntimeError (`backend/handler/database/scan_write_fence.py:17`), `IndeterminateOwnedPublicationError` inherits StorageResolutionError (`storage_access.py:405`; `backend/exceptions/storage_exceptions.py:1`), and SQLAlchemy errors are outside the optional tuples. The DLC loop also explicitly rethrows these fatal classes at `scan.py:343-344`.

The shared download scan branch aborts its prepared capability and rethrows at `resource_download.py:126-128`. SQL association remains outside that preparation catch. SQL commit/association failures and an unknown-commit RuntimeError therefore are not converted into these optional transport warnings. The existing session decorator and the relevant parent-provider call chain were inspected for intervening catches; their ValueError/OSError catches do not absorb those fatal classes.

## CR-07: Strict gzip completion

At `backend/handler/filesystem/resource_download.py:10-35`, each gzip member is decoded with a 1 MiB maximum output per call. The loop drains unconsumed input/output, uses unused_data after eof to start another member, and retains the new decoder across response chunks when a later header is split. A compressed member may therefore end within a raw chunk or at its boundary.

zlib corruption becomes ValueError, and a final decoder without eof is rejected. Truncated trailers, checksum errors, invalid later members and extra unencoded trailing bytes cannot reach successful finish/publication. There is no transition from decoded bytes back to raw compressed bytes. Earlier decoded staging bytes are aborted on a later failure.

Identity or absent Content-Encoding follows the plain streaming path, with output sliced to the same write bound. A complete empty gzip member is accepted; an absent/incomplete gzip member is rejected. Unsupported declared encodings and plain bytes advertised as gzip fail closed. These are deliberate encoding-contract choices, not a claim of support for every HTTP content coding.

## Behavioral coverage inspected, not executed

| New test module | Cases represented by its parametrization | Actual assertions and limits |
| --- | ---: | --- |
| `test_media_download_replacement.py` | 20 | Fourteen legacy cover/manual/screenshot failure cases assert exact snapshots and returned paths; one PNG/WebP success case checks formats/dimensions; one actual PC selection checks persisted paths; one foreign-temporary collision checks both private and public bytes; three real committed-generation screenshot cases check fallback and exact snapshots. |
| `test_media_download_transport.py` | 24 | Twelve actual scanner transport cases assert retained SQL references/bytes and that a second source has real ROM/file rows; three actual DLC cases first commit provider media and then verify retained row identities/paths/bytes; nine scanner fatal controls use the real publication/association path and real cancellation or callback SQL/indeterminate errors. |
| `test_media_download_gzip.py` | 33 | Twenty-four scan/non-scan manual/video rejection cases check unchanged references/snapshots and no cleanup intent; five completion controls check exact published bytes; three actual special-scanner corruption cases check retained metadata/bytes; one 56 MiB decoded-video case observes bounded writes and the full SHA-256 through the real capability. |

The helper uses HTTPX MockTransport and AsyncByteStream faults, not a replacement downloader returning synthetic success. Scanner tests replace provider discovery responses, while retaining actual scanner, mapping, SQL and capability paths. The fatal controls inject errors inside the association callback, and cancellation changes the actual operation repository.

Coverage is narrower than every claim one could make about these paths. The added transport cases explicitly inject ConnectError/ReadTimeout/ReadError, not DecodingError. Added fatal scanner controls cover primary/special/badge, not parent/DLC or a new lost-commit-acknowledgement case. The WebP-specific added case is successful conversion, not an existing-sidecar conversion-failure case. Committed-generation failure coverage is explicit for screenshots; cover/manual fallbacks were additionally traced in source. The gzip concatenation control sends complete members in separate response chunks, and the split-header control splits the initial header; packed members and a split later-member header were traced in the loop rather than separately demonstrated by these tests. These limits do not establish a concrete additional defect, and are not counted as findings.

The fix note's 362 full-suite passes and subsequent 77 targeted passes remain executor-reported evidence. No tests, application/runtime commands, database access or application resources were used by this reviewer.

## Decomposition and preservation

Pinned nonblank/noncomment counts are 171 for the new runtime download module and 353 for the publication module. Both remain within the repository's 500-logical-line target. The added test/helper modules were read in full; length alone was not treated as a defect. Legacy changes are narrow delegation, caller handling and capability ownership corrections.

Preflight and the pre-write check confirmed Linux over SSH `team4s-linux`, Git root `/home/d1sk/pc-game-download-portal`, branch `codex/phase-32-pgdp-naming`, origin `https://github.com/D1skanime/pc-game-download-portal.git` and matching project planning identity. Canonical AGENTS/CLAUDE and backend/security review guides informed the review. No additional project skill directories were present under `.codex/skills` or `.agents/skills`. Scoped source paths are tracked and were checked against repository ignore rules.

Only this additive review artifact was written. No source, test, original review, fix note, STATE, ROADMAP or other phase artifact was modified. No nested agents, tests, DB actions, deployment, commit, branch change or whole-phase approval occurred.

---

_Reviewer: gsd-code-reviewer_
_Depth: standard, targeted Group 1_
_Source: 4d6a076341578543287ed2e09fab70db94072bfe_
