# Testing Patterns

**Analysis Date:** 2026-10-15

## Test Framework

**Runner:**

- Backend uses pytest 9 with pytest-asyncio, pytest-cov, pytest-env, pytest-mock, pytest-recording, pytest-xdist, Hypothesis, and fakeredis from `pyproject.toml`.
- Backend defaults are in `backend/pytest.ini`: `asyncio_mode = auto`, function-scoped async loops, and `testpaths = tests`.
- Frontend uses Vitest 4, happy-dom, Vue Test Utils, and Storybook annotations via `frontend/vitest.config.ts` and `frontend/vitest.setup.ts`.
- Browser E2E uses Playwright 1.61 via `frontend/playwright.config.ts`.
- Stories under `frontend/src/v2/lib/` are composed and run by `frontend/test/storybook.test.ts`.

**Assertion Library:**

- Backend uses Python `assert`, pytest exception helpers, mock call assertions, parametrization, and Hypothesis.
- Frontend uses Vitest `expect` and Vue Test Utils. Playwright uses auto-waiting `expect`.
- Storybook tests use composed story `run()` helpers and axe-core accessibility assertions.

**Run Commands:**

```bash
cd backend && uv run pytest -vv
cd backend && uv run pytest tests/endpoints/roms/test_files.py -vv
cd backend && uv run pytest -n 4 --cov --cov-report=term-missing .
cd frontend && npm test
cd frontend && npm run test:watch
cd frontend && npm run test:ui
cd frontend && npm run storybook:test
cd frontend && npm run test:e2e
cd frontend && npm run typecheck
cd frontend && npm run build
```

## Test File Organization

**Location:**

- Current inventory: 201 backend pytest files under `backend/tests/`, 115 frontend unit/component files under `frontend/src/` and `frontend/test/`, 9 Playwright setup/spec files under `frontend/e2e/`, and 52 Storybook-related files under `frontend/src/v2/` and `frontend/test/`.
- Mirror backend layers under `backend/tests/`: endpoints, filesystem handlers, database handlers, metadata handlers, adapters, tasks, models, and utilities.
- Co-locate frontend tests as `*.test.ts` or `*.spec.ts`, for example `frontend/src/v2/components/GameDetails/LocalizedDescriptionEditor.test.ts` and `frontend/src/v2/composables/useGalleryVirtualItems/packFlowRows.test.ts`.
- Put shared frontend harness tests in `frontend/test/`, primitive stories beside code in `frontend/src/v2/lib/**/**.stories.ts`, and workflow tests in `frontend/e2e/*.spec.ts`.
- Store provider recordings under `backend/tests/**/cassettes/` and deterministic fixtures under nearby `fixtures/` directories.

**Naming:**

- Backend names encode expected outcomes and security boundaries, such as `test_claim_hidden_rom_is_404_masked` in `backend/tests/endpoints/test_streaming.py`.
- Frontend suite names identify the component or behavior, and `it()` descriptions state user-observable outcomes.
- Regression tests assert the original failure mode rather than only a bug number. Follow `frontend/src/v2/components/Scan/ScanPlatform.test.ts`.

**Structure:**

`backend/tests/
|-- conftest.py
|-- endpoints/{roms,sockets}/test_*.py
|-- handler/{auth,database,filesystem,metadata}/test_*.py
|-- adapters/services/test_*.py
|-- models/test_*.py
|-- tasks/test_*.py
`-- utils/test_*.py

frontend/
|-- src/**/<subject>.test.ts
|-- src/v2/lib/**/<Primitive>.stories.ts
|-- test/{storybook,smoke,utils}.test.ts
`-- e2e/{auth.setup.ts,*.spec.ts,fixtures/}

`

## Test Structure

**Suite Organization:**

```python
@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_get_config_requires_auth(client):
    assert client.get("/api/streaming/config").status_code == 401
```

Use fixtures for clients, authenticated users, storage roots, and external boundaries, then assert status, payload, side effects, and security masking. This pattern is in `backend/tests/endpoints/test_streaming.py`.

```typescript
describe("packFlowRows", () => {
  it("fills a row until the next card would overflow, then wraps", () => {
    const rows = packFlowRows(0, 7, 340, 100, 12, () => 1);
    expect(rows).toEqual([
      { start: 0, end: 3 },
      { start: 3, end: 6 },
      { start: 6, end: 7 },
    ]);
  });
});
```

This style in `frontend/src/v2/composables/useGalleryVirtualItems/packFlowRows.test.ts` covers empty, boundary, mixed-width, and over-wide inputs.

- Use source-contract assertions only when mounting would obscure the contract, as in `frontend/src/v2/components/GameDetails/LocalizedDescriptionEditor.test.ts`.
- Keep global setup minimal. `frontend/vitest.setup.ts` installs Storybook preview annotations for every Vitest test.

**Patterns:**

- Use fixture dependency injection and autouse isolation for backend database state.
- Use `TestClient` for sync endpoints and explicit `pytest.mark.asyncio` for direct async behavior.
- Use `pytest.mark.parametrize` for role, status, dialect, and boundary matrices.
- Make hydration and permission readiness explicit in frontend helpers.

## Mocking

**Framework:** pytest-mock and `unittest.mock`; Vitest mocks; Playwright request/page APIs.

**Patterns:**

```python
with patch("endpoints.streaming._call_broker") as call_broker:
    response = _claim(client, access_token, rom.id)
assert response.status_code == 200
call_broker.assert_called_once()
```

Patch the namespace under test, as in `backend/tests/endpoints/test_streaming.py`. Use `mocker.patch.object` for queues, Redis, socket emitters, and external services, as in `backend/tests/endpoints/sockets/test_scan.py`.

```typescript
const source = readFileSync(
  "src/v2/components/GameDetails/LocalizedDescriptionEditor.vue",
  "utf8",
);
expect(source).toContain("expectedVersion");
```

Prefer public rendered behavior when a component can be mounted cleanly.

**What to Mock:**

- Mock brokers, queues, sockets, Redis, external metadata APIs, and network calls at boundaries.
- Replay provider behavior with VCR cassettes under `backend/tests/adapters/services/cassettes/`.
- Mock filesystem permissions and storage health for storage-boundary tests, as in `backend/tests/endpoints/test_streaming.py`.

**What NOT to Mock:**

- Do not mock the handler or service under direct test.
- Do not bypass database constraints in endpoint and handler tests.
- Do not use live provider calls in ordinary tests when cassettes or fixtures suffice.

## Fixtures and Factories

**Test Data:**

- Shared fixtures in `backend/tests/conftest.py` create databases, users, platforms, ROMs, files, saves, states, screenshots, tokens, and storage entities.
- Autouse `setup_database` applies Alembic migrations. Autouse `clear_database` deletes domain rows and invalidates gallery filter caches before each test.
- Hypothesis profiles in `backend/tests/conftest.py` use 50 examples in `dev` and 200 in `ci`, selected by `HYPOTHESIS_PROFILE`.
- Frontend E2E accounts and storage state are defined in `frontend/e2e/fixtures/auth.ts`; users and library are seeded by `.github/scripts/seed_e2e_users.py` and `.github/scripts/seed_e2e_library.py`.

**Location:**

- Shared backend fixtures: `backend/tests/conftest.py`.
- Scoped endpoint fixtures: `backend/tests/endpoints/conftest.py` and nested `conftest.py` files.
- Frontend setup: `frontend/vitest.setup.ts` and `frontend/test/`.
- E2E helpers and auth state: `frontend/e2e/fixtures/` and `frontend/e2e/auth.setup.ts`.

## Coverage

**Requirements:** Backend CI collects coverage and emits `backend/coverage.xml`, but no threshold or `fail-under` gate is declared in `backend/.coveragerc`, `pyproject.toml`, or workflows. Frontend coverage is not an npm script or CI gate.

**View Coverage:**

```bash
cd backend && uv run pytest --cov --cov-report=term-missing .
cd backend && uv run pytest --cov --cov-report=html .
```

## Test Types

**Unit Tests:**

- Backend handler, adapter, model, utility, and task tests live under `backend/tests/`; real SQLAlchemy test databases cover most data paths.
- Frontend utilities and composables are tested directly; components use focused mounts or explicit source-contract tests.
- Storybook primitive tests cover rendered interaction and accessibility.

**Integration Tests:**

- Endpoint tests use FastAPI with real database fixtures, Redis/fakeredis, temporary filesystem paths, and mocked external calls.
- Provider integration tests use recordings under `backend/tests/adapters/services/cassettes/`.
- Migration tests include `backend/tests/alembic/test_mapping_preview_migration.py` and CI upgrade/downgrade cycles on PostgreSQL, MariaDB, and MySQL.
- E2E CI provisions MariaDB and Valkey, starts the API, seeds data, and runs the frontend against a Vite server.

**E2E Tests:**

- `frontend/e2e/` covers login, role visibility, ROM actions, PC media/DLC workflows, operational immutability, and media files.
- `frontend/e2e/auth.setup.ts` creates admin and viewer storage state. `frontend/e2e/login.spec.ts` is the only spec that drives the login form.
- Playwright runs Chromium with two workers by default, blocks service workers, retains failure traces, and captures screenshots on failure.
- E2E needs seeded users/library and a running backend. Use `.github/workflows/e2e.yml` as the canonical sequence.

## Common Patterns

**Async Testing:**

```python
@pytest.mark.asyncio
async def test_socket_handler(...):
    result = await handler(...)
    assert result == expected
```

Use `asyncio_mode = auto` from `backend/pytest.ini`.

**Error Testing:**

```python
with pytest.raises(ExpectedException, match="expected detail"):
    call_under_test()
```

For HTTP errors assert status and detail. For hidden resources assert 404. In frontend E2E assert stable state, role, or data contract rather than brittle toast copy, following `frontend/e2e/login.spec.ts`.

## CI Gates and Verification Matrix

| Change area           | Required gates                                                               | Workflow or config                                                  |
| --------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Backend code/tests    | Pytest on MariaDB and PostgreSQL, coverage artifact, Trunk                   | `.github/workflows/pytest.yml`, `.github/workflows/trunk-check.yml` |
| Frontend code         | Vitest plus composed Storybook tests, production build, TypeScript typecheck | `.github/workflows/frontend.yml`, `.github/workflows/typecheck.yml` |
| Frontend E2E behavior | Seeded backend/library, Playwright Chromium suite                            | `.github/workflows/e2e.yml`                                         |
| Locale JSON           | Locale parity and sorted-key checks                                          | `.github/workflows/i18n.yml`                                        |
| Alembic migrations    | Upgrade and downgrade/re-upgrade on PostgreSQL, MariaDB, MySQL               | `.github/workflows/migrations.yml`                                  |
| v1 frontend paths     | Frozen-directory diff check, bypass only with `allow-v1-changes` label       | `.github/workflows/frontend-v1-frozen.yml`                          |
| All PRs               | Trunk lint, format, security, and dependency checks                          | `.github/workflows/trunk-check.yml`                                 |

## Practical Verification Checklist

1. Run the narrowest relevant backend pytest or frontend Vitest subset first.
2. Run the full backend matrix command from `.github/workflows/pytest.yml` for shared backend changes.
3. Run `npm run typecheck`, `npm test`, and `npm run build` for frontend changes.
4. Run `npm run generate` before typecheck after a backend route or response-schema change.
5. Run both locale checks for locale changes.
6. Run Playwright with seeded users and library for visible workflow changes.
7. Run migration upgrade and downgrade/re-upgrade on all supported database engines for migration changes.
8. Run `trunk fmt && trunk check` before handoff. Do not use `--no-verify`.

---

_Testing analysis: 2026-10-15_
