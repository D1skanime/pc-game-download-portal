# Phase 9: Operational Immutability Proof - Research

**Researched:** 2026-08-27
**Domain:** Production-like Docker immutability evidence, browser E2E, operator safety
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Build the proof around a production-like Docker stack containing the RomM application, background worker, nginx, required database and queue services, a read-only fixture library mount, and distinct writable RomM-owned storage.
- **D-02:** Mount the fixture library read-only with Docker `:ro`. Database data, resources, assets, cache, configuration, temporary data, scan state, and all other RomM-owned output must use separate writable mounts or volumes.
- **D-03:** Exercise the actual nginx internal-redirect download/stream path and the actual worker queue path, not development-only substitutes.
- **D-04:** Include restart persistence in the stack proof. Restart only the isolated test stack created for Phase 9, never Team4s or unrelated host services.
- **D-05:** Capture a full source manifest immediately before and after every supported workflow. Each manifest records every relative path, exact name, entry type and directory structure, file size, content hash, and filesystem timestamps.
- **D-06:** Compare complete manifests with an exact, machine-verifiable diff. A workflow passes only when content, names, structure, sizes, hashes, and non-access timestamps are unchanged. Access-time invariance must be demonstrated under the documented `noatime` or NAS-equivalent configuration.
- **D-07:** Produce separate before/after evidence for mapping creation, mapping change, mapping removal, folder browsing and mapping tests, preview, scanning and hashing, metadata matching, streaming and browser play, single-file and multi-file downloading, restart persistence, legacy migration and rollback where supported, game catalog removal, and platform mapping removal.
- **D-08:** Evidence must cover multiple mappings and Unicode, nested, empty, and multi-file fixture shapes. It must make any source mutation or incomplete manifest a hard failure, including unexpected files, directories, sidecars, locks, caches, archives, or temporary output.
- **D-09:** Keep evidence deterministic and reviewable in CI. The planner may choose the exact manifest serialization and artifact layout, but it may not weaken the required fields, per-workflow boundaries, or exact comparison.
- **D-10:** Use browser end-to-end tests for the supported operator and user workflows, not API-only substitutes. Cover mapping and browsing, scan initiation and completion, streaming or browser play, downloading, legacy migration, game catalog removal, and platform mapping removal.
- **D-11:** Browser tests must drive the production-like nginx-backed application while worker jobs run through the separate worker service. They must verify visible success, safe failure states where relevant, and the corresponding unchanged source manifest.
- **D-12:** Include the Phase 8 deferred v2 browser smoke scope so authentication, pairing where applicable, v2 boot, navigation, and supported routes are exercised without any v1 fallback.
- **D-13:** Write one complete operator guide covering the one-root Docker `:ro` mount, separate writable storage, root registration, folder browsing, platform mapping and changes, scan and preview behavior, streaming and downloading, migration, catalog-only removal, restart behavior, troubleshooting, security boundaries, and known limitations.
- **D-14:** The guide must explain defense in depth: Docker `:ro` is mandatory, and the application policy must still deny mutations before filesystem access. It must also explain traversal and symlink behavior without exposing or encouraging unsafe bypasses.
- **D-15:** Include explicit `noatime` guidance and NAS-specific equivalents, explain why ordinary reads can otherwise update access time, and distinguish access-time controls from the independent content immutability guarantees.
- **D-16:** Include a maintenance-window checklist that requires authorization and workload review before any real NAS mount change. The checklist must require backups or recovery readiness, mount verification, read-only validation, writable-storage separation, manifest/evidence review, rollback steps, and post-window confirmation.
- **D-17:** State explicit Team4s safeguards: do not edit Team4s source or configuration, do not restart or stop Team4s services or the host, do not touch active encode workloads, and do not use Team4s paths, mounts, containers, or data as Phase 9 test fixtures.
- **D-18:** Phase 9 planning and execution use synthetic or repository-controlled fixtures only. Access to a real NAS mount remains prohibited unless a later, separately authorized maintenance window explicitly permits it.

### Folded Todos

- **Enforce immutable external game libraries:** Fold `.planning/todos/pending/2026-08-04-enforce-external-library-read-only.md` into Phase 9. Its remaining operational proof and documentation obligations are satisfied through the production-like `:ro` stack, complete before/after manifests, catalog-only removal coverage, negative mutation guarantees, and `noatime` operator guidance.

### the agent's Discretion

The exact fixture dataset, manifest file format, Docker project naming, CI artifact packaging, Playwright spec grouping, and operator-guide filename are open to the researcher and planner, provided every locked workflow, evidence field, service path, and safeguard above remains explicit and testable.

### Deferred Ideas (OUT OF SCOPE)

None recorded.
</user_constraints>

<phase_requirements>

## Phase Requirements

| ID                    | Description                                                                                      | Research Support                                                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| TEST-04               | Prove `:ro` mounting, reads, multiple mappings, changes, restart, and legacy migration.          | Isolated Compose topology, exhaustive workflow matrix, browser/worker orchestration. [VERIFIED: `.planning/REQUIREMENTS.md`, `09-CONTEXT.md`] |
| TEST-05               | Prove content, names, structure, sizes, hashes, and non-access timestamps unchanged.             | Versioned complete manifest, strict schema, per-workflow pairs, mutation self-tests. [VERIFIED: requirements and existing manifest helpers]   |
| TEST-06               | Prove production nginx and worker enforce database identity and root boundaries.                 | nginx-backed Playwright, internal redirect checks, queue/job witness. [VERIFIED: nginx template and repository tests]                         |
| DOC-01                | Explain one-root `:ro`, writable separation, mappings, browsing, migration, and catalog removal. | Guide outline plus executable documentation contract. [VERIFIED: requirements]                                                                |
| DOC-02                | Explain defense in depth, path safety, troubleshooting, limitations, and atime controls.         | Security guidance tied to the executable proof. [VERIFIED: requirements]                                                                      |
| DOC-03                | Require a safe maintenance window and prohibit Team4s disruption.                                | Mandatory checklist and explicit prohibitions. [VERIFIED: requirements and D-16 to D-18]                                                      |
| </phase_requirements> |

## Summary

Build one self-contained acceptance harness around a dedicated Compose file. It creates a nonce-scoped project, synthesizes the complete fixture, starts nginx, RomM, a separate worker, database, and queue, and mounts the source read-only into every reader. Every writable application path is a distinct named volume or task-owned bind directory. Before startup and after restart, inspect both the resolved Compose model and live container mounts. Reject a missing `ro` flag, writable alias, unexpected bind, fixed container collision, host network, or non-owned service. [VERIFIED: `backend/docker-compose.policy-test.yml`, `examples/docker-compose.example.yml`, D-01 to D-04]

Use one canonical manifest implementation. Existing helpers already demonstrate sorted relative paths and SHA-256, but Phase 9 must include the root and empty directories, exact encoded names, lstat type, mode, size, hashes, symlink targets, and nanosecond timestamps. Compare mtime, ctime, and birth time when available. Record atime separately and require equality only in an explicitly attested noatime run. Reject missing, extra, duplicate, malformed, reordered, or partially captured entries before value comparison. [VERIFIED: `backend/tests/integration/test_scan_source_immutability.py`, `backend/tools/verify_read_only_policy.py`, `backend/tools/verify_phase6_acceptance.py`, D-05 to D-09]

Playwright must drive nginx and the v2 UI while real jobs pass through the worker service. API setup/polling can support the fixture but cannot replace visible actions. Each test brackets one action with harness checkpoints and emits paired manifests, exact diff, UI result, service-path witness, and cleanup status into deterministic artifacts. [VERIFIED: `frontend/playwright.config.ts`, `frontend/e2e/fixtures/auth.ts`, D-10 to D-12]

**Primary recommendation:** Implement a fail-closed Python harness with a shared canonical manifest library and a thin Playwright checkpoint bridge, then give every required workflow an independently reviewable evidence bundle. [VERIFIED: repository verifier patterns]

## Architectural Responsibility Map

| Capability                        | Primary Tier       | Secondary Tier | Rationale                                                                                                          |
| --------------------------------- | ------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------ |
| Compose lifecycle and mount proof | Test orchestration | Docker         | Only the nonce-owned harness creates, inspects, restarts, and removes the stack. [VERIFIED: verifier patterns]     |
| Manifest and exact diff           | Test orchestration | Filesystem     | One contract prevents divergent completeness rules. [VERIFIED: existing duplicate helpers]                         |
| Mapping/migration/removal         | API/backend        | Database       | Existing typed endpoints and lifecycle handlers own these operations. [VERIFIED: Phase 6 context]                  |
| Scan/hash/metadata                | Worker/backend     | Database       | Durable work uses the queue and persists owned state. [VERIFIED: Phase 5 context]                                  |
| Stream/download                   | nginx plus API     | Browser        | API authorizes an internal redirect, nginx transfers bytes. [VERIFIED: nginx template, `backend/utils/nginx.py`]   |
| Operator actions                  | Browser            | Harness        | Playwright proves visible behavior, harness proves infrastructure and archive invariants. [VERIFIED: E2E patterns] |
| Operator guide                    | Documentation      | Compose/policy | Guidance must match the executable deployment and safety contracts. [VERIFIED: DOC-01 to DOC-03]                   |

## Standard Stack

| Component                 | Version              | Purpose                                               | Basis                                                                               |
| ------------------------- | -------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Python standard library   | Project Python 3.13+ | JSON, lstat, hashing, subprocess orchestration        | Existing tools use Python, no new dependency needed. [VERIFIED: `CLAUDE.md`]        |
| pytest                    | 9.x                  | Harness unit/integration tests                        | Existing backend runner. [VERIFIED: `.planning/codebase/TESTING.md`, local probe]   |
| Docker / Compose          | 29.6.2 / 5.3.1       | Isolated production-like stack and mount inspection   | Installed on canonical host. [VERIFIED: local probe]                                |
| Playwright                | 1.61.1               | Authenticated v2 browser workflows                    | Current repository E2E dependency. [VERIFIED: `frontend/package.json`, local probe] |
| Repository nginx template | current checkout     | Static UI, API proxy, internal library/cache delivery | Production path required by TEST-06. [VERIFIED: nginx template]                     |

Supporting tools are `docker compose config --format json`, `docker inspect`, Playwright trace/screenshots, and `hashlib.sha256`. No external package installation is required. Do not add another E2E runner, manifest library, or Compose wrapper. [VERIFIED: environment and repository inspection]

## Architecture Patterns

### System Architecture Diagram

```text
fixture builder -> canonical source -> :ro mounts -> app / worker / nginx
                      |                    |         |       |
                 before manifest          DB    Redis/RQ    X-Accel
                      |                    |         |       |
                      +------ browser through nginx --------+
                      |                 workflow action
                 after manifest
                      |
            schema check -> exact diff -> per-workflow evidence -> pass/fail
```

### Recommended Project Structure

```text
backend/docker-compose.immutability-test.yml
backend/tools/verify_operational_immutability.py
backend/tests/tools/test_verify_operational_immutability.py
backend/tests/integration/test_operational_immutability.py
frontend/e2e/operational-immutability.spec.ts
frontend/e2e/fixtures/operational-proof.ts
tests/fixtures/operational-immutability/
docs/external-read-only-library-operations.md
artifacts/operational-immutability/              # generated, not committed
```

Harness code belongs in `backend/tools/`, browser specs in `frontend/e2e/`, and the guide in `docs/`. [VERIFIED: `CLAUDE.md`, repository conventions]

### Pattern 1: Canonical manifest evidence contract

Serialize canonical JSON with schema version, run/workflow identity, root record, sorted entries, completeness counters, and aggregate digest. Sort by raw name representation, not locale collation. Use `lstat`, never follow a symlink. For regular files, record metadata, hash bytes, lstat again, and fail if metadata changed during capture. Each entry contains relative path, unambiguous encoded name, type, mode, size, file SHA-256, symlink target, mtime_ns, ctime_ns, optional birthtime_ns, and separately reported atime_ns. [VERIFIED: existing helpers and D-05 to D-09]

### Pattern 2: One workflow, one proof envelope

Every locked workflow writes `before.json`, `after.json`, `diff.json`, and `result.json` under a stable slug. `result.json` binds requirement IDs, browser title, Compose project, fixture digest, expected service path, worker job/service where applicable, HTTP evidence, manifest digests, and final status. Never collapse several workflows behind one pair. [VERIFIED: D-07, D-09]

### Pattern 3: Nonce ownership and fail-closed cleanup

Create bounded project/temp names, label all resources, and record exact IDs. Cleanup removes only IDs whose labels match recorded ownership. Fail if the name already exists. Restart only this project and re-attest mounts afterward. [VERIFIED: Phase 6 acceptance patterns, D-04]

### Pattern 4: Browser action plus infrastructure witness

Playwright asserts visible v2 states with semantic, auto-waiting locators. The harness independently proves worker execution and nginx transfer. For downloads/play, prove an authorized public request succeeds, the application selected the expected internal redirect path, nginx served it, and direct `/library/...` or `/cache/...` access returns 404. [VERIFIED: E2E fixtures, nginx `internal`, backend redirect tests]

### Anti-Patterns to Avoid

- One manifest around the suite violates per-workflow evidence. [VERIFIED: D-07]
- API-only tests miss v2/browser and Phase 8 smoke. [VERIFIED: D-10 to D-12]
- Vite, direct FastAPI, or inline workers do not satisfy TEST-06. [VERIFIED: requirement]
- Files-and-hashes-only manifests miss empty directories, names, links, modes, and timestamps. [VERIFIED: D-05, D-08]
- `:ro` errors do not replace application denial-before-I/O proof. [VERIFIED: Phase 2 and folded todo]
- Fixed container names or broad cleanup risk unrelated services and Team4s. [VERIFIED: D-04, D-17]
- Atime equality without mount attestation is not portable evidence. [VERIFIED: D-06, D-15]

## Don't Hand-Roll

| Problem          | Use Instead                          | Why                                                                                  |
| ---------------- | ------------------------------------ | ------------------------------------------------------------------------------------ |
| Browser waits    | Playwright locators/response waits   | Current fixtures already handle hydration and avoid sleeps. [VERIFIED: auth fixture] |
| File delivery    | Repository nginx path                | TEST-06 requires it. [VERIFIED: requirement]                                         |
| Worker execution | Real Redis/RQ worker container       | D-03/D-11 require queue execution. [VERIFIED: context]                               |
| Hashing          | `hashlib.sha256`                     | Existing evidence standard. [VERIFIED: helpers]                                      |
| Authorization    | Existing DB identity/resolver/policy | The proof exercises rather than duplicates the boundary. [VERIFIED: Phase 2/5]       |

## Common Pitfalls

1. **Capture races or changes atime.** Use quiescent synthetic fixtures, noatime attestation for the atime-specific run, and pre/post lstat around hashing. Never normalize evidence after capture. [VERIFIED: D-06, D-15]
2. **A second writable alias escapes YAML review.** Inspect resolved Compose JSON and every live container mount, rejecting overlaps and `RW=true`. [VERIFIED: D-02]
3. **Browser success bypasses production.** Set `E2E_BASE_URL` to nginx so Playwright does not launch its own server, and retain nginx plus worker witnesses. [VERIFIED: Playwright config]
4. **Artifacts land in source.** Mount every owned path separately and seed mutation self-tests for files, directories, sidecars, locks, caches, and temp output. [VERIFIED: D-02, D-08]
5. **Restart proves only availability.** Re-attest mounts/labels, query persisted mapping IDs, then run a mapped read with its own manifest pair. [VERIFIED: TEST-04]
6. **Teardown removes failure evidence.** Store artifacts outside volumes, preserve them in `finally`, and separately attest exact cleanup. [VERIFIED: D-09]

## Assumptions Log

| #   | Claim                                                                                        | Risk if Wrong                                                                           |
| --- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| A1  | CI exposes filesystem birth time. [ASSUMED]                                                  | Keep it optional with explicit availability, never substitute another timestamp.        |
| A2  | nginx logs provide sufficient path correlation without image changes. [ASSUMED]              | Wave 0 must probe container logs or mount a task-owned access log.                      |
| A3  | Pairing applies only if the isolated stack exposes a pairing-capable route/device. [ASSUMED] | Inventory actual Phase 8 contract and record a bounded not-applicable result if needed. |

## Open Questions

1. **Final Phase 6/7 surface:** Phase 6 still has unfinished roadmap plans. Gate Phase 9 execution on dependencies and inventory the implemented browser migration/rollback actions before finalizing the matrix. [VERIFIED: `ROADMAP.md`]
2. **nginx witness:** Wave 0 must choose structured task-owned access logs or container-log correlation. API header evidence alone is insufficient. [VERIFIED: TEST-06]
3. **CI noatime:** Separate the mandatory content/non-access timestamp gate from an attested atime gate. If noatime is unavailable, do not claim atime proof. [VERIFIED: D-06, D-15]

## Environment Availability

| Dependency      | Available                | Version                   | Fallback                                 |
| --------------- | ------------------------ | ------------------------- | ---------------------------------------- |
| Docker Engine   | yes                      | 29.6.2                    | none [VERIFIED: local probe]             |
| Docker Compose  | yes                      | 5.3.1                     | none [VERIFIED: local probe]             |
| Python / pytest | yes                      | Python 3.13+ / pytest 9.x | none [VERIFIED: project and local probe] |
| Node / npm      | yes                      | 24.19.0 / 11.17.0         | none [VERIFIED: local probe]             |
| Playwright      | yes                      | 1.61.1                    | none [VERIFIED: local probe]             |
| NAS / Team4s    | intentionally not probed | not applicable            | synthetic fixture [VERIFIED: D-17, D-18] |

## Validation Architecture

### Test Framework

| Property        | Value                                                                                                                                     |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Backend         | pytest 9.x [VERIFIED: repository environment]                                                                                             |
| Browser         | Playwright 1.61.1, authenticated Chromium setup [VERIFIED: config]                                                                        |
| Config          | `backend/pyproject.toml`, `backend/tests/conftest.py`, `frontend/playwright.config.ts`                                                    |
| Quick command   | `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -x -q`                                                   |
| Browser command | `cd frontend && E2E_BASE_URL="$PHASE09_BASE_URL" npx playwright test e2e/operational-immutability.spec.ts --project=chromium --workers=1` |
| Full command    | `python3 backend/tools/verify_operational_immutability.py --all --artifacts "$PHASE09_ARTIFACTS"`                                         |

Harness variables must resolve to bounded task-owned values, never broad paths or home aliases. [VERIFIED: repository safety rules]

### Phase Requirements to Test Map

| Req     | Behavior                                                                | Type                             | Automated Command                                                                                                                                                 | Exists?    |
| ------- | ----------------------------------------------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| TEST-04 | topology plus all mapping/read/lifecycle/restart workflows              | production integration + browser | `python3 backend/tools/verify_operational_immutability.py --requirement TEST-04`                                                                                  | No, Wave 0 |
| TEST-05 | complete manifest schema, mutation mutants, exact per-workflow equality | unit + integration               | `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -x -q && python3 tools/verify_operational_immutability.py --requirement TEST-05` | No, Wave 0 |
| TEST-06 | nginx internal delivery and real worker queue with bound identity       | production integration + browser | `python3 backend/tools/verify_operational_immutability.py --requirement TEST-06`                                                                                  | No, Wave 0 |
| DOC-01  | complete workflow and storage guide                                     | docs contract                    | `python3 backend/tools/verify_operational_immutability.py --check-docs DOC-01`                                                                                    | No, Wave 0 |
| DOC-02  | security, path safety, troubleshooting, noatime                         | docs contract + review           | `python3 backend/tools/verify_operational_immutability.py --check-docs DOC-02`                                                                                    | No, Wave 0 |
| DOC-03  | authorized window and Team4s prohibitions                               | docs contract + review           | `python3 backend/tools/verify_operational_immutability.py --check-docs DOC-03`                                                                                    | No, Wave 0 |

### Feedback Loops

1. **Per task, under 30 seconds:** Manifest/harness unit tests cover canonical order, root/empty directories, Unicode and encoded names, types, modes, sizes, hashes, timestamps, duplicates/missing entries, race detection, and seeded mutation of every field. Run the quick command after each harness edit. [VERIFIED: pytest patterns]
2. **Static topology, under 30 seconds:** `python3 backend/tools/verify_operational_immutability.py --preflight-only` resolves Compose without starting containers and rejects service/mount/ownership hazards. [VERIFIED: D-01 to D-04]
3. **Workflow smoke:** `python3 backend/tools/verify_operational_immutability.py --workflow <slug> --keep-stack` runs one workflow and its manifest pair in a task-owned session. Final gates never keep the stack. [VERIFIED: D-07]
4. **Browser task loop:** run one grep-selected workflow through nginx with `--workers=1`, never against Vite or direct FastAPI. [VERIFIED: TEST-06]
5. **Per wave:** changed unit tests, all workflows introduced in the wave, regression workflows sharing that tier, Compose preflight, and `git diff --check`. Documentation waves also run docs contracts and path/link validation. [VERIFIED: pre-PR patterns]
6. **Phase gate:** one clean full harness lifecycle, affected backend tests, frontend typecheck/test/build if touched, scoped Trunk, exact cleanup, and artifact schema validation. [VERIFIED: pre-PR skill and acceptance patterns]

### Sampling and Coverage

The final gate is exhaustive. Every D-07 workflow gets an independent pair: mapping create/change/remove, browse/test, preview, scan/hash, metadata match, stream/play, single/multi-download, restart, migration/rollback where supported, catalog removal, and platform mapping removal. Fixtures include at least two mappings, nested and Unicode paths, an empty directory, zero-byte and ordinary files, a multi-file game, and symlink/traversal rejection. The aggregate matrix must show each workflow and each fixture dimension covered at least once. [VERIFIED: D-07, D-08]

Task loops sample the changed workflow plus all manifest mutation tests. Wave gates run introduced workflows and tier peers. The phase gate runs all workflows serially or with fully separate fixtures/databases. Never parallelize against shared state. [VERIFIED: deterministic evidence D-09]

### Required Artifacts

```text
artifacts/operational-immutability/<run-id>/
├── run.json
├── topology/{compose.resolved.json,mounts.before.json,mounts.after-restart.json}
├── workflows/<slug>/{before.json,after.json,diff.json,result.json,browser/}
├── services/{app.log,worker.log,nginx.log}
├── aggregate.json
└── cleanup.json
```

Automated validation requires every file to parse and bind the same run/project/fixture identity. Artifacts must contain no secrets, cookies, or unsafe host paths. Missing artifacts, incomplete manifests, source deltas, absent nginx/worker witnesses, or cleanup residue are hard failures. [VERIFIED: D-08, D-09, secret policy]

### Manual-Only Checks

- Review the guide for clear sequencing, authorization, backup/recovery readiness, workload review, rollback, and post-window confirmation. Automation can require sections but cannot prove operational clarity. [VERIFIED: DOC-01 to DOC-03]
- Verify vendor-specific noatime equivalents during a later authorized deployment review. Phase 9 does not probe a NAS. [VERIFIED: D-15, D-18]
- Confirm Team4s and encode workloads are outside any later maintenance target. This is outside the synthetic proof. [VERIFIED: D-16 to D-18]
- Human visual/audio emulator sanity may supplement automated v2 boot, route/network, authorization, no-v1-fallback, and immutability assertions. [ASSUMED]

### Wave 0 Gaps

- [ ] `backend/tools/verify_operational_immutability.py`: orchestrator, manifest, artifacts, topology, cleanup.
- [ ] `backend/tests/tools/test_verify_operational_immutability.py`: schema, mutation, Compose, artifact, cleanup tests.
- [ ] `backend/docker-compose.immutability-test.yml`: complete isolated stack and mounts.
- [ ] `frontend/e2e/operational-immutability.spec.ts`: v2 browser workflow matrix.
- [ ] `frontend/e2e/fixtures/operational-proof.ts`: checkpoint/finalize bridge and witnesses.
- [ ] Complete deterministic fixture seed.
- [ ] CI artifact upload with redaction and always-run cleanup.
- [ ] Executable DOC-01 to DOC-03 contract.

No framework installation is required. [VERIFIED: environment audit]

## Security Domain

### Project Constraints (from AGENTS.md and CLAUDE.md)

- Work only in canonical `/home/d1sk/romm`, verify path/branch/status/planning state before writes, and preserve unrelated changes. [VERIFIED: repository instructions]
- Do not deploy, access a NAS, restart/alter Team4s, touch encode workloads, or use Team4s paths/data. [VERIFIED: repository instructions and context]
- Keep code and Markdown in English, avoid em dashes, put backend tools under `backend/tools/`, test changed logic, use Trunk, never bypass hooks, never commit secrets, and disclose AI assistance in a PR. [VERIFIED: `CLAUDE.md`]

### Applicable ASVS Categories

| Category            | Applies | Control                                                                                |
| ------------------- | ------- | -------------------------------------------------------------------------------------- |
| V2 Authentication   | yes     | Existing real login/session fixtures and protected routes. [VERIFIED: auth fixture]    |
| V3 Session          | yes     | Generated gitignored state, no cookies in evidence. [VERIFIED: auth fixture]           |
| V4 Access Control   | yes     | Roles/scopes plus database-bound storage identity. [VERIFIED: backend skill]           |
| V5 Input Validation | yes     | Typed APIs, canonical path policy, bounded harness variables. [VERIFIED: Phase 1 to 3] |
| V6 Cryptography     | yes     | Standard SHA-256 for evidence integrity, no custom crypto. [VERIFIED: helpers]         |

| Threat                     | STRIDE                 | Mitigation                                                                                     |
| -------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------- |
| Traversal/symlink escape   | Tampering / disclosure | Existing resolver and denial before I/O, negative tests, manifest. [VERIFIED: Phase contracts] |
| Writable alias             | Tampering              | Resolved and live mount attestation for every service. [VERIFIED: D-02]                        |
| Stale/forged job identity  | Spoofing / tampering   | Persisted IDs and worker witness, stale mapping failures. [VERIFIED: Phase 5]                  |
| Direct nginx internal path | Disclosure             | `internal`, direct 404, authorized public request. [VERIFIED: nginx template]                  |
| Evidence leakage           | Disclosure             | Allowlisted/redacted schema, no cookies/env dumps. [VERIFIED: secret policy]                   |
| Broad cleanup              | Denial of service      | Nonce labels, recorded IDs, ownership check. [VERIFIED: D-04, D-17]                            |

## Sources

### Primary (HIGH confidence)

- `09-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/PROJECT.md` and carried Phase 5 to 8 contexts. [VERIFIED: repository inspection]
- `backend/docker-compose.policy-test.yml`, `backend/tools/verify_read_only_policy.py`, `backend/tools/verify_phase6_acceptance.py`. [VERIFIED: repository inspection]
- `backend/tests/integration/test_scan_source_immutability.py`, legacy migration and redirect tests. [VERIFIED: repository inspection]
- `frontend/playwright.config.ts`, `frontend/e2e/fixtures/auth.ts`. [VERIFIED: repository inspection]
- `docker/nginx/templates/default.conf.template`, `backend/utils/nginx.py`, `examples/docker-compose.example.yml`. [VERIFIED: repository inspection]
- `CLAUDE.md`, backend-development and pre-pr-verification skills. [VERIFIED: repository inspection]

### Secondary / Tertiary

None. No external ecosystem choice is needed; unresolved claims are isolated in the Assumptions Log.

## Metadata

**Confidence breakdown:** Standard stack HIGH, architecture HIGH, validation HIGH, pitfalls HIGH. All recommendations derive from locked decisions, live repository patterns, and locally verified tool availability.

**Research date:** 2026-08-27
**Valid until:** 2026-09-26, or earlier if Phase 6/7 contracts or production Compose topology change.
