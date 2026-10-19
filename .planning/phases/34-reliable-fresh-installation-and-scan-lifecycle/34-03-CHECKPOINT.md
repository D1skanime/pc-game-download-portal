# Phase 34 Plan 03: Scope checkpoint

Status: blocked at decomposition review, 0/3 tasks complete. No SUMMARY exists.
Date: 2026-10-19. Inspected HEAD: 37ccc9f5f.

## Verified environment

Linux over SSH team4s-linux. Root: /home/d1sk/pc-game-download-portal.
Branch: codex/phase-32-pgdp-naming.
Origin: https://github.com/D1skanime/pc-game-download-portal.git.
Compatibility CLI confirmed Phase 34 and completed 01/02/05. No branch switch, worktree, nested agent, live scan, reset, restart or deployment.

## Scope decision required

The plan's decomposition_review says: "if the actual persistence seam exceeds this budget, report an additional-plan need rather than omit commit fencing."

SQL fencing alone cannot satisfy Task 3's asset-publication requirement:

- backend/endpoints/sockets/scan.py:721 deletes published cover/manual/screenshots and special media for COMPLETE scans before replacement downloads.
- backend/handler/filesystem/resources_handler.py:326, :532, :711 and :868 stream/copy into final cover, screenshot, manual and special-media paths. Network work and publication share existing methods.
- backend/handler/filesystem/base_handler.py:382/:435 expose final-path writes without an operation/attempt publication transaction.
- backend/handler/filesystem/resources_handler.py:136/:208 publish parent/DLC media before separate catalog association transactions in roms_handler.py:680/:2942.
- backend/handler/scan_handler.py:339 and backend/utils/audio_tags.py:319/:354 write or delete deterministic soundtrack covers outside the resource writer.

These paths require a coherent publication extraction beyond the listed decorator/worker/socket seams. A check before download permits revocation during streaming. Holding the operation lock during download violates the task's network/lock constraint. Omitting publication fencing leaves Task 3 incomplete.

Proposed additional bounded plan: extract attempt-scoped owned-media staging/publication using existing storage capabilities; reuse downloaders and catalog handlers; handle deferred replacement/deletion and exact attempt-owned cleanup. Cover parent/DLC media, legacy resource paths and soundtrack covers. Keep new runtime modules below 500 logical lines. Add real SQL/filesystem cancellation races for revocation during download and both commit/cancel orderings. Specify publication/rollback semantics before worker integration. No second scanner, resolver or transport.

Additional scope: handler/filesystem/resources_handler.py, a focused publication module, handler/metadata/rom_media.py, handler/scan_handler.py, utils/audio_tags.py and publication tests. Review shared filesystem base handling to avoid affecting unrelated uploads. Watcher acceptance also belongs in backend/watcher.py:152; sync_folder_scan.py handles save synchronization, not library scans.

## Actual verification

From the verified Linux root:

    python3 backend/tools/phase34.py backend tests/endpoints/sockets/test_scan_job_identity.py -q

Exit 1. Pytest: 3 failed, 3 passed, 2 warnings in 1.26s. Failures: actual P34_RQ_RUNNING, P34_RQ_QUEUED and P34_RQ_STOP assertions. No GREEN claim or worker/cancellation race coverage.

Evidence: /tmp/pgdp34-1f47ca73705f4355a57f38d3a7b6612e-bnmncmhq/evidence.
Runner log: 13.log. cleanup.json: clean=true, source_unchanged=true, empty remaining resource lists. Independent exact project-label inventories found no containers, volumes or networks. Checkout snapshot removed; redacted evidence retained.

## Continuation

Resolve the additional publication-plan boundary, then execute all three tasks with real RED/GREEN gates. Acceptance/repository implementation was not rerun or changed. No dispatch/worker modules or task commits were created. Do not treat inventory as complete.

Unrelated dirty STATE, Phase 33 UAT/VALIDATION, setup response, Compose files and both pgdp_test directories remain untouched. Shared tracking is orchestrator-owned. No frontend work or browser acceptance.
