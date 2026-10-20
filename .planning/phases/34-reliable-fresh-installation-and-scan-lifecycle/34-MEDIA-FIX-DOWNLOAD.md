# Phase 34 Media Fix: Download Group 1

Date: 2026-10-19. Contract: 34-15-PLAN.md and 34-REVIEW.md at da362317b, reviewed source 4a05a1b62. Corrective execution baseline: ccc92d366.

## Result and limits

CR-01, CR-06 and CR-07 were independently reproduced against their actual callers and repaired under deviation Rules 1 and 2. None of these three findings was rejected. Executor verification is complete for this group; independent review remains pending. The review artifact and its status are unchanged.

This is an additive correction note for completed 34-15, not a replacement SUMMARY, a new phase, a repeat of Tasks 1/2/3, or permission to start 34-03. Overall remains five existing summaries (01/02/05/07/15). Shared STATE, ROADMAP, requirements and Phase 33 acceptance remain parent-owned.

Unfixed and not adjudicated here: CR-02, CR-03, CR-04, CR-05, CR-08 and WR-01. The 34-15 quality gate remains open. All groups still need the future independent review. 03 worker/dispatch and non-ROM outputs, plus 08 nginx/HTTP, production and browser acceptance, remain open.

## Canonical environment and preservation

Preflight confirmed Linux over ssh team4s-linux, Git root /home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming, origin https://github.com/D1skanime/pc-game-download-portal.git and matching RomM PC Library planning identity. Repeated before the additive note. workflow.use_worktrees=false was honored.

All project reads, code/artifact writes, tests and commits ran in that verified checkout. No Windows project copies/writes, branch change, worktree, nested agent, push, live database, dev.env, scan, reset, stash, service restart or deployment was used. Normal commit hooks ran without bypass. Staging always named exact files.

Preserved unrelated dirty STATE, Phase 33 UAT/VALIDATION, setup.py, both Compose files and untracked backend/pgdp_test/ and pgdp_test/. No shared requirement completion. Original media/fence test files, runner/fixtures, completed summaries and review are unchanged by this group. No tracked files were deleted.

Canonical backend-development/pre-pr-verification and receiving-code-review, systematic-debugging, TDD and verification-before-completion guidance informed caller tracing, actual behavioral RED, capability reuse and fresh verification.

## Verified findings and implementation

### CR-01: Non-scan replacement preservation

Actual get_cover, get_manual, get_rom_screenshots and PC metadata-selection execution reproduced deletion or corruption of prior good files after 503, invalid MIME, invalid image content, ReadError and ReadTimeout.

Extracted the existing shared streaming seam from scan_media_publication.py into resource_download.py. The publication module re-exports its existing entry point. No parallel downloader, HTTP client, storage resolver or authority was added. Existing ScreenScraper throttle and mapped/local reads remain in use.

Non-scan downloads now use the existing descriptor-relative OwnedReplace.binary_file capability. Response validation, complete streaming, image loading/chroma-key checks, resize and optional WebP transformation happen against staging. A pre-publication failure aborts staging and preserves the old final bytes. Cover responses keep their existing PNG paths and optional WebP sidecars; manuals retain their existing direct-child/fallback contract. Publication failures propagate.

Two directly necessary caller/capability corrections were proved separately:

- OwnedReplace.binary_file previously unlinked its PID-named temporary even when O_EXCL failed before creating it. A real existing private-file collision reproduced that deletion. Cleanup now checks whether this invocation created the temporary. Only this method changed; no new prepared-replacement authority or stable-output protocol was introduced.
- A failed non-scan screenshot refresh previously returned deterministic 0.jpg even when the authoritative screenshot was a committed scan generation. The getter now returns the existing inventory when a download returns None. Three real SQL/filesystem regressions exercise status, MIME and stream failure after a valid generation was committed.

The storage_access.py ownership correction is the exact extra runtime deviation required by CR-01's private-only abort guarantee. The legacy module received three net logical lines, not a new responsibility.

### CR-06: Optional transport boundaries

Verified HTTPX ConnectError, ReadTimeout and ReadError through actual _identify_rom -> scan_rom, primary, special-video, badge, parent-provider and _enrich_pc_dlc_from_igdb execution. Each optional failure now retains old references/bytes and permits the next readable source to be indexed.

Only the five relevant optional-media catches in scan.py gained TransportError and DecodingError. Existing explicit fatal boundaries remain. Nine controls retain the real publication/fence and SQL association while injecting callback SQL/indeterminate failure, or perform actual repository cancellation during the local HTTPX request. All propagate to the caller. No authority predicate is mocked.

The next-game assertions inspect actual SQL ROM/file rows from the read-only synthetic soundtracks directory, not a substituted scanner. DLC tests first commit valid provider media, then fault a real HTTPX stream and verify retained rows and exact bytes.

### CR-07: Strict bounded gzip completion

The original decoder accepted incomplete members, mixed decoded and raw bytes after corruption, and dropped later concatenated members. Both manual and video regressions proved incorrect publication; the actual special-video scanner proved incorrect catalog association.

_response_chunks now validates every declared gzip member, including trailer integrity and final eof, and bounds each decoded write to 1 MiB. Concatenated members and split headers are supported. A bad later member, corrupt trailer, truncation, extra raw trailer or mislabeled plain body fails before finish/publication. There is no decoded-to-raw fallback.

Plain identity responses remain compatible. No caller or existing test established a need to accept a plain body advertised as gzip, so that case is rejected before publication instead of guessing from partially emitted output. Unknown content encodings also fail closed. No arbitrary video/audio whole-body buffer was introduced.

Prepared bytes, decoding and validation stay outside the SQL publication lock. Real complete-stream controls cover identity, gzip, concatenation, empty complete members and split headers. A spy on the actual capability file verifies bounded writes and SHA-256 for a 56 MiB decoded output while the real capability and SQL association remain in use.

## Commits

All hashes resolve on the current canonical branch. Each commit used normal hooks.

| Commit | Scope |
| --- | --- |
| 54d8d27aa | CR-01 initial behavioral RED |
| d9dc9f9d3 | CR-01 staged replacement and coherent extraction |
| b539b9615 | Initial CR-06 tests; valid DLC RED, scanner fixture incomplete |
| 0def7782d | Corrected complete scanner fixture, actual CR-06 RED and fatal controls |
| fbfd98913 | CR-06 optional transport catches |
| 4dc7fcf8f | CR-07 bounded behavioral RED and exact test-file cleanup fixture |
| 196eb9c65 | CR-07 strict streamed member completion |
| cef419c36 | CR-01 foreign staging collision RED |
| 3e1ace932 | CR-01 private staging ownership correction |
| 03c82ca32 | CR-01 committed screenshot fallback RED |
| 5f1fdd58e | CR-01 screenshot fallback correction |
| f7b2ba757 | Restored two misplaced new collision assertions to their owning test |
| 7da945bfb | Final test typing/import and real-file spy cleanup |

5f1fdd58e was committed before the following fixture NameError was diagnosed. It is not presented as a verified GREEN point by itself. f7b2ba757 restored both assertions, and the subsequent 20-case and full 362-case runs passed. No original assertion was removed or weakened.

## RED/GREEN commands and retained evidence

All backend commands used only:

    PYTHONDONTWRITEBYTECODE=1 python3 backend/tools/phase34.py backend <listed test paths and options>

Each root below contains evidence/, with commands.json, logs, source-before.json, source-after.json and cleanup.json. Completed pytest runs also retain backend.xml. Existing receipts were not rewritten.

| Stage | Test paths/options after backend | Outcome | Linux root |
| --- | --- | --- | --- |
| CR-01 valid RED | tests/handler/test_media_download_replacement.py -q | 15 failed, 1 passed | /tmp/pgdp34-beac6d0ffc3c43618bb697d61ee25ca0-mws7q3eu |
| CR-01 first GREEN | resource-handler tests, then replacement tests, -q | 116 passed | /tmp/pgdp34-d9d52086de6c4ea4a019fdfc1bcc16a9-s1vpgtwz |
| CR-06 corrected RED | tests/handler/test_media_download_transport.py -q | 15 transport failures, 9 fatal controls passed | /tmp/pgdp34-bce47221711e43d095ddac30a964d63e-bmmngszo |
| CR-06 GREEN | same file, -q | 24 passed | /tmp/pgdp34-a27e9ff3f938440584c0ecf63eb9786d-5d26eflm |
| CR-07 bounded RED | tests/handler/test_media_download_gzip.py -q | 28 failed, 5 passed | /tmp/pgdp34-09493ff23ade4c1ebc802e1eaccae3f1-2btgq8g6 |
| CR-07 GREEN | same file, -q | 33 passed | /tmp/pgdp34-3141450f4dd3454a84499e9d182535c7-geqrwgdp |
| Private collision RED | replacement file, -k collision -q | 1 failed, 16 deselected | /tmp/pgdp34-24aa6bfc5d374c23b5a0364338a330a7-g5y06t47 |
| Private collision GREEN | replacement, resource-handler and storage-access files, -q | 181 passed | /tmp/pgdp34-8049c19bd09c4cd7aa553d721e93d8e4-odqnipkz |
| Initial combined GREEN | original eight files plus three new files, -q | 359 passed | /tmp/pgdp34-a27642d52ffe4e6cbe88adc8852192e5-qz0haw60 |
| Generation fallback RED | replacement file, -k committed_generation -q | 3 failed, 17 deselected | /tmp/pgdp34-d06a615106a04ebf89ad3aa1a6e53ff4-gvawb7xy |
| Corrected replacement GREEN | replacement file, -q | 20 passed | /tmp/pgdp34-fcece3c64186427f8c634242b3fe7c85-irj9kwbq |
| Final full GREEN | exact command below | 362 passed, 0 failed/errors/skipped, 76.73 seconds | /tmp/pgdp34-aac6e4b5048d4db8a78ad761bd1fd84b-ge3ncb_q |
| After final test-only static fixes | all three new test files, -q | 77 passed, 0 failed/errors/skipped, 35.47 seconds | /tmp/pgdp34-91262e4c31dc4720b8291e80dc363dc1-rqjxf28f |

Exact full command:

    PYTHONDONTWRITEBYTECODE=1 python3 backend/tools/phase34.py backend tests/handler/filesystem/test_resources_handler.py tests/handler/filesystem/test_storage_access.py tests/tasks/test_owned_media_cleanup.py tests/handler/metadata/test_steam_owned_media.py tests/handler/metadata/test_rom_media.py tests/handler/test_persist_soundtrack_cover.py tests/handler/test_scan_write_fence.py tests/handler/test_scan_media_publication.py tests/handler/test_media_download_replacement.py tests/handler/test_media_download_transport.py tests/handler/test_media_download_gzip.py -q

The final full run includes the unchanged original 285 cases plus 77 new cases (20 replacement, 24 transport, 33 gzip). Both successful final runs retain the two existing Alembic/SQLAlchemy warnings. No -k exclusion was used at either final GREEN gate.

No host-test rerun or new 23-host-pass claim: runner and fixture files are unchanged, and execution was restricted to the authorized backend runner. The prior 23 host passes remain historical evidence, not this group's fresh result. No frontend/API schema changed.

### Invalid/intermediate attempts, not GREEN proof

- /tmp/pgdp34-8c7d88886de245d4986dd16d28e375bb-9xmo0v6v: initial endpoint-test import mistake, corrected before valid CR-01 RED.
- /tmp/pgdp34-6731547c76b84dd295e6f4e0601ba176-x35bn58l: attempted patch had not applied and new files polluted legacy empty-directory checks. Later exact per-test owned-file cleanup resolved test isolation.
- /tmp/pgdp34-aa7e33c6d0b14bc9bd7be46a9b8ea5c8-oqpbabtw, /tmp/pgdp34-65649fc4131c47b2982cb88c11565b9c-pfevnyah, /tmp/pgdp34-d1b00473e32d49de978217ef248b3f8c-7bdkhyz7 and /tmp/pgdp34-df10f49dbe6449eaa44a60c72dfd4252-j42ib4ak: incomplete achievement fixtures prevented scanner entry. Only the DLC transport failures in the RED attempts are valid behavior proof. The complete-fixture RED listed above replaced these as scanner proof.
- /tmp/pgdp34-887210cf1d2344ada2e7a70c4f2657f3-h_3qapbz: actual scans continued, but the test tried to lazy-load Rom.files contrary to its raise-loading contract. It now reads through the real repository; no assertion was removed.
- /tmp/pgdp34-bed1ebf7c1bc4330b40fa32f61c5c1c5-xfreu4rg: original gzip fault run exceeded the 180-second runner limit. Cleanup passed; it is neither RED nor PASS. The later bounded per-case run established actual RED.
- /tmp/pgdp34-7c1f6acbcda24b9c871416c098cc76a5-100kbp61 and /tmp/pgdp34-aba9782e88544aa0aaae024828dac67c-myugco7h: three new test NameErrors from misplaced collision assertions; the latter had 359 passes. Both assertions were restored to the collision case, followed by the valid 20/362/77 GREEN runs.

Failed patch applications made no partial source changes. Infrastructure, fixture errors and timeouts are not counted as behavioral RED or passing verification.

## Static checks, decomposition and cleanup

Scoped Trunk formatting, git diff --check and final Trunk check against ccc92d366 passed with no new diagnostics on the nine exact changed Python files. Three inherited scan.py findings remain outside scope. Normal source/test commit hooks passed. A first scoped check found five new test-only import/type diagnostics; these were repaired and the fresh 77-case run passed afterward.

Static evidence is additive under the final full run's evidence/: group1-static.log retains the initial five issues; group1-static-final.log retains the passing result. These do not modify the runner's original source/cleanup receipts.

Logical lines, using nonblank/noncomment counts:

| File | Logical lines |
| --- | ---: |
| handler/filesystem/scan_media_publication.py | 353 |
| handler/filesystem/resource_download.py | 171 |
| tests/handler/media_download_helpers.py | 84 |
| tests/handler/test_media_download_replacement.py | 167 |
| tests/handler/test_media_download_transport.py | 298 |
| tests/handler/test_media_download_gzip.py | 259 |

All paths in the table are below backend/. The new runtime seam and all new handwritten test/helper modules stay below 500. The 1,492-line original publication test was not enlarged. Existing resources_handler.py and scan.py changes are narrow delegation/caller corrections. The legacy storage capability change is confined to exact temporary ownership on abort.

Final full cleanup.json: clean=true, source_unchanged=true. Exact containers removed: 7e94a6afedaf, 0099df9b9ed2, ec2487038a63. Exact volumes removed: pgdp34-aac6e4b5048d4db8a78ad761bd1fd84b_node_modules and pgdp34-aac6e4b5048d4db8a78ad761bd1fd84b_owned. Exact network removed: 60a73f7d5c3c. All remaining resource lists empty.

That run's source-before.json and source-after.json both hash to dcd02c5650ded8e551691d1c6bb42b435b4b41241f228fa09ea106f16e92d495.

Final 77-case cleanup also reports clean=true, source_unchanged=true and empty remaining lists. It removed cbb89827f2ad, 64ae6fb9e197, 2a122461ef0c, its exact two run-named volumes and network b7ae45995568. Final read-only Docker label inventory found no Phase 34 containers, volumes or networks. No global prune was used.

No new endpoint, schema, trust authority or goal-blocking stub was introduced. HTTP privacy is not claimed: 08 still owns real nginx exclusions and HTTP evidence. No auth gate occurred.

## Self-check

All listed source/test files and commits were verified on the canonical branch. Original media/fence tests, runner files, shared tracking, review and completed summary have no committed diff from ccc92d366. Required RED/GREEN, exact cleanup and source-unchanged receipts exist. Only the explicitly scoped source/tests and this note were staged. The original unrelated dirty paths remain.

Group 1 is ready for the parent to serialize the next correction group. CR-02/03/04/05/08/WR-01 and independent review remain outstanding; Phase 34 and Phase 33 acceptance are not closed.
