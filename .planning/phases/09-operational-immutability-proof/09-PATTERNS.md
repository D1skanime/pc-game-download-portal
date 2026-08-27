# Phase 9: Operational Immutability Proof - Pattern Map

**Mapped:** 2026-08-27
**Purpose:** Concrete analogs and code excerpts for the files Phase 9 is expected to create or modify.

## Planned File Inventory

| Target file                                                   | Role                                                                                 | Data flow                                                                                     | Closest analogs                                                                           |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `backend/docker-compose.immutability-test.yml`                | Isolated production-like proof stack                                                 | host fixture + owned mounts -> app/worker/nginx/db/redis -> harness                           | `backend/docker-compose.policy-test.yml`, `examples/docker-compose.example.yml`           |
| `backend/tools/verify_operational_immutability.py`            | Canonical harness and evidence orchestrator                                          | CLI -> fixture build -> compose preflight/up/restart/down -> manifests/artifacts -> pass/fail | `backend/tools/verify_read_only_policy.py`, `backend/handler/storage/legacy_migration.py` |
| `backend/tests/tools/test_verify_operational_immutability.py` | Fast feedback for manifest schema, topology, artifacts, cleanup                      | pytest -> harness helpers -> exact assertions                                                 | `backend/tests/integration/test_scan_source_immutability.py`                              |
| `backend/tests/integration/test_operational_immutability.py`  | Backend integration for workflow envelopes and witnesses                             | pytest -> harness subprocess / app paths -> artifacts                                         | `backend/tests/endpoints/test_streaming.py`, `backend/tests/endpoints/roms/test_files.py` |
| `frontend/e2e/fixtures/operational-proof.ts`                  | Shared Playwright proof helpers                                                      | browser action -> API/bootstrap -> artifact finalization -> assertions                        | `frontend/e2e/fixtures/auth.ts`                                                           |
| `frontend/e2e/operational-immutability.spec.ts`               | nginx-backed v2 workflow matrix                                                      | authenticated browser -> v2 UI -> nginx/app/worker -> artifacts                               | `frontend/playwright.config.ts`, existing `frontend/e2e/` auth pattern                    |
| `docs/external-read-only-library-operations.md`               | Operator guide and maintenance procedure                                             | phase evidence + compose contract -> human ops guidance                                       | `docs/design/v2-storage-administration.md`, `examples/docker-compose.example.yml`         |
| `backend/tests/integration/test_scan_source_immutability.py`  | Existing manifest seed to extend or keep as narrow regression                        | source fixture -> manifest capture -> exact compare                                           | self                                                                                      |
| `frontend/playwright.config.ts`                               | E2E config extension point if nginx-only/proof-specific routing needs a project knob | env -> baseURL / workers / trace / webServer                                                  | self                                                                                      |

## Pattern 1: Compose proof stack must model explicit `:ro` and owned-write separation

**Use for:** `backend/docker-compose.immutability-test.yml`

**Analog:** [backend/docker-compose.policy-test.yml](/home/d1sk/romm/backend/docker-compose.policy-test.yml)

```yaml
services:
  policy-readonly:
    image: romm-romm-dev:latest
    working_dir: /workspace/backend
    entrypoint:
      - python3
      - /workspace/backend/tools/verify_read_only_policy.py
      - --probe
    volumes:
      - type: bind
        source: ${POLICY_FIXTURE_SOURCE:?set POLICY_FIXTURE_SOURCE}
        target: /policy/external
        read_only: true
      - type: bind
        source: ${POLICY_OWNED_OUTPUT:?set POLICY_OWNED_OUTPUT}
        target: /policy/owned
```

**Carry forward:**

- Use bind mounts with explicit `read_only: true` for the source fixture.
- Keep repo checkout itself read-only inside containers.
- Route all writable output to a separate owned target, never back into the source mount.
- Phase 9 extends this to a full app, worker, nginx, db, and queue topology instead of a single probe container.

## Pattern 2: Canonical manifest capture is deterministic, path-based, and hash-backed

**Use for:** `backend/tools/verify_operational_immutability.py`, `backend/tests/tools/test_verify_operational_immutability.py`

**Analog:** [backend/tests/integration/test_scan_source_immutability.py](/home/d1sk/romm/backend/tests/integration/test_scan_source_immutability.py)

```python
def source_manifest(root: Path):
    result = []
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().encode()):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            result.append((rel, "symlink", 0, ""))
        elif path.is_dir():
            result.append((rel, "directory", 0, ""))
        else:
            data = path.read_bytes()
            result.append((rel, "file", len(data), hashlib.sha256(data).hexdigest()))
    return tuple(result)
```

**Carry forward:**

- Keep byte-order sorting stable, do not use locale sort.
- Preserve relative-path identity and file type in the manifest.
- Expand from the current tuple shape to a versioned JSON schema with timestamps, mode, symlink target, completeness counters, and aggregate digest.
- Treat missing or extra entries as a hard failure before field-by-field comparison.

## Pattern 3: Harnesses should be fail-closed Python CLIs with owned temp roots

**Use for:** `backend/tools/verify_operational_immutability.py`

**Analog:** [backend/tools/verify_read_only_policy.py](/home/d1sk/romm/backend/tools/verify_read_only_policy.py)

```python
def _run_service(service: str, fixture: Path, owned: Path) -> dict[str, Any]:
    owned.mkdir()
    environment = os.environ | {
        "POLICY_FIXTURE_SOURCE": str(fixture),
        "POLICY_OWNED_OUTPUT": str(owned),
        "POLICY_REPO_ROOT": str(REPO_ROOT),
    }
    completed = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "run", "--rm", service],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
```

**Carry forward:**

- Build one Python entrypoint that owns environment setup, subprocess orchestration, and JSON evidence emission.
- Keep task-owned temp or artifact directories explicit and bounded.
- Use `capture_output=True` and structured JSON/known text markers for downstream parsing.
- Cleanup should only remove recorded, labeled resources that the harness created.

## Pattern 4: Storage and legacy workflows already expose the lifecycle edges Phase 9 must prove

**Use for:** backend harness workflow matrix and browser targets

**Analogs:** [backend/endpoints/storage.py](/home/d1sk/romm/backend/endpoints/storage.py), [backend/handler/storage/legacy_migration.py](/home/d1sk/romm/backend/handler/storage/legacy_migration.py), [frontend/src/services/api/storage.ts](/home/d1sk/romm/frontend/src/services/api/storage.ts)

```python
def preview_storage_mapping(
    mapping: PlatformStorageMapping,
    storage_root: StorageRoot,
    limit: int,
    cursor: str | None,
) -> StorageMappingPreview:
    directory = resolve_directory(storage_root, mapping.relative_path)
```

```python
@dataclass(frozen=True, slots=True)
class LegacyImpactPlannedEffects:
    mapping_create_count: int
    catalog_reconnect_count: int
    catalog_preserve_unmatched_count: int
    audit_record_count: int
    rollback_record_count: int
    source_mutation_count: int = 0
```

```ts
function browseRoot(rootId: number, parent = "", cursor?: string | null) {
  return api.get<StorageDirectoryPageSchema>(
    `/storage/roots/${rootId}/browse`,
    { params: { parent, cursor, limit: 50 } },
  );
}
```

**Carry forward:**

- Phase 9 should prove real storage browsing, preview, mapping, removal, migration, and rollback paths instead of duplicating them.
- Legacy migration already encodes a `source_mutation_count: 0` expectation, which should become executable evidence in the harness.
- Browser proof should target the real storage APIs and states the v2 client already calls.

## Pattern 5: Production file delivery proof must witness server-side path resolution and hidden nginx locations

**Use for:** harness workflow results, integration tests, browser download/stream evidence

**Analogs:** [docker/nginx/templates/default.conf.template](/home/d1sk/romm/docker/nginx/templates/default.conf.template), [backend/tests/endpoints/test_streaming.py](/home/d1sk/romm/backend/tests/endpoints/test_streaming.py), [backend/tests/endpoints/roms/test_files.py](/home/d1sk/romm/backend/tests/endpoints/roms/test_files.py)

```nginx
location /library/ {
    internal;
    alias "${ROMM_BASE_PATH}/library/";
}

location /cache/ {
    internal;
    alias "${ROMM_BASE_PATH}/cache/";
}
```

```python
def test_claim_derives_rom_path_server_side(client, access_token, rom: Rom):
    with _streaming(_container_for(rom)):
        with patch("endpoints.streaming._call_broker") as call_broker:
            r = _claim(client, access_token, rom.id)
    _, rom_path, _ = call_broker.call_args[0]
```

```python
def test_rom_file_served_as_attachment(...):
    r = client.get(
        f"/api/roms/{file.id}/files/content/game.bin",
        headers=_auth(access_token),
    )
    assert r.headers["content-disposition"].startswith("attachment")
```

**Carry forward:**

- Verify the app derives authorized file paths from DB identity, not browser input.
- Prove user-visible downloads and play/stream flows traverse nginx-backed internal locations.
- Negative proof should include that direct `/library/...` and `/cache/...` requests remain inaccessible.
- Result artifacts need both UI success and low-level service-path witness data.

## Pattern 6: Playwright is already configured for authenticated, production-like, deterministic E2E

**Use for:** `frontend/e2e/fixtures/operational-proof.ts`, `frontend/e2e/operational-immutability.spec.ts`, optional `frontend/playwright.config.ts` adjustments

**Analogs:** [frontend/playwright.config.ts](/home/d1sk/romm/frontend/playwright.config.ts), [frontend/e2e/fixtures/auth.ts](/home/d1sk/romm/frontend/e2e/fixtures/auth.ts)

```ts
use: {
  baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
  trace: "retain-on-failure",
  screenshot: "only-on-failure",
  serviceWorkers: "block",
},
```

```ts
export async function gotoHydrated(page: Page, path: string) {
  const hydrated = page
    .waitForResponse(
      (r) => r.url().includes("/api/permissions/me") && r.status() === 200,
      { timeout: 10_000 },
    )
    .catch(() => null);
  await page.goto(path);
  await hydrated;
  await expect(page.locator(".r-v2-user__name")).toBeVisible({
    timeout: 30_000,
  });
}
```

**Carry forward:**

- Point `E2E_BASE_URL` at nginx-backed app URLs for proof runs, not Vite or direct FastAPI.
- Reuse authenticated storage state and hydrated-shell waits instead of adding sleeps.
- Keep traces and failure screenshots because they fit the evidence bundle.
- Add a thin fixture layer for proof checkpoints and artifact finalization, not a second auth system.

## Pattern 7: Phase 9 UI work must stay inside existing v2 surfaces

**Use for:** browser spec scope and any minimal UI-facing instrumentation

**Analog:** [09-UI-SPEC.md](/home/d1sk/romm/.planning/phases/09-operational-immutability-proof/09-UI-SPEC.md)

```md
- storage root and mapping administration flows from the Phase 7 design direction
- authentication and boot flows required by the Phase 8 deferred smoke scope
- stream, play, and download surfaces that prove nginx-backed delivery
```

**Carry forward:**

- Do not create a proof-only dashboard or alternate route.
- Keep any proof status local to existing pages and regions.
- Prefer semantic selectors, visible route context, and existing success/error copy patterns.

## Pattern 8: Docs must align with executable safety contracts, not just feature descriptions

**Use for:** `docs/external-read-only-library-operations.md`, docs-verification tasks

**Analogs:** [09-CONTEXT.md](/home/d1sk/romm/.planning/phases/09-operational-immutability-proof/09-CONTEXT.md), [09-RESEARCH.md](/home/d1sk/romm/.planning/phases/09-operational-immutability-proof/09-RESEARCH.md), [docs/design/v2-storage-administration.md](/home/d1sk/romm/docs/design/v2-storage-administration.md)

**Carry forward:**

- The guide must describe one-root `:ro` mounting, separate owned storage, migration, removal, restart, noatime, and maintenance-window steps in the same terms the harness validates.
- Documentation checks should assert required sections and forbidden unsafe guidance such as Team4s operations or absolute host-path debug instructions.
- The guide is part of acceptance, not a post-hoc appendix.

## Recommended Plan Shape

1. Establish the manifest library, deterministic fixture, compose topology, and fast verifier tests.
2. Add backend harness workflow orchestration, service witnesses, restart/cleanup evidence, and docs contract checks.
3. Add nginx-backed Playwright proof flows against existing v2 surfaces, including Phase 8 deferred smoke.
4. Finish the operator guide, aggregate matrix, and full phase verification loop.
