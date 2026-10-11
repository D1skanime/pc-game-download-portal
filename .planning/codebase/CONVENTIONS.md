# Coding Conventions

**Analysis Date:** 2026-08-04

## Naming Patterns

**Files:**

- Use lowercase `snake_case.py` for backend modules and mirror implementation areas under `backend/tests/`, for example `backend/handler/filesystem/roms_handler.py` and `backend/tests/handler/filesystem/test_roms_handler.py`.
- Name Python tests `test_<subject>.py`; group related behavior in `TestPascalCase` classes only when a shared subject or fixture makes the grouping useful, as in `backend/tests/tasks/test_scan_library.py` and `backend/tests/endpoints/test_saves.py`.
- Use PascalCase for Vue component files and co-locate frontend tests as `<Component>.test.ts`, for example `frontend/src/v2/components/Scan/ScanPlatform.vue` and `frontend/src/v2/components/Scan/ScanPlatform.test.ts`.
- Use `index.ts` only for multi-file v2 composables and primitive barrels. Primitive folders use `RFoo/RFoo.vue`, `RFoo/RFoo.stories.ts`, and `RFoo/index.ts`, as demonstrated under `frontend/src/v2/lib/forms/RSelect/`.
- Treat `frontend/src/__generated__/` as generated output. Regenerate it with `frontend/package.json`'s `generate` command; never hand-edit files such as `frontend/src/__generated__/models/SimpleRomSchema.ts`.
- Name Alembic revisions with a four-digit sequence and descriptive suffix, for example `backend/alembic/versions/0106_hash_search_indexes.py`. Keep `revision` and `down_revision` aligned with that chain.

**Functions:**

- Use `snake_case` for Python functions, methods, fixtures, and tests, as in `compute_file_name_parts` in `backend/models/base.py` and `test_claim_hidden_rom_is_404_masked` in `backend/tests/endpoints/test_streaming.py`.
- Prefix private backend helpers with `_`, for example `_ensure_database_exists` in `backend/tests/conftest.py` and `_access_token` in `backend/tests/endpoints/test_streaming.py`.
- Use `camelCase` for TypeScript functions and helpers, with `use` prefixes for composables, as in `mountPlatform` in `frontend/src/v2/components/Scan/ScanPlatform.test.ts` and `useGameActions` under `frontend/src/v2/composables/useGameActions/`.
- Name Vue test helpers for their intent (`mountList`, `labels`, `gotoHydrated`) rather than exposing incidental implementation details; see `frontend/src/v2/components/GameActions/GameActionsList.test.ts` and `frontend/e2e/fixtures/auth.ts`.

**Variables:**

- Use `snake_case` in Python and `camelCase` in TypeScript. Constants use `UPPER_SNAKE_CASE` in both stacks, for example `FILE_NAME_MAX_LENGTH` in `backend/models/base.py` and `UPLOAD_CHUNK_SIZE` in `frontend/src/services/api/rom.ts`.
- Give mocks behavior-oriented names (`mock_scan_platforms`, `call_broker`, `getRoms`) and use a leading underscore for intentionally unused arguments, consistent with `frontend/eslint.config.js` and backend examples in `backend/tests/endpoints/test_saves.py`.
- Prefer explicit domain names such as `rom_file`, `platform_id`, and `viewer_access_token`; preserve the backend's snake_case API fields when consuming generated contracts in `frontend/src/__generated__/`.

**Types:**

- Use `PascalCase` for Python classes, enums, TypedDicts, and TypeScript interfaces/types, as in `RomFileCategory`, `RomArchiveMember`, and `GetRomsParams` in `backend/models/rom.py` and `frontend/src/services/api/rom.ts`.
- Type SQLAlchemy models with `Mapped[T]` and `mapped_column`; declare relationships explicitly, as in `backend/models/rom.py`.
- Use Python 3.13 union syntax (`str | None`, `list[T]`) and precise return annotations. Use `TYPE_CHECKING` imports to break model cycles, as in `backend/models/rom.py`.
- Use generated OpenAPI types from `frontend/src/__generated__/` for backend-owned payloads. Define local interfaces only for frontend-specific inputs or derived state, as in `GetRomsParams` in `frontend/src/services/api/rom.ts`.
- Keep TypeScript strict: avoid `any` and double assertions. `frontend/tsconfig.json` enforces `noImplicitAny`; v2 guidance is documented in `.claude/skills/frontend-v2-components/SKILL.md`.

## Code Style

**Formatting:**

- Run `trunk fmt` from the repository root. `.trunk/trunk.yaml` coordinates Black, isort, Prettier, shfmt, and other formatters.
- Python follows Black-compatible formatting with four-space indentation, trailing commas in multiline calls, and double-quoted strings. Examples are in `backend/models/base.py` and `backend/endpoints/roms/files.py`.
- TypeScript and Vue use Prettier through `.trunk/trunk.yaml`; retain semicolons, double quotes, trailing commas, and two-space indentation, as shown in `frontend/src/services/api/rom.ts`.
- Keep all code, comments, identifiers, and Markdown in English. Do not use em dashes. These repository-wide constraints are in `CLAUDE.md`.
- Keep comments concise and focused on non-obvious reasons or invariants. Security and concurrency explanations in `backend/endpoints/roms/files.py`, `backend/tests/endpoints/test_streaming.py`, and `frontend/e2e/fixtures/auth.ts` are the model.

**Linting:**

- Run `trunk check` from the root. `.trunk/trunk.yaml` enables Ruff, Black, isort, mypy, Bandit, ESLint, Prettier, dependency/security scanners, and format checks.
- Frontend ESLint configuration lives in `frontend/eslint.config.js`. Use PascalCase component tags, camelCase props, hyphenated template attributes, and prefix intentionally unused variables or arguments with `_`.
- Do not lint or edit generated OpenAPI output directly; both `.trunk/trunk.yaml` and `frontend/eslint.config.js` exclude `frontend/src/__generated__/`.
- Keep backend type checks compatible with `.trunk/configs/mypy.ini` and lint rules in `.trunk/configs/ruff.toml`. Alembic files under `backend/alembic/` are excluded from mypy because Alembic injects runtime globals.
- Never bypass hooks with `--no-verify`; `CLAUDE.md` and `.claude/skills/pre-pr-verification/SKILL.md` make this a repository rule.

## Import Organization

**Order:**

1. Standard-library or platform imports, including `__future__`, `pathlib`, `typing`, and Node built-ins.
2. Third-party imports such as FastAPI, SQLAlchemy, Vue, Vitest, or Axios.
3. Project-local imports, grouped by layer or alias.
4. Type-only imports use `import type` in TypeScript and `TYPE_CHECKING` blocks in Python when needed to avoid runtime cycles.

- Keep imports explicit and avoid wildcard imports. Backend examples are `backend/models/rom.py` and `backend/endpoints/roms/files.py`.
- Prefer importing patch targets from the module where the symbol is used, then patch that namespace in tests, as in `backend/tests/tasks/test_scan_library.py` and `backend/tests/endpoints/test_streaming.py`.
- Let Prettier's import-sort plugin configured in `.trunk/trunk.yaml` settle frontend ordering; do not manually fight generated formatting.

**Path Aliases:**

- Use `@/` for canonical shared frontend resources and `@v2/` for v2 code. Aliases are configured in `frontend/tsconfig.json` and `frontend/vitest.config.ts`.
- Import primitives from the `@v2/lib` barrel; import v2 composites directly via `@/v2/...`. Do not create composite barrels solely to shorten imports. See `.claude/skills/frontend-v2-components/SKILL.md`.
- Backend imports are rooted at `backend/` modules (`from handler...`, `from models...`, `from utils...`) because commands and tests run from `backend/`; examples are in `backend/tests/conftest.py`.

## Error Handling

**Patterns:**

- Keep FastAPI endpoints thin: validate inputs, enforce scopes/visibility, call handlers, and serialize response schemas. `backend/endpoints/roms/files.py` demonstrates `@protected_route`, `assert_can`, `assert_rom_visible`, and handler delegation.
- Raise a typed exception from `backend/exceptions/` when one exists; use `HTTPException` for endpoint-specific status/detail behavior. Preserve exception chaining with `raise ... from exc`, as in `backend/endpoints/roms/files.py`.
- Security-sensitive lookups must 404-mask hidden or unauthorized resources rather than disclose existence. Tests in `backend/tests/endpoints/test_streaming.py`, `backend/tests/endpoints/test_states.py`, and `backend/tests/endpoints/test_screenshots.py` enforce this.
- Validate filesystem paths through ownership-specific handlers before reading, writing, or deleting. Cover missing files, invalid paths, and cleanup behavior in tests such as `backend/tests/endpoints/test_saves.py` and `backend/tests/handler/filesystem/test_resources_handler.py`.
- For frontend promises, surface domain errors through the shared snackbar/error seams and keep async failures testable. Upload code in `frontend/src/services/api/rom.ts` cancels a failed chunked upload, records store failure, and rejects for the caller.
- Use `Promise.allSettled` when independent uploads should all reach a terminal state; use retries only around bounded transient work, with explicit limits such as `MAX_CHUNK_RETRIES` in `frontend/src/services/api/rom.ts`.

## Logging

**Framework:** Backend structured logger in `backend/logger/`; frontend production errors may use `console.error`.

**Patterns:**

- Use `log.info`, `log.warning`, and `log.error` from `backend/logger/logger.py`; format highlighted values with helpers from `backend/logger/formatter.py`, as in `backend/endpoints/roms/files.py`.
- Include actor and resource context for downloads, scans, deletes, and background tasks without logging credentials or tokens. Scanner log assertions in `backend/tests/tasks/test_scan_library.py` show expected stable messages.
- Pass `exc_info=exc` when a backend error needs a traceback. Do not silently swallow unexpected filesystem failures.
- Do not ship frontend `console.log` or `console.warn`; `console.debug` is development-only. The only test-oriented `console.warn` exception is the explicit accessibility `todo` ratchet in `frontend/test/storybook.test.ts`.

## Comments

**When to Comment:**

- Explain security boundaries, lifecycle constraints, concurrency ordering, cross-dialect SQL, or intentionally surprising behavior. Good examples include trusted filename handling in `backend/endpoints/roms/files.py`, per-worker database creation in `backend/tests/conftest.py`, and auth hydration ordering in `frontend/e2e/fixtures/auth.ts`.
- Do not narrate obvious control flow or explain historical edits. Keep the comment about the current invariant and place regression context in the test name or short test comment.
- Use issue references sparingly when they clarify a regression contract, as in `frontend/src/v2/components/Scan/ScanPlatform.test.ts`.

**JSDoc/TSDoc:**

- Use Python docstrings for public functions/classes or fixtures whose semantics are not evident, especially domain distinctions such as `save` versus `archival_save` in `backend/tests/conftest.py`.
- Use TSDoc on reusable frontend helpers when callers need behavioral guarantees, as in `login`, `gotoFirstRom`, and `gotoHydrated` in `frontend/e2e/fixtures/auth.ts`.
- Do not add documentation comments that merely repeat types or names.

## Function Design

**Size:** Keep endpoints and UI handlers small by extracting reusable domain logic into `backend/handler/`, `backend/utils/`, frontend services, stores, or composables. Large domain workflows may remain cohesive when their phases and invariants are explicit, such as scanner reconciliation in `backend/handler/database/roms_handler.py`.

**Parameters:**

- Prefer keyword-friendly typed parameters and small request models. Use FastAPI `Annotated` constraints for path/query values, as in `backend/endpoints/roms/files.py`.
- Use typed object parameters for TypeScript functions with several related inputs, as in `uploadRomChunked` and `getRoms` in `frontend/src/services/api/rom.ts`.
- Inject dependencies through pytest fixtures and test helper arguments. Do not access shared mutable test state without resetting it, as shown in `backend/tests/conftest.py` and `frontend/src/stores/platforms.test.ts`.

**Return Values:**

- Return typed ORM/domain objects from handlers and Pydantic response schemas from endpoints. Keep generated OpenAPI output consistent with `backend/endpoints/responses/`.
- Use explicit `None`/nullability and structured result objects when callers need cleanup metadata, as scanner database tests in `backend/tests/handler/database/test_roms_handler.py` demonstrate.
- Frontend service functions should return typed data or a promise whose rejection remains observable; avoid undocumented response-shape inference.

## Module Design

**Exports:**

- Backend layers follow endpoint -> handler -> database/filesystem/metadata -> models/adapters. Put HTTP concerns in `backend/endpoints/`, business logic in `backend/handler/`, models in `backend/models/`, and shared pure helpers in `backend/utils/`.
- New frontend work belongs in `frontend/src/v2/`; `frontend/src/views/`, `frontend/src/components/`, `frontend/src/console/`, and `frontend/src/layouts/` are frozen v1 code per `CLAUDE.md`.
- V2 primitives under `frontend/src/v2/lib/` must be domain-neutral, use the `R` prefix, and must not import stores, services, router, emitter, or i18n. Shared and feature composites belong under `frontend/src/v2/components/shared/` and `frontend/src/v2/components/<feature>/`.
- API response schemas are backend-owned. After changing a route signature or response model under `backend/endpoints/`, regenerate `frontend/src/__generated__/` and run the frontend typecheck.

**Barrel Files:**

- Re-export all v2 primitives from `frontend/src/v2/lib/index.ts` and import them via `@v2/lib`.
- Do not add barrels for composites; import composites directly by alias.
- A v2 composable may expose one named export from `frontend/src/v2/composables/useFoo/index.ts`; keep initialization free of module-load side effects.

---

_Convention analysis: 2026-08-04_
