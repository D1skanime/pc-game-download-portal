# Codebase Concerns

**Analysis Date:** 2026-08-04

## Tech Debt

**ROM and file are the only persistent component boundaries:**

- Issue: A nested game directory is represented as one `Rom` plus a flat collection of `RomFile` rows. `RomFileCategory` provides broad content labels, but there is no component identity, install root, dependency relation, required/optional flag, launch role, or manifest revision in the current model.
- Files: `backend/models/rom.py`, `backend/handler/filesystem/roms_handler.py`, `backend/endpoints/responses/rom.py`, `frontend/src/__generated__/models/RomFileSchema.ts`
- Impact: A PC game split into base game, redistributables, DLC, patches, language packs, and optional extras cannot be selected or reconstructed deterministically from existing fields. Inferring components from `category` or path strings would make the API dependent on folder naming conventions.
- Fix approach: Add a narrow, explicit component abstraction owned by a ROM, then associate `RomFile` rows with components. Keep `RomFile` as the physical-file record and expose the new backend schema through `backend/endpoints/responses/rom.py`; regenerate `frontend/src/__generated__/` rather than hand-editing generated types.

**Category inference is path-name driven:**

- Issue: `_build_rom_file` assigns the first matching `RomFileCategory` when a lowercased directory segment equals a category value or its plural. Unmatched files receive `None`, and non-nested files are defaulted at response time rather than stored with an explicit component meaning.
- Files: `backend/handler/filesystem/roms_handler.py`, `backend/models/rom.py`, `backend/endpoints/responses/rom.py`
- Impact: Directories named `updates`, `mods`, or `dlcs` have implicit semantics, while arbitrary PC layouts do not. A modular PC scanner based only on this rule will misclassify ordinary directories and cannot distinguish two components of the same category.
- Fix approach: Preserve category as a presentation/filter attribute. Store component membership explicitly and make scanner discovery rules opt-in and deterministic, preferably through a sidecar manifest with a versioned schema.

**Download identity and display name are conflated in legacy routes:**

- Issue: ROM content routes accept a client-provided `file_name` path segment even though file selection is by ROM ID and optional file IDs. The direct file route correctly derives response type and name from the trusted database row, but the URL still suggests the name identifies content.
- Files: `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/endpoints/feeds.py`
- Impact: Manifest clients may persist decorative URLs, misunderstand rename stability, or accidentally rely on ignored names. File IDs can also be replaced during rescans, as documented by the stale-ID regression coverage.
- Fix approach: Define manifest entries with an opaque server identifier and a separate relative install path. Treat the display/download filename as metadata, not authorization or identity. Document whether IDs survive rescans; if stable resumability is required, add an immutable file-version identifier.

**ZIP cache validity uses database metadata, not file identity:**

- Issue: The cache key uses database `updated_at`, stored size, and download name. It does not hash current bytes or stat the source at cache lookup. The cache namespace and key are truncated SHA-256 identifiers, but those hashes protect naming, not content integrity.
- Files: `backend/utils/zip_cache.py`, `backend/endpoints/roms/__init__.py`, `backend/models/rom.py`
- Impact: Out-of-band file mutation can leave an old cached ZIP addressable until TTL cleanup, or build a ZIP whose bytes do not match the metadata used for its key. A component manifest must not reuse this key as a content digest.
- Fix approach: Give each downloadable file a content-version contract based on a strong digest plus size, or a verified stat tuple when hashing is intentionally deferred. Invalidate manifest revisions and cached artifacts when that contract changes.

**High-churn upstream hotspots:**

- Issue: The natural implementation seams are among the repository's most active files. The five main ROM model, scanner, endpoint, file endpoint, and ZIP cache paths have 212 commits in the six months visible in the current checkout. The local `master` is exactly aligned with `origin/master` at `071e82ada`, so this is ongoing upstream churn rather than local divergence.
- Files: `backend/models/rom.py`, `backend/handler/filesystem/roms_handler.py`, `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/utils/zip_cache.py`
- Impact: A long-lived feature branch that rewrites existing download or scan flows will accumulate conflicts and may silently lose upstream visibility, hashing, or media fixes during conflict resolution.
- Fix approach: Keep additions modular: new models and handlers, thin route registration, small extensions to scanner output, and focused tests. Rebase frequently on `master`, avoid formatting these hotspots, and preserve upstream fixes around `assert_rom_visible`, Range handling, archive hashes, and generated response types.

## Known Bugs

**Filesystem changes can make stored file metadata stale before download:**

- Symptoms: `file_size_bytes`, `last_modified`, and digests are scan-time database snapshots. Direct nginx responses and mod_zip manifests can serve the live path after the file has changed, been truncated, or been replaced without a rescan.
- Files: `backend/models/rom.py`, `backend/handler/filesystem/roms_handler.py`, `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/utils/nginx.py`
- Trigger: Modify a library file after scanning, then request it or request a multi-file ZIP before the watcher/rescan updates the row.
- Workaround: Rescan before generating or consuming a download manifest. A new manifest endpoint should detect stat drift and fail with a retryable conflict instead of emitting known-stale size or digest data.

**Development multi-file downloads buffer the complete archive in memory:**

- Symptoms: In development mode, each selected file is read fully and the complete ZIP is returned as one `bytes` object. Memory usage can exceed the total component size by a substantial margin.
- Files: `backend/endpoints/roms/__init__.py`
- Trigger: Download a multi-file directory ROM while `DEV_MODE` is enabled, especially a PC game with multi-gigabyte files.
- Workaround: Use the production nginx path. Do not base manifest download behavior on the development ZIP implementation; per-file downloads should remain streaming/file-backed.

## Security Considerations

**Configured symlinks weaken containment guarantees:**

- Risk: `FSHandler.validate_path` intentionally uses lexical containment when any path component is a symlink. This permits an in-library symlink to target content outside `LIBRARY_BASE_PATH`. Production file responses construct `/library/{file.full_path}` for nginx without calling `validate_path` at request time.
- Files: `backend/handler/filesystem/base_handler.py`, `backend/endpoints/roms/files.py`, `backend/endpoints/roms/__init__.py`, `backend/utils/nginx.py`, `backend/utils/filesystem.py`
- Current mitigation: Absolute paths and `..` segments are rejected. Database file IDs are resolved to their parent ROM, and `assert_rom_visible` masks hidden content. `os.walk` does not follow directory symlinks by default, but symlinked files can still be enumerated and served.
- Recommendations: Define whether symlinks are supported library content before shipping manifests. If supported, resolve and record the final target during scanning and constrain it to an explicit allowlist of storage roots. If unsupported for component downloads, reject any symlink in the full path using `lstat`/`openat` semantics. Validate before issuing `X-Accel-Redirect`, and test intermediate-directory links, leaf links, broken links, and link retargeting between validation and open.

**Path traversal protection is not sufficient for manifest install paths:**

- Risk: Existing `validate_path` protects server-side relative paths, and `_sanitize_filename` strips directory components. A component manifest necessarily preserves relative directory structure, so applying filename sanitization would destroy layout while accepting raw paths would expose clients to `../`, absolute paths, drive prefixes, UNC paths, alternate separators, control characters, and case-collision attacks.
- Files: `backend/handler/filesystem/base_handler.py`, `backend/utils/filesystem.py`, `backend/models/rom.py`, `backend/endpoints/roms/files.py`
- Current mitigation: Server paths reject explicit parent components and absolute `pathlib.Path` values. Direct response names come from database records. Existing safeguards are server-oriented and do not define a portable client extraction/install policy.
- Recommendations: Validate manifest paths as POSIX-relative logical paths independent of host OS. Reject empty, dot, parent, absolute, drive/UNC, NUL/control, and separator-confusable segments. Specify Unicode normalization and case-collision behavior. Authorize by server-side file ID and derive the returned path from a trusted scanned row, never from a request path.

**Download authorization can be globally disabled:**

- Risk: `DISABLE_DOWNLOAD_ENDPOINT_AUTH` removes the `ROMS_READ` scope requirement from content routes. Visibility checks remain in the current direct-file and ROM-content handlers, but unauthenticated permission behavior becomes part of the security boundary and new manifest routes could accidentally expose library structure or bytes.
- Files: `backend/config/__init__.py`, `backend/endpoints/roms/files.py`, `backend/endpoints/roms/__init__.py`, `backend/handler/auth/dependencies.py`
- Current mitigation: Current routes resolve the parent ROM and call `assert_rom_visible`; authenticated users are filtered through granular hidden-ROM/platform permissions. Endpoint tests cover direct file-ID visibility bypasses in `backend/tests/endpoints/roms/test_rom.py` and `backend/tests/endpoints/test_permissions_visibility.py`.
- Recommendations: Apply the same auth toggle and the same `assert_rom_visible` decision to both manifest issuance and every file request. Never treat possession of a manifest URL as authorization unless URLs are explicitly short-lived and signed. Add tests for anonymous mode, hidden ROMs, hidden platforms, stale file IDs, files belonging to another ROM/component, revoked permissions, and mixed authorized/unauthorized batch requests.

**Time-of-check to time-of-use races are unhandled:**

- Risk: The application authorizes a database row and then hands a path to Starlette or nginx. A file or symlink can be replaced, retargeted, truncated, or appended between scan, manifest generation, and byte serving. Stored size and hashes may then describe different bytes from those received.
- Files: `backend/endpoints/roms/files.py`, `backend/endpoints/roms/__init__.py`, `backend/handler/filesystem/base_handler.py`, `backend/utils/nginx.py`, `backend/utils/zip_cache.py`
- Current mitigation: Atomic writes are available for application-managed mutations in `FSHandler._atomic_write`, and ZIP cache construction writes to a temporary file before rename. Library files can still be mutated externally, and nginx opens them after the application response.
- Recommendations: Put immutable version metadata in manifests. Re-stat immediately before response, return `409` or `412` on mismatch, emit a strong ETag where the digest is known, and require clients to verify the final digest. For high assurance, serve a content-addressed immutable snapshot or open a file descriptor securely and stream that descriptor rather than re-opening a mutable path.

**Manifest contents can disclose the full PC installation layout:**

- Risk: Relative paths, executable names, DLC names, and file hashes reveal more information than the existing high-level ROM record. Broad ROM read access currently implies file download access, but a manifest makes enumeration cheap and structured.
- Files: `backend/endpoints/responses/rom.py`, `backend/endpoints/roms/files.py`, `backend/models/permission.py`, `backend/handler/auth/dependencies.py`
- Current mitigation: ROM and platform visibility controls exist, with `ROMS_READ` on authenticated download routes.
- Recommendations: Keep manifest access at least as restrictive as byte access, avoid embedding server absolute paths, do not expose nginx internal paths, and log manifest issuance without logging sensitive full path lists.

## Performance Bottlenecks

**Recursive scanning and hashing scale with every component file:**

- Problem: Folder ROMs are recursively enumerated with `os.walk`. When hashing is enabled, files are read and CRC32, MD5, and SHA-1 are calculated, while archive paths may decompress content. Per-file work is dispatched through `asyncio.to_thread`, but a PC tree can contain hundreds of thousands of small files or very large archives.
- Files: `backend/utils/filesystem.py`, `backend/handler/filesystem/roms_handler.py`, `backend/utils/archives.py`, `backend/endpoints/sockets/scan.py`
- Cause: The scanner assumes a console-style ROM has a tractable file count and that metadata hashes are useful. Windows, Linux, and macOS are explicitly in `NON_HASHABLE_PLATFORMS`, so current PC scans trade integrity metadata for speed.
- Improvement path: Separate component indexing from metadata-provider hashing. Use bounded concurrency, configurable file-count and byte budgets, incremental stat-based reuse, cancellation points, and progress reporting. Compute the manifest's strong digest in a background pipeline only when required, and persist an explicit pending/verified/failed state.

**Strong hashing is an additional full read for large PC files:**

- Problem: Existing file records store CRC32, MD5, SHA-1, and CHD-specific SHA-1, but PC platforms normally skip these hashes. A secure download manifest needs a collision-resistant digest such as SHA-256, which requires reading every byte unless supplied by a trusted ingest process.
- Files: `backend/models/rom.py`, `backend/handler/filesystem/roms_handler.py`, `backend/utils/hashing.py`
- Cause: Metadata matching and download integrity have different goals. Reusing MD5/SHA-1 would provide inconsistent coverage and weaker integrity guarantees, while synchronously adding SHA-256 to scans would make large-library scans I/O-bound for long periods.
- Improvement path: Add one canonical integrity algorithm and digest state for manifest files. Hash in chunks off the event loop, cap concurrent disk readers, resume/reuse results when stable size and modification identity match, and surface unverified files explicitly rather than emitting an empty digest as if valid.

**Range support differs by route and environment:**

- Problem: Single-file downloads rely on Starlette Range behavior in development and nginx Range behavior in production. Multi-file ZIP downloads only build a cached seekable ZIP after receiving a Range request; normal downloads use mod_zip streaming. The application itself does not parse or validate ranges.
- Files: `backend/endpoints/roms/files.py`, `backend/endpoints/roms/__init__.py`, `backend/utils/nginx.py`, `backend/utils/zip_cache.py`
- Cause: Byte serving is delegated to different servers. A manifest client that resumes per-file downloads will observe infrastructure-dependent headers and error behavior unless the contract is tested end to end.
- Improvement path: Keep component transfer per physical file and preserve nginx/Starlette delegation. Specify `Accept-Ranges`, `206`, `Content-Range`, `416`, ETag/If-Range, HEAD parity, and zero-byte behavior. Test both development and production nginx configurations with first, middle, suffix, open-ended, invalid, and stale-If-Range requests on files larger than 4 GiB.

**ZIP caching can duplicate very large libraries on disk:**

- Problem: A Range request for a multi-file or bulk download may materialize a full `ZIP_STORED` copy. Archives above 8 GiB receive a shorter 12-hour TTL, but there is no reservation, quota, deduplication across namespaces, or preflight free-space check.
- Files: `backend/utils/zip_cache.py`, `backend/endpoints/roms/__init__.py`
- Cause: Resumability is achieved by caching a complete archive. PC component packages can be tens or hundreds of gigabytes.
- Improvement path: Prefer manifest-driven per-file Range downloads for PC content. Do not create component ZIPs by default. If packaging remains available, enforce cache quotas and coordinate concurrent builders for the same key.

## Fragile Areas

**Scanner's top-level ownership assumption:**

- Files: `backend/handler/filesystem/roms_handler.py`, `backend/utils/filesystem.py`, `backend/endpoints/sockets/scan.py`
- Why fragile: Every immediate file or directory under a platform ROM folder becomes one ROM. Every descendant of a directory ROM becomes a `RomFile`, subject only to global exclusions and category heuristics. Launcher files, installers, caches, logs, redistributables, and mutable saves can therefore be swept into one immutable-looking game payload.
- Safe modification: Introduce a versioned, opt-in PC layout detector. Keep current console behavior unchanged. Define include/exclude precedence, component roots, symlink handling, mutable-data exclusions, and behavior for missing or malformed manifests before altering `get_roms` or `get_rom_files`.
- Test coverage: Existing scanner tests cover ROM enumeration and hashes, but no contract covers modular PC component discovery, enormous directory trees, symlink loops/escapes, case-only duplicate paths, manifest conflicts, or files changing during enumeration.

**Direct nginx path construction:**

- Files: `backend/endpoints/roms/files.py`, `backend/endpoints/roms/__init__.py`, `backend/utils/nginx.py`
- Why fragile: Correctness depends on nginx internal-location configuration, URL quoting, the database path being trustworthy, and visibility checks occurring before the redirect. A seemingly harmless new endpoint can bypass Python containment by constructing `X-Accel-Redirect` directly.
- Safe modification: Centralize authorized library-file response creation in one helper that accepts a validated `RomFile`, enforces parent visibility, performs drift checks, chooses disposition, and emits the internal redirect. Do not let manifest request fields feed `download_path`.
- Test coverage: Endpoint tests assert the redirect header and visibility behavior, but repository tests do not exercise nginx opening the target, symlink retargeting, encoded separators, Range semantics, or mutation mid-transfer.

**File row replacement during rescans:**

- Files: `backend/endpoints/sockets/scan.py`, `backend/handler/database/rom_handler.py`, `backend/tests/endpoints/roms/test_rom.py`
- Why fragile: Scanner rebuilds can replace file rows, and current tests explicitly recognize stale file IDs after rename. Long-lived manifests can therefore point at deleted IDs or, if identifiers are ever reused externally, the wrong version.
- Safe modification: Bind manifests to a revision and immutable file-version IDs. Return an explicit expired/stale response when a component or file no longer belongs to that revision. Never silently substitute a same-name file.
- Test coverage: Stale `file_ids` are tested for ROM ZIP downloads, but there is no long-lived manifest lifecycle coverage.

**Private stdlib monkey patch in ZIP support:**

- Files: `backend/utils/zip_cache.py`, `backend/handler/filesystem/roms_handler.py`
- Why fragile: `_ensure_zipfile_writable` patches the private `zipfile._get_compressor` function to work around `zipfile_inflate64`. Python or dependency updates can change this private signature or global behavior.
- Safe modification: Keep manifest downloads independent of ZIP construction. If component packaging uses ZIP, isolate and regression-test this shim against the supported Python version and dependency lock.
- Test coverage: `backend/tests/utils/test_zip_cache.py` covers current behavior, but it cannot guarantee compatibility with future Python internals.

## Scaling Limits

**Manifest row and response volume:**

- Current capacity: No explicit component-manifest limit exists. Current detailed ROM responses can include all `RomFile` rows, and scanner enumeration materializes lists in memory.
- Limit: PC installations with very high file counts can create large database transactions, response bodies, generated client objects, and slow permission/serialization paths. URL query selection via comma-separated `file_ids` is also unsuitable for thousands of files.
- Scaling path: Paginate or stream manifest entries, provide a compact immutable manifest artifact, cap entries and path bytes, and use server-side component selection rather than huge query strings. Index component ownership and revision columns used by authorization and lookup.

**Very large individual files:**

- Current capacity: `file_size_bytes` uses `BigInteger`, nginx and Starlette can serve files, and ZIP cache tests recognize files above 8 GiB.
- Limit: No explicit tested ceiling covers 4 GiB boundary behavior, filesystem sparse files, reverse-proxy timeouts, client integer precision, or content hashing duration. JavaScript safely represents integers only through `2^53 - 1`.
- Scaling path: Define maximum supported file size, keep byte sizes as validated non-negative 64-bit values in the backend, verify generated frontend handling, and add production Range tests at 4 GiB and representative larger sizes without allocating equivalent in-memory buffers.

## Dependencies at Risk

**nginx mod_zip and X-Accel behavior:**

- Risk: Core download behavior depends on nginx modules and configuration outside the FastAPI response code. A manifest feature that assumes application-server semantics can pass unit tests but fail behind production nginx.
- Impact: Incorrect Range responses, bad quoting, inaccessible internal paths, or inconsistent headers can break resumable component installation.
- Migration plan: Treat nginx as part of the download contract. Add container-level integration tests and keep a FileResponse fallback for development, while avoiding mod_zip for manifest-driven per-file transfer.

**Generated OpenAPI frontend contract:**

- Risk: `frontend/src/__generated__/models/RomFileSchema.ts` is generated from backend response models. Manual frontend additions or partial schema changes will be overwritten or drift from runtime.
- Impact: Component and manifest fields may compile locally yet disappear during regeneration, or backend changes may break the active v2 UI.
- Migration plan: Change backend response schemas first, run the documented generation workflow, and commit generated changes with backend and frontend contract tests.

## Missing Critical Features

**Immutable, versioned component manifest:**

- Problem: There is no schema that binds a ROM revision to ordered components and per-file relative path, byte size, strong digest, download identifier, and required/optional status.
- Blocks: Safe selective installation, integrity verification, resumable synchronization, stale-manifest detection, and reproducible PC game assembly.

**Explicit mutable-file exclusion:**

- Problem: Current recursive directory scans can include any non-excluded descendant. PC installs commonly contain logs, caches, settings, saves, and generated files that should not be treated as distributable components.
- Blocks: Stable manifests and reliable hashes. The scanner needs manifest-controlled inclusions plus project-defined defaults before PC component packaging is trustworthy.

**File-version preconditions for resume:**

- Problem: Current downloads do not expose a manifest-specific immutable version token or require `If-Match`/`If-Range` against it.
- Blocks: Correct recovery when a file changes between chunks. A client can otherwise concatenate ranges from different versions.

## Test Coverage Gaps

**Containment and symlink matrix:**

- What's not tested: Manifest paths containing traversal forms, Windows drive/UNC forms, encoded separators, Unicode normalization collisions, leaf/intermediate symlinks, broken links, symlink loops, and symlink retargeting after authorization.
- Files: `backend/handler/filesystem/base_handler.py`, `backend/endpoints/roms/files.py`, `backend/tests/handler/filesystem/test_base_handler.py`, `backend/tests/endpoints/roms/test_files.py`
- Risk: Arbitrary server-file disclosure or client-side write outside the chosen install root.
- Priority: High

**Authorization parity across manifest and file routes:**

- What's not tested: Manifest issuance and subsequent per-file requests under anonymous download mode, hidden ROM/platform rules, revoked access, cross-ROM file IDs, mixed batches, and component membership changes.
- Files: `backend/handler/auth/dependencies.py`, `backend/endpoints/roms/files.py`, `backend/tests/endpoints/roms/test_rom.py`, `backend/tests/endpoints/test_permissions_visibility.py`
- Risk: Structured path disclosure or direct download of content the caller cannot browse.
- Priority: High

**Mutation and integrity lifecycle:**

- What's not tested: File replacement, truncation, append, same-size mutation, mtime rollback, and changes between manifest generation, HEAD, Range chunks, and final digest verification.
- Files: `backend/models/rom.py`, `backend/handler/filesystem/roms_handler.py`, `backend/endpoints/roms/files.py`, `backend/utils/zip_cache.py`
- Risk: Corrupt installations, mixed-version files, or a manifest digest that does not describe delivered bytes.
- Priority: High

**Large-file and Range conformance:**

- What's not tested: Production nginx behavior for valid and invalid ranges, `416`, suffix/open-ended requests, If-Range, HEAD parity, zero-byte files, disconnects, and files beyond 4 GiB.
- Files: `backend/endpoints/roms/files.py`, `backend/endpoints/roms/__init__.py`, `backend/utils/nginx.py`, `backend/tests/endpoints/roms/test_files.py`, `backend/tests/endpoints/roms/test_rom.py`
- Risk: Resume corruption or downloads that work in TestClient but fail in the deployed container.
- Priority: High

**PC scanner component semantics:**

- What's not tested: Versioned sidecar parsing, overlapping component roots, optional components, deterministic ordering, missing files, extra files, duplicate/case-colliding paths, exclusion precedence, and huge trees.
- Files: `backend/handler/filesystem/roms_handler.py`, `backend/utils/filesystem.py`, `backend/tests/handler/filesystem/test_roms_handler.py`
- Risk: Files attach to the wrong component, mutable data enters manifests, or scans become prohibitively slow.
- Priority: High

**Upstream integration regression suite:**

- What's not tested: A narrow suite that locks down existing console ROM scanning, single/multi-file downloads, feeds, archive metadata, visibility, and ZIP behavior while PC component logic evolves.
- Files: `backend/tests/handler/filesystem/test_roms_handler.py`, `backend/tests/endpoints/roms/test_rom.py`, `backend/tests/endpoints/roms/test_files.py`, `backend/tests/utils/test_zip_cache.py`, `backend/tests/endpoints/test_permissions_visibility.py`
- Risk: Merge conflict resolution or upstream refactors silently change legacy behavior while the feature branch still passes only new PC-focused tests.
- Priority: High

---

_Concerns audit: 2026-08-04_
