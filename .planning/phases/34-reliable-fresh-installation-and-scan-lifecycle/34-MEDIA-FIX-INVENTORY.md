# Phase 34 Media Fix: CR05 Sealed Descriptor Continuation Checkpoint

Date: 2026-10-19. Scope: bounded Group 3 CR-05 only, resumed after 5cf542a65
and parent decision c0a0d4f27. Status: CHECKPOINT. CR-05 remains OPEN.

This additive checkpoint preserves 34-MEDIA-FIX-CATALOG.md and its failure
history. It is not a SUMMARY, GREEN source commit, independent review, Group 3
acceptance, phase completion or Phase 33 acceptance.

## Result and concrete blocker

The new behavioral RED commit is e0491bf0e:
test(34-15): expose sealed media descriptor and substitution failures.
Normal Trunk commit hooks passed. Only the exact new test file was staged.
No runtime correction is committed or claimed verified.

The first draft run passed the real accepted 1,000-image Steam inventory,
the 96-descriptor process-limit case, 65 two-badge scanner inventory, late
stream/cancellation/association failures, receipt bounds/schema compatibility,
and both unchanged original sql-badge and indeterminate-badge fatal controls.
It nevertheless failed three new same-inode modified-private cases.

The final bounded compatibility run is 83 tests, 81 passed, 2 failed, zero
errors/skips, 8.189 seconds. All 64 existing storage-access cases passed.
The two failures are:

- test_abort_preserves_substituted_private[True-modified]
- test_recovery_retains_sealed_substitution[modified]

The earlier 59-case run also failed
test_sealed_publication_rejects_substitution_before_sql[modified].
Its later timing-dependent pass is not proof of a fix.

The actual Linux kernel is 5.15.0-191-generic. A diagnostic against actual
disposable owned files established that a same-length write followed by
restoring mtime can leave size, mtime_ns and ctime_ns identical to the sealed
snapshot. One actual pair was:

    before: (20, 1792417843960344960, 1792417843960344960)
    after:  (20, 1792417843960344960, 1792417843960344960)

The bytes changed from complete owned bytes to modified owned bytes.
The original inode and parent also stayed the same. This is behavioral evidence,
not a mocked stat, authority predicate or source-text test. The temporary
safe timestamp diagnostic was removed after its retained run.

Consequently, parent/file inode plus size/mtime/ctime is not sufficient
unchanged-content proof on this host. The current draft can publish or delete
modified private bytes during the same timestamp interval. It must not ship.
The Linux documentation explains the historical same-jiffy timestamp behavior:
https://docs.kernel.org/filesystems/multigrain-ts.html

## Required next decision

The approved internal prepared lifecycle extension remains authorized.
This checkpoint does not ask for that permission again.

The unresolved boundary is a stronger bounded content-proof mechanism that
survives descriptor release and remains valid at publication and exact cleanup.
It must handle same-inode modification as well as substitutions, without hashing
arbitrary media under SQL locks, reopening all inventory descriptors at once,
raising file limits or weakening original assertions.

A fresh hash only before taking SQL locks does not by itself close the gap
between that hash and reopening for publication when timestamps can coincide.
Another inode/timestamp comparison is therefore insufficient. A new trusted
immutability/change-proof primitive needs an explicit design decision before
adding it to the authority. An internal notification hint alone must not be
assumed complete content proof for every filesystem modification path.

Alternatively, changing the explicit no-hashing-under-SQL-lock requirement
would require the parent's instruction. No such change was inferred or made.
No new endpoint, database schema, resolver or user-facing API is proposed.

## Preserved draft implementation

All previous CR-05 drafts were reused and remain intact in the working tree.

- Extracted PreparedOwnedFile, _OwnedStagedPublication and the indeterminate
  exception coherently into owned_publication.py. storage_access.py re-exports
  the existing symbols and binds prepared locators from open_owned_access.
- finish flushes/fsyncs, hashes in 1 MiB chunks outside SQL, records ownership
  and releases file/parent descriptors. Finished outputs retain zero descriptors.
  Publication and abort reopen one exact generated private object at a time.
- Reopening uses the existing no-follow owned capability and root policy with
  parent/file identity checks. Abort and rollback check exact inode ownership.
  These checks are useful but insufficient for unchanged same-inode content.
- The existing ScanMediaBatch.publish_and_associate method is again the one
  inherited shared seam. Inventory supplies its bounded units through
  _publication_units, preserving the original fatal badge injection controls.
- Pending schema 2 fingerprints and multi-receipt inventory remain. MAX_OUTPUTS
  stays 128 and MAX_MANIFEST_BYTES stays 128 KiB. Reservation accounts for
  completed digest/size/private ownership evidence before accepting an output.
- Receipt validation and recovery cross-link optional exact parent/file/sealed
  evidence. Legacy schema 1 parsing and exact final recovery controls still
  pass. Legacy private digests use existing bounded hashing before SQL locks.
  The new private metadata proof has the same unresolved timestamp weakness.
- Inventory publication still uses one checked SQL association transaction.
  No output truncation, partial catalog inventory, provider-contract limit
  increase or new storage/deletion authority was introduced.

No old media, fence, transport, recovery or storage test assertion was changed.
The original 1,492-line publication test was not enlarged.

## Descriptor budget and module size

The new process-budget test runs only inside the guarded disposable harness.
It lowers the process RLIMIT_NOFILE soft limit to 96, stages/publishes 256 outputs,
asserts descriptors remain at most baseline plus 8 after every finish, then
restores the original soft/hard limits in finally. The passing draft run does
not raise any host or container file limit. The actual 1,000 valid image fixture
and large prior-reference inventory also passed without truncation.

The intended descriptor budget is zero per sealed output, one parent plus one
file during individual reopening, and bounded existing root traversal/snapshot
descriptors. It is independent of accepted inventory cardinality. This budget
is proved for the draft, not a security acceptance verdict.

Logical counts are nonblank, noncomment lines:

| File under backend/ | Physical | Logical |
| --- | ---: | ---: |
| handler/filesystem/owned_publication.py | 324 | 288 |
| handler/filesystem/scan_media_publication.py | 409 | 363 |
| handler/filesystem/scan_media_inventory.py | 37 | 30 |
| handler/filesystem/scan_media_manifest.py | 196 | 181 |
| handler/filesystem/scan_media_recovery.py | 317 | 287 |
| tests/handler/test_media_sealed_files.py | 194 | 171 |

The capability extraction reduces the legacy storage_access module instead of
adding another storage monolith. All new runtime and test/helper modules stay
below 500 logical lines.

## Actual commands and evidence

Every invocation used only the canonical existing guarded runner:

    PYTHONDONTWRITEBYTECODE=1 python3 backend/tools/phase34.py backend

Arguments after backend and actual outcomes:

1. tests/handler/test_media_sealed_files.py -q
   Initial real RED: 19 tests, 15 failed, 4 passed, no errors/skips, 6.800 seconds.
2. tests/handler/test_media_sealed_files.py tests/handler/test_media_inventory.py
   tests/handler/test_media_inventory_failures.py
   tests/handler/test_media_inventory_receipts.py
   tests/handler/test_media_download_transport.py -q
   Draft: 59 tests, 3 failed, 56 passed, no errors/skips, 81.170 seconds.
3. tests/handler/test_media_sealed_files.py -k modified -q
   Safe timestamp diagnostic: 3 selected, 2 failed, 1 passed, 16 deselected,
   no errors/skips, 2.288 seconds. Not a full-suite result.
4. tests/handler/filesystem/test_storage_access.py
   tests/handler/test_media_sealed_files.py -q
   Final bounded check: 83 tests, 2 failed, 81 passed, no errors/skips,
   8.189 seconds.

| Stage | Linux evidence root |
| --- | --- |
| New primitive behavioral RED | /tmp/pgdp34-89c6057d3e4f43e3ae36db5b846b1990-gkyyf70u |
| Draft inventory and fatal controls | /tmp/pgdp34-cea74fde524b4d0eabd41aef8736bc9b-k3bchbre |
| Actual unchanged timestamp diagnostic | /tmp/pgdp34-5f22ec7858d34bd990f56a6cf016d0c3-h88ycr4z |
| Final storage compatibility and unresolved failures | /tmp/pgdp34-d076727077914c7b8b5351ef8a439a76-sb32l8hk |

Each root retains evidence/commands.json, redacted logs, backend.xml,
source-before.json, source-after.json and cleanup.json. The diagnostic contains
only owned-file timestamps/identifiers, not environment or process arguments.

All four cleanup receipts report clean=true, source_unchanged=true and empty
remaining container, volume and network arrays. Source-before/source-after
SHA-256 values respectively match:

- RED: 1fef39f4a396af5437e26e9b96a3f48e69e8c38f7499c264959775b93fa6c9c1
- Draft: a065e14ac095a3a22d5d0e944c029a50345b57393572ced9695b89093104a89e
- Diagnostic: fe6535f59c52b50d9e10cf2bd22da88776a00fd90fe5bf3f46916c19df42007d
- Final: b15e6b3e9c6302d9c71b177d0d509bef3319eaeafb956416a9195589277106f7

Final exact cleanup removed containers b3dc72c411d1, 2bf8518ee407 and 6caa53d77a68,
the run's two named owned/node_modules volumes, and network 6ae7aef7f6b4.
The final read-only Phase 34 label inventory found zero resources of each kind.
No global prune, broad cleanup or source-library write occurred.

No unfiltered 443-case run, full 401 compatibility result, fresh PostgreSQL
regression or final CR-05 GREEN is claimed. The content-proof blocker must be
resolved before those outstanding required gates. Prior PostgreSQL evidence
in the catalog checkpoint remains historical and is not repeated as fresh proof.

## Static verification, containment and preservation

Scoped Trunk fmt passed. Final Trunk check --no-fix --no-progress --color=false
--upstream HEAD on all twelve current correction source/test paths reports
no new issues and three inherited issues. git diff --check passes.
Final logs and exact preserved/draft hashes are retained as
evidence/sealed-static.log and evidence/sealed-preservation.log under the final root.
The test RED commit used normal hooks. No unverified fix commit was created.

Before every test and at handoff pgdp-dev was exited with Running=false.
No restart, live SQL, dev.env, reset, scan, deployment or host Media write occurred.
The later fresh-UAT database recreation authority was not used.

Host Media controls were only statted. Size/mtime/ctime/inode remain:
lock (0, 1792411826.7119808100, 1792411826.7119808100, 294876);
cursor (2, 1792413626.7140350500, 1792413626.7180350830, 294888).
Their contents were not read or written.

SHA-256 preservation checks match the starting values for dirty STATE, Phase 33
UAT/VALIDATION, setup.py, both Compose files, ROADMAP, REQUIREMENTS, original
REVIEW, original 15 SUMMARY and Group 2 review. The new uncommitted
34-MEDIA-FIX-CATALOG-LOCKS-REVIEW.md remains untouched and unstaged, hash
da0dbb2610abdf2d3dc26f3b83b2e7a2e5dd2dbaa15388f0bfeb0cbea24ec634.
Untracked backend/pgdp_test/, pgdp_test/ and Media remain preserved.

All project writes used unified git apply over SSH stdin in the verified Linux
checkout. Canonical branch/origin/planning identity were repeatedly checked.
No Windows project file/copy, branch switch, worktree, nested agent, stash,
reset, broad staging, skipped hook, push or shared-state update occurred.

CR-02/08 commits 736836a80 and 3e2404aa5 were not redone. Independent CR-10 is
reserved for parent follow-up. Group 2 CR-09 and WR-02 remain separate and open.
Group 3, the original review, 03 worker/non-ROM fencing, 08 production/HTTP/browser
proof and Phase 33 acceptance are not cleared. Five summaries do not establish
phase quality acceptance. Parent retains STATE/ROADMAP/requirements ownership.

## Handoff self-check

The new test file and RED commit resolve. All four evidence roots contain actual
JUnit and clean exact-resource/source receipts. The runtime drafts remain
uncommitted and explicitly unverified. Original assertions and failure history
are retained. This exact checkpoint note is the only planning artifact added by
this continuation; no SUMMARY or shared completion update was created.
