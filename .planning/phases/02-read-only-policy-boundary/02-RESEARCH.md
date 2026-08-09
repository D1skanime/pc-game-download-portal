# Phase 2: Read-only Policy Boundary - Research

**Researched:** 2026-08-09
**Domain:** Deny-by-default filesystem authorization for immutable external roots
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use explicit, fine-grained operation capabilities rather than broad read/write groups.
- **D-02:** The external-root allowlist is closed. It contains only `LIST`, `STAT`, `READ`, `SCAN`, `HASH`, `STREAM`, `DOWNLOAD`, and the explicitly named safe resolution capability.
- **D-03:** Unknown and newly introduced operations fail closed until explicitly classified and allowed.
- **D-04:** Policy decisions use the requested operation and a trusted storage classification. Caller-supplied path text must never determine the storage class.
- **D-05:** Authorize source reads and destination writes independently. A read grant must never imply permission to write.
- **D-06:** Temporary and generated output may be written only to explicitly classified RomM-owned storage, never merely to any path outside an external root.
- **D-07:** Model copying from an external source as an authorized external read plus a separate authorized RomM-owned write. An external root can never be the copy destination.
- **D-08:** Extraction, patching, conversion, and similar transformations may use external bytes only as input. All generated or modified bytes must land in RomM-owned storage; in-place processing and write-back are forbidden.
- **D-09:** Use one typed policy-denial error with a stable machine-readable code. API, job, and internal callers translate the same domain error for their channel.
- **D-10:** Direct API denials return HTTP 403 with the stable error code.
- **D-11:** Background jobs and internal workflows fail immediately and visibly. They must not skip the denied step, silently fall back, redirect to another path, or report partial work as success.
- **D-12:** Externally visible denial details are limited to the operation, storage class, and logical root or mapping identifier. Do not expose absolute paths, relative paths, filesystem details, or unrelated mappings.
- **D-13:** Enforce policy at the lowest common filesystem boundary. Endpoints, handlers, and jobs must not access an external root through raw resolved paths.
- **D-14:** Successful authorization returns an operation-bound capability or handle, not a freely reusable absolute path. The capability exposes only the approved operation.
- **D-15:** Maintain a complete inventory of existing mutation paths. Every path must use the policy or be structurally and testably restricted to RomM-owned storage. Any unclassified path blocks phase completion.
- **D-16:** Run the same denial matrix against a writable fixture and a container-mounted read-only fixture. Tripwires must prove that a denial occurs before `stat`, `open`, enumeration, or mutation reaches the target filesystem.

### Agent's Discretion

The exact Python names, module boundaries, capability representation, error-code spelling, and test organization are left to research and planning, provided they preserve D-01 through D-16.

### Deferred Ideas (OUT OF SCOPE)

None. Discussion stayed within the Phase 2 boundary.
</user_constraints>

<phase_requirements>

## Phase Requirements

| ID                    | Research Support                                                                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ROOT-05               | Explicit owned-storage classification and startup disjointness, never negative path inference. [VERIFIED: requirements and `backend/config/__init__.py`] |
| SAFE-01/02            | Closed `StorageOperation` enum and operation-specific capabilities; pure denial precedes all I/O. [VERIFIED: D-01 through D-04, D-16]                    |
| SAFE-03               | One domain denial translated to bounded HTTP 403. [VERIFIED: D-09, D-10, D-12]                                                                           |
| SAFE-04               | Inventory below covers common handler, endpoints, tasks, utilities, migrations, and watcher seams. [VERIFIED: codebase grep 2026-08-09]                  |
| SAFE-05               | Example and test Compose use `:ro`; same matrix also runs writable. [CITED: https://docs.docker.com/engine/storage/bind-mounts/]                         |
| SAFE-06               | External capabilities have no write method; generated output needs a separate owned grant. [VERIFIED: D-05 through D-08]                                 |
| TEST-03               | Parameterized mutation matrix, source manifests, symlink races, and pre-access tripwires. [VERIFIED: requirements]                                       |
| </phase_requirements> |

## Summary

Add a small policy kernel beside the Phase 1 resolver. It accepts a trusted `StorageRoot` or explicit RomM-owned descriptor plus one `StorageOperation`, rejects unknown combinations before I/O, and returns a narrow capability. External capabilities own already-open descriptors and expose only their approved behavior, never an absolute path. [VERIFIED: D-01 through D-14]

`FSHandler` is unsafe for external roots because construction calls `mkdir`, `validate_path` returns a path, and the class combines reads with create, write, copy, move, and delete. Library handlers bind it to `LIBRARY_BASE_PATH`; resource and asset handlers use separate roots. [VERIFIED: `backend/handler/filesystem/*.py`] Keep owned handlers behind explicit owned classification, but prohibit external capability construction through `FSHandler`.

`Path.resolve()` is only a point-in-time administration check. Access should open the trusted root, then each component relative to the prior directory FD using `O_DIRECTORY`, `O_NOFOLLOW`, `dir_fd`, and `fstat`. Because `O_NOFOLLOW` covers only the final component of one call, every component must be opened separately. [CITED: https://docs.python.org/3/library/os.html] [CITED: https://man7.org/linux/man-pages/man2/openat.2.html] Linux `openat2` is stronger and available since Linux 5.6, but Python does not directly expose it, so a native wrapper adds avoidable risk. [CITED: https://man7.org/linux/man-pages/man2/openat2.2.html]

**Primary recommendation:** Add `storage_policy.py` for pure fail-closed decisions and `storage_access.py` for descriptor opening; return operation-specific capabilities, classify writable destinations explicitly, and block completion until inventory and dual-fixture evidence are green.

## Architectural Responsibility Map

| Capability          | Primary Tier        | Secondary Tier | Rationale                                                                            |
| ------------------- | ------------------- | -------------- | ------------------------------------------------------------------------------------ |
| Authorization       | Backend domain      | Storage        | Trusted identity plus operation only. [VERIFIED: D-04]                               |
| Race-safe access    | Filesystem boundary | Backend        | Lowest common boundary owns descriptors. [VERIFIED: D-13, D-14]                      |
| API/job translation | Presentation/worker | Domain         | Channel-specific status, shared error. [VERIFIED: D-09 through D-12]                 |
| Writable separation | Config/storage      | Docker         | Code classifies roots; mount supplies defense in depth. [VERIFIED: ROOT-05, SAFE-05] |

## Project Constraints (from AGENTS.md and CLAUDE.md)

- Canonical work is on `team4s-linux:/home/d1sk/romm`; Windows is not evidence. [VERIFIED: `CLAUDE.md`]
- Follow endpoint to handler to filesystem/database layering and typed exceptions. [VERIFIED: backend skill]
- New logic needs tests; run `uv run pytest` and Trunk, never bypass hooks. [VERIFIED: `CLAUDE.md`]
- API schemas remain backend-owned; regenerate frontend types for contract changes. [VERIFIED: `CLAUDE.md`]
- English only, no em dash, no secrets, no Team4s/NAS/service changes. [VERIFIED: project instructions]

## Standard Stack

| Library/API                    |         Version | Purpose                                                                    | Evidence                                                                        |
| ------------------------------ | --------------: | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Python `os` descriptor APIs    |          >=3.13 | `open`, `fstat`, `read`, `scandir`, `dup`, `close`, `dir_fd`, `O_NOFOLLOW` | [CITED: https://docs.python.org/3/library/os.html] [VERIFIED: `pyproject.toml`] |
| Phase 1 storage model/resolver |   revision 0108 | Trusted identity, normalization, admin validation                          | [VERIFIED: Phase 1 verification 14/14]                                          |
| FastAPI / Starlette            | 0.134.0 / 1.0.1 | HTTP translation and later streaming                                       | [VERIFIED: `uv.lock`]                                                           |
| pytest / pytest-asyncio        |   9.0.3 / 1.3.0 | Unit and integration tests                                                 | [VERIFIED: `uv.lock`]                                                           |
| Docker Compose                 |      5.3.1 host | Writable and `:ro` fixture parity                                          | [VERIFIED: environment probe]                                                   |

No new runtime dependency is required. [VERIFIED: recommended standard-library design]

## Architecture Patterns

```text
endpoint / RQ job / internal handler
        |
trusted storage identity + StorageOperation
        |
StoragePolicy.authorize() [pure, no I/O]
   | allow                         | deny
   v                               v
StorageAccess open FD      StoragePolicyDenied(code,...)
   |                               +--> HTTP 403
operation-bound capability         +--> terminal job failure
   |
external read FD + optional separate owned-write capability
```

Recommended files:

```text
backend/exceptions/storage_policy_exceptions.py
backend/handler/filesystem/storage_policy.py
backend/handler/filesystem/storage_access.py
backend/tests/handler/filesystem/test_storage_policy.py
backend/tests/handler/filesystem/test_storage_access.py
backend/tests/handler/filesystem/test_storage_inventory.py
backend/tests/endpoints/test_storage_policy_denials.py
backend/tests/tasks/test_storage_policy_denials.py
backend/tools/verify_read_only_policy.py
```

### Closed policy

Define every allowed and denied operation in `StorageOperation(StrEnum)`. The external allowlist contains exactly `RESOLVE`, `LIST`, `STAT`, `READ`, `SCAN`, `HASH`, `STREAM`, and `DOWNLOAD`. Any unhandled or non-enum value denies. [VERIFIED: D-01 through D-04] [ASSUMED: exact Python coercion behavior]

### Descriptor-bound access

Open the root `O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW`; normalize with Phase 1 code; open each intermediate component with the same flags and `dir_fd`; open leaf files `O_RDONLY|O_CLOEXEC|O_NOFOLLOW`; validate kind with `fstat`; close every non-returned FD. Translate `ELOOP`, `ENOENT`, `ENOTDIR`, and permission failures to bounded storage errors. [CITED: Python os docs and Linux open(2)]

### Narrow capabilities

Return separate `ListCapability`, `StatCapability`, `ReadCapability`, `ScanCapability`, `HashCapability`, `StreamCapability`, and `DownloadCapability`. Do not return a generic object with `.path`, `.open`, or all methods plus an operation flag. Capabilities are context managers and own their descriptors. [VERIFIED: D-01, D-14] [ASSUMED: exact class names]

### Independent source/destination grants

Copy, extract, patch, convert, cover, sidecar, ZIP, and temp workflows require an external input capability plus a separate owned destination capability. No grant is implied by the other. [VERIFIED: D-05 through D-08]

### Typed denial

Use one `StoragePolicyDenied` with stable code such as `external_storage_operation_denied` and bounded operation, class, and storage identity. A FastAPI handler returns 403; RQ/internal translators preserve the code and fail terminally. Exact JSON field names remain discretionary. [VERIFIED: D-09 through D-12] [ASSUMED: example code spelling]

### Anti-patterns

- Authorize then return `Path`; use an FD-owning capability. [VERIFIED: D-13, D-14]
- Subclass `FSHandler` for external roots; its constructor mutates. [VERIFIED: `base_handler.py`]
- Classify with string prefix or “outside external means writable.” [VERIFIED: D-04, D-06]
- Treat mount errors as policy. [VERIFIED: D-16]
- Catch denial and continue. [VERIFIED: D-11]
- Apply `O_NOFOLLOW` only to the leaf. [CITED: Linux open(2)]

## Existing Operation and Mutation Inventory

| Surface                                                         | Observed operations                                     | Required disposition                                                                                       |
| --------------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `FSHandler` constructor and `_atomic_write`                     | mkdir, mkstemp, chmod, replace, unlink                  | Owned-only; authorize before constructor/temp I/O. [VERIFIED: `base_handler.py`]                           |
| `FSHandler` public methods                                      | list/read/stream/stat plus mkdir/write/copy/move/delete | External reads use capabilities; mutations require owned grant at entry. [VERIFIED: `base_handler.py`]     |
| `FSPlatformsHandler`                                            | create structure/platform dirs; list                    | Gate creation; later mapping read cutover is Phase 5. [VERIFIED: `platforms_handler.py`]                   |
| `FSFirmwareHandler`                                             | list/hash                                               | Read capabilities; firmware upload cannot target external. [VERIFIED: `firmware_handler.py`; endpoint]     |
| `FSRomsHandler`                                                 | recursive list/stat/hash and rename                     | Read capabilities; external rename denial. [VERIFIED: `roms_handler.py`]                                   |
| ROM upload                                                      | temp chunks, final replace, cleanup                     | Owned staging; external final destination denied before target I/O. [VERIFIED: `endpoints/roms/upload.py`] |
| ROM patch                                                       | temp writes, subprocess transform, cleanup              | External input only, owned output only. [VERIFIED: `endpoints/roms/patch.py`]                              |
| ROM rename                                                      | filesystem rename then DB changes                       | Deny before lookup. [VERIFIED: `endpoints/roms/__init__.py`]                                               |
| Manual/screenshot/soundtrack, saves/states/identity/collections | upload/replace/unlink                                   | Explicit resources/assets owned classification. [VERIFIED: endpoint inventory]                             |
| `zip_cache.py`                                                  | source reads, cache mkdir/temp/rename/unlink            | External download/read plus owned cache write. [VERIFIED: code]                                            |
| `archives.py`                                                   | extraction and cleanup deletion                         | External source input only, owned destination. [VERIFIED: code]                                            |
| exporters                                                       | mkdir and link/copy                                     | Independent source/destination classifications. [VERIFIED: exporter code]                                  |
| audio tags                                                      | resource mkdir/write/unlink                             | Owned resources only. [VERIFIED: `audio_tags.py`]                                                          |
| sync handler/task/watcher                                       | sync mkdir/write/unlink                                 | Explicit owned sync root. [VERIFIED: sync code]                                                            |
| cleanup tasks                                                   | resource/tmp rmtree                                     | Explicit owned roots; types cannot accept `StorageRoot`. [VERIFIED: task code]                             |
| scanner/socket/watcher                                          | enumerate/hash/stat, legacy paths                       | Policy-govern reads now; mapping cutover Phase 5. [VERIFIED: code and roadmap]                             |
| streaming/download                                              | raw absolute library paths, FileResponse/nginx/ZIP      | Block bypass now; mapping cutover Phase 5 and nginx proof Phase 9. [VERIFIED: code and roadmap]            |
| historical migrations 0019/0040                                 | resource/asset mutations                                | Structurally owned, not runtime external consumers; regression-test imports. [VERIFIED: migrations]        |

Turn this table into a checked test parameter list. Any unclassified runtime seam blocks completion. [VERIFIED: D-15]

## Writable Location Separation

Use closed owned kinds for resources, assets, config, cache, upload temp, sync, database, and every generated output root. Composition creates trusted descriptors. Startup validation rejects equality or ancestry overlap with active external roots. Never infer ownership from absence under the external root. [VERIFIED: D-06, ROOT-05] [ASSUMED: enum names/startup hook]

Current paths are siblings under `ROMM_BASE_PATH`; uploads default under resources, while config, database, and sync are siblings. [VERIFIED: config code] The production example mounts `/romm/library` writable today, so add `:ro` and keep writable mounts separate. [VERIFIED: `examples/docker-compose.example.yml`] [CITED: Docker bind-mount docs]

## Don't Hand-Roll

| Problem               | Use                                     | Evidence                      |
| --------------------- | --------------------------------------- | ----------------------------- |
| Relative path parsing | Phase 1 normalizer                      | [VERIFIED: Phase 1]           |
| Safe access           | Descriptor-relative `os.open` walk      | [CITED: Linux open(2)]        |
| Hash formats          | Existing hashers fed by read capability | [VERIFIED: codebase]          |
| HTTP-only checks      | Domain policy plus channel translators  | [VERIFIED: D-09, D-13]        |
| Adjacent temp files   | Owned cache/tmp capability              | [VERIFIED: D-06, SAFE-06]     |
| Raw errors            | Typed bounded denial/resolver errors    | [VERIFIED: D-09 through D-12] |

## Common Pitfalls

1. **I/O before authorization:** even `exists`, `stat`, `resolve`, enumeration, or constructor `mkdir` violates D-16. Pure policy must run first. [VERIFIED]
2. **Generic read grant:** it silently broadens fine-grained rights. Separate public capability types and share only private FD helpers. [VERIFIED: D-01, D-14]
3. **FD leaks/lifetime:** streaming and subprocess adapters must keep the authorized FD open until the response or child process finishes, pass only a duplicated descriptor when ownership is transferred, and close it deterministically. Add descriptor-count and post-close tests. [VERIFIED: `backend/utils/rom_patcher/patcher.py`, `backend/utils/archives.py`, Python subprocess contract]
4. **Leaf-only no-follow:** intermediate symlinks remain traversable. Open every component. [CITED: Linux open(2)]
5. **Negative ownership inference:** arbitrary system paths become writable. Only trusted owned descriptors qualify. [VERIFIED: D-06]
6. **Swallowed job denial:** produces partial success. Preserve the code and fail terminally. [VERIFIED: D-11]
7. **Only testing `:ro`:** can pass via `EROFS`. Writable fixture and zero-call tripwires prove application denial. [VERIFIED: D-16]
8. **Reopening ordinary paths:** `FileResponse`, nginx aliases, and current archive/patch helpers reopen supplied names and therefore cannot consume an external capability unchanged. Backend subprocess adapters may use `/proc/self/fd/<n>` only with `pass_fds=(n,)`; nginx remains a separate opener and receives no external path in Phase 2. [VERIFIED: `backend/endpoints/roms/files.py`, `docker/nginx/templates/default.conf.template`, `backend/utils/archives.py`, `backend/utils/rom_patcher/patcher.py`]

## State of the Art

| Old                                                    | Required                                    | Impact                                                 |
| ------------------------------------------------------ | ------------------------------------------- | ------------------------------------------------------ |
| `FSHandler(base_path)` creates directories             | Trusted classification then authorization   | Denial before mutation. [VERIFIED]                     |
| `Path.resolve()` returns path                          | Descriptor-relative no-follow handle        | Opened object remains anchored. [CITED: Linux open(2)] |
| Source and generated content share library assumptions | External source plus explicit owned outputs | ROOT-05/SAFE-06. [VERIFIED]                            |
| Route-specific 403 strings                             | One typed policy denial                     | API/job parity. [VERIFIED]                             |
| Writable example library mount                         | `:ro` plus writable-fixture policy proof    | Defense in depth. [CITED: Docker docs]                 |

## Assumptions Log

| #   | Claim                                              | Risk                                         |
| --- | -------------------------------------------------- | -------------------------------------------- |
| A1  | Non-enum inputs are rejected rather than coerced.  | Low, naming only.                            |
| A2  | Exact capability classes and FD duplication shape. | Medium, consumer needs may narrow protocols. |
| A4  | Exact HTTP JSON fields/error code spelling.        | Medium, OpenAPI convention may differ.       |
| A5  | Owned enum names and startup overlap hook.         | Medium, invariant is locked.                 |

## Open Questions (RESOLVED)

1. **RESOLVED, nginx downloads:** The current production branch creates `X-Accel-Redirect: /library/<full_path>`, and nginx independently opens that name through its `/library/` alias. It cannot use or prove the backend's descriptor-bound authorization. Phase 2 must classify this as an unavailable adapter for trusted external roots: no external capability may be converted to `FileRedirectResponse`, `FileResponse`, an absolute path, or an X-Accel URI. The Phase 2 inventory test must fail if an external-root branch reaches either response constructor. Allowed external `STREAM` and `DOWNLOAD` operations remain represented by FD-owning capabilities, but wiring those capabilities into mapped download routes is Phase 5; nginx performance/proof remains Phase 9. Existing legacy-library routing is not converted in this phase. [VERIFIED: `backend/endpoints/roms/files.py:120-143`, `backend/utils/nginx.py:56-85`, `docker/nginx/templates/default.conf.template:103-107`, `.planning/ROADMAP.md`]
2. **RESOLVED, external-tool adapters:** The live Python archive readers already accept file objects for ZIP paths, while 7zz and bsdtar and the Node patcher currently receive ordinary path strings and reopen them. The implementation-ready adapter is: retain or duplicate the authorized read FD, invoke Linux child processes with `/proc/self/fd/<fd>` and `pass_fds=(fd,)`, keep the capability alive through `communicate()` or process iteration, and close the duplicate in `finally`. Archive commands remain list/read-to-stdout only. The patcher receives two inherited read descriptors for ROM and library patch input plus one separately authorized RomM-owned output path; uploaded patches and output remain in owned temp storage. No subprocess receives an external destination path. Adapter tests must assert the exact `pass_fds` tuple, proc-FD arguments, capability lifetime, child failure propagation, no fallback to an ordinary source path, and unchanged source manifests. [VERIFIED: `backend/utils/archives.py:131-211,331-401,445-541,578-610`, `backend/utils/rom_patcher/patcher.py:27-75`, `backend/utils/rom_patcher/patcher.js:39-90`, `backend/endpoints/roms/patch.py:118-194`; CITED: https://docs.python.org/3/library/subprocess.html]
3. **RESOLVED, writable fixture versus health:** D-16 is a policy-denial test, not a successful production-resolution test. Build the same source tree once, expose it at two logical fixture roots, one ordinary writable directory and one container bind mount with `:ro`, then construct unsaved `StorageRoot` identities directly with fixed IDs, `mode=external_read_only`, and `active=True`. Call the pure policy authorization entry point directly for the complete denied/unknown matrix while I/O tripwires cover `stat`, `lstat`, `open`, enumeration, and mutation; therefore neither fixture invokes `check_storage_root_health` or `resolve_storage_root`. Separately, allowed-access integration tests use only the `:ro` identity and the normal resolver/access health gate. The container verifier must mount the same host fixture twice, `/fixtures/writable` and `/fixtures/read-only:ro`, and assert identical typed denials and identical before/after manifests. This preserves Phase 1's production rejection of writable roots without weakening D-16's proof that application policy, rather than `EROFS`, denied the operation. [VERIFIED: `backend/tests/handler/filesystem/test_storage_resolver.py:81-150`, `backend/handler/filesystem/storage_resolver.py:51-110`, `backend/models/storage.py:27-56`, `backend/docker-compose.test.yml`, D-16]

## Environment Availability

| Dependency              |    Available | Version / fallback                                                             |
| ----------------------- | -----------: | ------------------------------------------------------------------------------ |
| Linux descriptor APIs   |          Yes | Kernel 5.15.0-186; standard `os.open` walk. [VERIFIED: probe]                  |
| Docker Engine / Compose |          Yes | 29.6.2 / 5.3.1. [VERIFIED: probe]                                              |
| Project Python          |    Container | Project requires >=3.13; host 3.10 is unsuitable. [VERIFIED: probe, pyproject] |
| pytest                  |          Yes | 9.0.3 locked. [VERIFIED: uv.lock]                                              |
| Real NAS                | Not required | Deferred to Phase 9. [VERIFIED: roadmap]                                       |

No blocking dependency is missing. Use the existing development container without restarting services. [VERIFIED: environment audit]

## Validation Architecture

### Framework and commands

| Property   | Value                                                                                                                            |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Framework  | pytest 9.0.3, pytest-asyncio 1.3.0 [VERIFIED: lockfile]                                                                          |
| Quick      | `cd backend && uv run pytest tests/handler/filesystem/test_storage_policy.py tests/handler/filesystem/test_storage_access.py -x` |
| Full phase | Add endpoint, task, and inventory suites to the quick command.                                                                   |
| Container  | `python3 backend/tools/verify_read_only_policy.py`, running identical writable and `:ro` cases.                                  |

### Requirements to test map

| Req     | Behavior                                                                            | Test/file                                                 |
| ------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------- |
| ROOT-05 | owned roots explicit and disjoint                                                   | unit/config, `test_storage_policy.py` (Wave 0)            |
| SAFE-01 | exact allowlist                                                                     | parameterized unit, same file (Wave 0)                    |
| SAFE-02 | mutation denial before all I/O                                                      | tripwire matrix, same file (Wave 0)                       |
| SAFE-03 | bounded 403 code                                                                    | API, `test_storage_policy_denials.py` (Wave 0)            |
| SAFE-04 | inventory governed or owned-only                                                    | contract, `test_storage_inventory.py` (Wave 0)            |
| SAFE-05 | writable and `:ro` parity                                                           | Docker, verifier tool (Wave 0)                            |
| SAFE-06 | read leaves source manifest identical                                               | filesystem integration, `test_storage_access.py` (Wave 0) |
| TEST-03 | delete/rename/move/overwrite/upload/mkdir/extract/patch/sidecar/cover/symlink cases | adversarial matrix (Wave 0)                               |

Required dimensions: exact allow/deny/unknown matrix; pre-access spies for open/stat/scandir/Path/temp/mkdir/unlink/rename/replace/copy/move/extract/patch; capability surface and post-close checks; coordinated symlink/name-swap races; typed denial rather than `EROFS`; before/after manifest excluding atime; API/job/internal parity and no partial-success event. [VERIFIED: D-15, D-16; Phase 1 testing pattern]

Per commit run focused tests; per wave run all Phase 2 tests; phase gate requires full suite, both mount modes, scoped Trunk, and reviewed inventory. [VERIFIED: repository rules]

## Security Domain

| ASVS area           | Applies | Control                                                                                                                                     |
| ------------------- | ------: | ------------------------------------------------------------------------------------------------------------------------------------------- |
| V4 Access Control   |     Yes | default-deny operation policy and typed 403. [VERIFIED]                                                                                     |
| V5 Validation       |     Yes | Phase 1 normalization plus trusted identity. [VERIFIED]                                                                                     |
| V8 Data Protection  |     Yes | no leakage/mutation and owned outputs. [VERIFIED]                                                                                           |
| V12 Files/Resources |     Yes | descriptor-relative no-follow and explicit destinations. [CITED: https://owasp.org/www-project-application-security-verification-standard/] |

Threats include traversal, symlink swap/TOCTOU, caller-forged class, operation confusion, path disclosure, partial workflow, FD exhaustion, and writable nested mounts. Mitigations are Phase 1 normalization, per-component no-follow descriptors, trusted descriptors, closed enum, bounded denial, terminal failure, context-managed FDs, and avoiding nested mounts. Docker says recursive read-only submounts require Linux 5.12 or later. [VERIFIED: decisions/code] [CITED: Docker docs]

## Sources

### Primary (HIGH)

- Phase 2 context, project requirements/roadmap/state, Phase 1 context/research/summaries/verification.
- Live backend filesystem, endpoint, task, utility, config, tests, and Docker example code.
- https://docs.python.org/3/library/os.html
- https://man7.org/linux/man-pages/man2/openat.2.html
- https://man7.org/linux/man-pages/man2/openat2.2.html
- https://docs.docker.com/engine/storage/bind-mounts/
- https://owasp.org/www-project-application-security-verification-standard/

### Secondary (MEDIUM)

- `.planning/codebase/ARCHITECTURE.md`, `CONCERNS.md`, and `TESTING.md`, cross-checked against live code.

### Tertiary (LOW)

- None; unverified points are isolated in the Assumptions Log.

## Metadata

- Standard stack: HIGH, lockfile/environment plus official docs.
- Architecture: HIGH for policy/descriptor boundary, MEDIUM for deferred consumer adapters.
- Inventory: HIGH for current Python code, but re-scan before implementation per D-15.
- Research date: 2026-08-09.
- Valid until: 2026-09-08 for stable design; inventory expires on code changes.
