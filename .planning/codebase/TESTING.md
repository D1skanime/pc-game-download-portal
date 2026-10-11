# Testing Patterns

**Analysis Date:** 2026-08-04

## Test Framework

**Runner:**

- Backend: pytest 9 with pytest-asyncio, pytest-cov, pytest-mock, pytest-recording, pytest-xdist, Hypothesis, and fakeredis, declared in `pyproject.toml`.
- Backend configuration and global fixtures: `backend/tests/conftest.py`; coverage exclusions: `backend/.coveragerc`.
- Frontend unit/component: Vitest 4 with happy-dom and Vue Test Utils, configured in `frontend/vitest.config.ts` and initialized by `frontend/vitest.setup.ts`.
- Frontend browser E2E: Playwright 1.61, configured in `frontend/playwright.config.ts`, with tests under `frontend/e2e/`.
- Component interaction/accessibility: Storybook stories under `frontend/src/v2/lib/` are composed and run by `frontend/test/storybook.test.ts`.

**Assertion Library:**

- Backend uses Python `assert`, pytest exception helpers, mock call assertions, and Hypothesis assertions.
- Frontend uses Vitest `expect` and Vue Test Utils wrappers; E2E uses Playwright's auto-waiting `expect`.

**Run Commands:**

```bash
cd backend && uv run pytest -vv                         # Run all backend tests
cd backend && uv run pytest tests/endpoints/roms/test_files.py -vv  # Focused backend tests
cd backend && uv run pytest -n 4 --cov --cov-report=term-missing .  # Parallel coverage run
cd frontend && npm test                                # Vitest unit, component, and Storybook tests
cd frontend && npm run test:watch                      # Vitest watch mode
cd frontend && npm run test:ui                         # Vitest UI
cd frontend && npm run test:e2e                        # Playwright E2E
cd frontend && npm run storybook:test                  # Storybook composition test only
```

## Test File Organization

**Location:**

- Mirror backend production layers under `backend/tests/`: endpoints in `backend/tests/endpoints/`, filesystem handlers in `backend/tests/handler/filesystem/`, database handlers in `backend/tests/handler/database/`, models in `backend/tests/models/`, tasks in `backend/tests/tasks/`, and utilities in `backend/tests/utils/`.
- Co-locate frontend unit/component tests with source as `*.test.ts` or `*.spec.ts`, for example `frontend/src/v2/components/Scan/ScanPlatform.test.ts` and `frontend/src/v2/lib/overlays/bodyScrollLock.spec.ts`.
- Put cross-cutting frontend harness tests in `frontend/test/`, Storybook stories beside primitives in `frontend/src/v2/lib/**/**.stories.ts`, and live workflow tests in `frontend/e2e/*.spec.ts`.
- Store backend HTTP recordings beside their test area under `backend/tests/**/cassettes/`; examples include `backend/tests/adapters/services/cassettes/test_steamgriddb/`.
- Store deterministic binary/YAML fixtures under a local `fixtures/` directory, such as `backend/tests/tasks/fixtures/` and `backend/tests/config/fixtures/config/`.

**Naming:**

- Backend files and functions use `test_<behavior>`. Use names that state the expected outcome and security boundary, such as `test_claim_hidden_rom_is_404_masked` in `backend/tests/endpoints/test_streaming.py`.
- Frontend suites name the component or behavior; individual `it()`/`test()` descriptions state user-observable outcomes, as in `frontend/src/v2/components/GameActions/GameActionsList.test.ts` and `frontend/e2e/login.spec.ts`.
- Regression tests should encode the original failure in their assertion and short comment, not depend on a vague bug-number-only name. `frontend/src/v2/components/Scan/ScanPlatform.test.ts` is the preferred pattern.

**Structure:**

```text
backend/tests/
├── conftest.py
├── endpoints/
│   ├── conftest.py
│   └── roms/
│       ├── conftest.py
│       └── test_files.py
├── handler/{auth,database,filesystem,metadata}/test_*.py
├── models/test_*.py
├── tasks/test_*.py
└── utils/test_*.py

frontend/
├── src/**/<subject>.test.ts
├── src/v2/lib/**/<Primitive>.stories.ts
├── test/storybook.test.ts
└── e2e/{auth.setup.ts,*.spec.ts,fixtures/}
```

## Test Structure

**Suite Organization:**

```python
class TestFSRomsHandler:
    @pytest.fixture
    def handler(self):
        return FSRomsHandler()

    @pytest.mark.asyncio
    async def test_get_roms(self, handler, platform, config):
        # Arrange filesystem/config, invoke one behavior, assert domain result.
        ...
```

```typescript
vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

describe("ScanPlatform", () => {
  it("shows the count of firmware discovered by this scan", () => {
    const wrapper = mountPlatform({ new_firmware_count: 2 });
    expect(wrapper.findAll(".r-tag")[1].text()).toBe("2");
  });
});
```

**Patterns:**

- Arrange using narrow fixtures/helpers, act once, then assert response, state, side effects, and forbidden side effects. Scanner examples are in `backend/tests/tasks/test_scan_library.py` and `backend/tests/handler/database/test_roms_handler.py`.
- Test public behavior at the lowest layer that owns the invariant, then add endpoint coverage for HTTP/auth/serialization boundaries. Filesystem parsing belongs in `backend/tests/handler/filesystem/test_roms_handler.py`; visibility and disposition belong in `backend/tests/endpoints/roms/test_files.py`.
- Use `@pytest.mark.asyncio` for async Python tests and await the real coroutine. For FastAPI concurrency, use `httpx.AsyncClient` with `ASGITransport`, as in `backend/tests/endpoints/test_streaming.py`.
- Reset shared DB/cache/store state between tests. `backend/tests/conftest.py` deletes persisted test rows and invalidates caches; `backend/tests/endpoints/conftest.py` flushes Redis; frontend Pinia tests call `setActivePinia(createPinia())` in `beforeEach`.
- Assert both success and denial paths for protected resources. A hidden ROM/platform must remain 404-masked in `backend/tests/endpoints/test_states.py`, `backend/tests/endpoints/test_screenshots.py`, and `backend/tests/endpoints/test_streaming.py`.
- Prefer semantic, auto-waiting browser assertions over sleeps or immediate counts. `frontend/e2e/fixtures/auth.ts` waits for the authenticated shell and permission hydration.

## Mocking

**Framework:**

- Backend: `pytest-mock`'s `mocker`, `unittest.mock` (`patch`, `Mock`, `MagicMock`, `AsyncMock`), pytest `monkeypatch`, and fakeredis.
- Frontend: Vitest `vi.mock`, `vi.fn`, `vi.hoisted`, `vi.mocked`; Vue Test Utils `global.stubs`; Playwright request/page fixtures for live dependencies.

**Patterns:**

```python
mock_scan_platforms = mocker.patch(
    "tasks.scheduled.scan_library.scan_platforms",
    side_effect=AsyncMock(return_value=scan_result),
)
await task.run()
mock_scan_platforms.assert_called_once_with(...)
```

```typescript
const { getRoms } = vi.hoisted(() => ({ getRoms: vi.fn() }));
vi.mock("@/services/api/rom", () => ({ default: { getRoms } }));
```

**What to Mock:**

- Mock external metadata services, brokers, network downloads, timers, and destructive filesystem writes at the namespace used by the subject. See `backend/tests/tasks/test_scan_library.py`, `backend/tests/endpoints/test_streaming.py`, and `backend/tests/handler/filesystem/test_resources_handler.py`.
- Mock configuration values when exercising feature gates or filesystem layouts; use `pytest.MonkeyPatch.context()` to restore state, as in `backend/tests/handler/filesystem/test_roms_handler.py`.
- Stub complex child Vue primitives when the parent test owns conditional rendering or orchestration, as in `frontend/src/v2/components/Scan/ScanPlatform.test.ts`.
- Mock frontend services/stores/composables in unit tests when testing a single component/composable contract. Use real Playwright API/session flows for E2E permission and navigation coverage.
- Use VCR recordings for external provider integration behavior so request matching remains deterministic; `backend/tests/conftest.py` matches method, scheme, host, port, path, query, and raw body.

**What NOT to Mock:**

- Do not mock SQLAlchemy models/database handlers in database integration tests. `backend/tests/conftest.py` migrates and cleans a real MariaDB/PostgreSQL test database, and tests such as `backend/tests/handler/database/test_roms_handler.py` verify persisted reconciliation.
- Do not mock path parsing, archive/hash logic, or file lifecycle when that is the behavior under test. Use controlled files/directories and cleanup in `backend/tests/handler/filesystem/` and `backend/tests/utils/`.
- Do not mock the login form in `frontend/e2e/login.spec.ts`; it is the canonical real login-flow test. Other E2E specs reuse saved sessions from `frontend/e2e/auth.setup.ts`.
- Do not duplicate component interaction assertions in both Vitest and Storybook. Use Vitest for pure logic/component contracts and Storybook `play()` for primitive interactions, per `.claude/skills/pre-pr-verification/SKILL.md`.

## Fixtures and Factories

**Test Data:**

```python
@pytest.fixture
def rom(admin_user: User, platform: Platform):
    rom = Rom(
        platform_id=platform.id,
        name="test_rom",
        fs_name="test_rom.zip",
        fs_path=f"{platform.slug}/roms",
        ...
    )
    rom = db_rom_handler.add_rom(rom)
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=admin_user.id)
    return rom
```

```typescript
function platform(id: number, displayName: string, romCount: number): Platform {
  return { id, display_name: displayName, rom_count: romCount, ... } as Platform;
}
```

**Location:**

- Put broadly reused DB/domain fixtures in `backend/tests/conftest.py`; endpoint auth/client fixtures in `backend/tests/endpoints/conftest.py`; feature-local fixtures in the nearest `conftest.py` or test module, such as `backend/tests/endpoints/roms/conftest.py`.
- Use distinct fixtures for semantically different persisted states. `save` and `archival_save` in `backend/tests/conftest.py` distinguish syncable slot saves from null-slot archival uploads.
- Use `tmp_path`, `tempfile`, or the controlled `backend/romm_test/` library for filesystem cases; always clean manually created files in `finally` when the fixture does not own cleanup.
- Put reusable E2E auth/session helpers in `frontend/e2e/fixtures/auth.ts`; saved storage-state files under `frontend/playwright/.auth/` are generated, gitignored session artifacts.
- Prefer small typed factory functions inside frontend test files for test-specific data; avoid a global fixture layer when only one suite uses the shape.

## Coverage

**Requirements:** No numeric threshold is enforced in `backend/.coveragerc` or `frontend/vitest.config.ts`. CI requires passing suites and collects backend coverage; new logic and endpoints are required to carry tests by `CLAUDE.md`.

**View Coverage:**

```bash
cd backend && uv run pytest --cov --cov-report=term-missing .
cd backend && uv run pytest --cov --cov-report=html .
cd frontend && npx vitest run --coverage   # coverage provider/config is not currently declared
```

- Backend CI writes `coverage.xml` via `.github/workflows/pytest.yml`; `backend/.coveragerc` omits migrations and test modules.
- Frontend CI runs `npm test` and `npm run build` in `.github/workflows/frontend.yml`; typechecking is a separate gate in `.github/workflows/typecheck.yml`.

## Test Types

**Unit Tests:**

- Test pure filename parsing, validation, archive/hash algorithms, comparison logic, model properties, and frontend utilities without HTTP. Representative files are `backend/tests/utils/test_filesystem.py`, `backend/tests/utils/test_rvz_hasher.py`, `backend/tests/models/test_base.py`, and `frontend/src/v2/utils/romVerification.test.ts`.
- Use Hypothesis for broad parser/filesystem/hash input coverage. Profiles in `backend/tests/conftest.py` run 50 examples locally and 200 in CI with no deadline.

**Integration Tests:**

- Backend endpoint tests use FastAPI `TestClient` or `httpx.AsyncClient`, real handlers/models/test databases, and controlled filesystem/cache dependencies. Examples are `backend/tests/endpoints/roms/test_files.py`, `backend/tests/endpoints/test_saves.py`, and `backend/tests/endpoints/test_streaming.py`.
- Database model/handler tests verify real persistence, relationships, defaults, indexes/query behavior, and scanner reconciliation in `backend/tests/models/` and `backend/tests/handler/database/`.
- External metadata clients use pytest-recording cassettes under `backend/tests/adapters/services/cassettes/` rather than live API calls on every run.
- API-contract integration is backend-owned: response schemas under `backend/endpoints/responses/` generate `frontend/src/__generated__/`. After a route/schema change, run `npm run generate` and `npm run typecheck`; do not substitute handwritten frontend interfaces.

**E2E Tests:**

- Playwright tests under `frontend/e2e/` cover real login, role/permission gating, navigation, ROM actions, and media/file affordances.
- `frontend/e2e/auth.setup.ts` authenticates each fixture role once and saves cookies/localStorage. `frontend/e2e/login.spec.ts` alone drives the login form from an unauthenticated context.
- `frontend/playwright.config.ts` runs Chromium with two workers by default, CI retries, retained traces, failure screenshots, blocked service workers, and a setup-project dependency.
- Seed fixture users with `.github/scripts/seed_e2e_users.py` before E2E runs, as documented in `frontend/playwright.config.ts`.

## Domain-Specific Coverage

**Scanners:**

- Cover scheduled task enable/disable behavior and exact metadata-source selection in `backend/tests/tasks/test_scan_library.py`.
- Cover filename/tag parsing, exclusions, single/multi-file layouts, category detection, hashing, and actual filesystem enumeration in `backend/tests/handler/filesystem/test_roms_handler.py`.
- Cover DB reconciliation semantics such as rename/move matching, partial hashes, deletion, metadata preservation, and orphan cleanup in `backend/tests/handler/database/test_roms_handler.py`.
- Cover scan result presentation and regression states in `frontend/src/v2/components/Scan/ScanPlatform.test.ts` and scan-priority UI in `frontend/src/v2/components/Settings/ScanPriorityList.test.ts`.

**Filesystem Handling and Downloads:**

- Test path validation, traversal resistance, file existence, content disposition, trusted content type, visibility, and category-specific behavior in `backend/tests/utils/test_filesystem.py`, `backend/tests/endpoints/roms/test_files.py`, and asset endpoint tests.
- Test partial download cleanup and provider concurrency slots in `backend/tests/handler/filesystem/test_resources_handler.py`.
- Test multi-file download naming and detached ORM relationships in `backend/tests/handler/test_db_handler.py`; test ZIP cache lifecycle and hidden paths in `backend/tests/utils/test_zip_cache.py`.
- For any changed download endpoint, assert status, bytes or redirect, `Content-Disposition`, media type, `X-Content-Type-Options` where inline, missing-file behavior, and authorization/visibility.

**Auth and Permissions:**

- Cover session, OAuth/OIDC, CSRF, permission dependency/resolver parity, and route auth under `backend/tests/handler/auth/` and `backend/tests/endpoints/test_permissions_*.py`.
- Use role-specific tokens from `backend/tests/endpoints/conftest.py`; assert unauthenticated, allowed, forbidden, and 404-masked cases.
- Cover frontend permission-driven rendering in `frontend/src/v2/components/GameActions/GameActionsList.test.ts` and live role behavior in `frontend/e2e/profile-role.spec.ts`, `frontend/e2e/rom-actions.spec.ts`, and `frontend/e2e/game-media-files.spec.ts`.

**Range Requests:**

- Range support is delegated to Starlette `FileResponse` in development and nginx `X-Accel-Redirect` in production, as documented in `backend/endpoints/roms/files.py` and `backend/utils/nginx.py`.
- Bulk and multi-file ROM Range branching exists in `backend/endpoints/roms/__init__.py`. Exercise both Range and non-Range branches when changing this code, including `206`, `Content-Range`, `Accept-Ranges`, resumable cached ZIP behavior, invalid/unsatisfiable ranges, and auth/visibility.
- Dedicated HTTP Range assertions were not detected in `backend/tests/endpoints/roms/test_files.py`. Treat Range behavior as a regression-sensitive integration gap when modifying file serving.

**Database Models and Migrations:**

- Test derived columns, validation hooks, relationships, cascade behavior, cached properties, and serialization in `backend/tests/models/test_base.py`, `backend/tests/models/test_rom.py`, and related handler tests.
- Migrations under `backend/alembic/versions/` must be reversible and cross-dialect. Use `op.batch_alter_table` and guarded create/drop operations where appropriate, following `backend/alembic/versions/0106_hash_search_indexes.py` and `backend/alembic/versions/0107_roms_dedup_cover_index.py`.
- Run `uv run alembic upgrade head` and `uv run alembic downgrade -1` locally for changed migrations. CI upgrade coverage runs on MariaDB and PostgreSQL in `.github/workflows/migrations.yml`; downgrade verification remains a required local handoff check.
- Backend pytest CI also runs the full suite against both MariaDB and PostgreSQL in `.github/workflows/pytest.yml` with per-xdist-worker databases created by `backend/tests/conftest.py`.

**Frontend API Contracts:**

- Treat FastAPI response/request schemas as the source of truth and `frontend/src/__generated__/` as generated artifacts. The generation command is defined in `frontend/package.json`.
- Import generated types in services/stores/components, as `frontend/src/services/api/rom.ts` does. Test frontend mapping, query construction, cancellation, retries, and UI behavior around the typed service rather than redefining backend payloads.
- After backend route or response-schema changes: run the backend endpoint tests, start the backend, run `npm run generate`, inspect the generated diff, run `npm run typecheck`, and run affected frontend tests.
- No standalone schema snapshot/contract-diff test was detected. Generated-file review plus frontend typecheck is the current contract gate.

## Common Patterns

**Async Testing:**

```python
@pytest.mark.asyncio
async def test_concurrent_claim_only_one_succeeds(access_token, rom):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        first, second = await asyncio.gather(...)
    assert sorted([first.status_code, second.status_code]) == [200, 409]
```

```typescript
it("uploads after resolving the platform", async () => {
  const wrapper = mount(Upload, { ... });
  await flushPromises();
  await wrapper.get(".upload").trigger("click");
  await flushPromises();
  expect(uploadRoms).toHaveBeenCalledWith(...);
});
```

**Error Testing:**

```python
with patch("endpoints.streaming._call_broker", side_effect=HTTPException(503)):
    failed = _claim(client, token, rom.id)
retry = _claim_ok(client, token, rom.id)
assert failed.status_code == 503
assert retry.status_code == 200  # failed work released shared state
```

```typescript
await expect(page.locator(".r-v2-user__name")).toHaveCount(0);
await expect(page).toHaveURL(/\/login/);
```

- For failure paths, assert cleanup and absence of side effects in addition to the error itself: no broker call for hidden ROMs, no stale claim after launch failure, no partial file after download failure, no destructive controls for read-only users.
- Use `pytest.raises` for pure exceptions, HTTP status/detail assertions for endpoints, rejected mocks for frontend async failures, and Playwright-visible outcomes for browser workflows.

---

_Testing analysis: 2026-08-04_
