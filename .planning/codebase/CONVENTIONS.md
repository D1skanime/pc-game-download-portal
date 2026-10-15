# Coding Conventions

**Analysis Date:** 2026-10-15

## Naming Patterns

**Files:**

- Use lowercase `snake_case.py` for backend modules and mirror them under `backend/tests/`, for example `backend/handler/filesystem/roms_handler.py` and `backend/tests/handler/filesystem/test_roms_handler.py`.
- Name Python tests `test_<behavior>.py`; use `TestPascalCase` classes only for one subject with shared fixtures, as in `backend/tests/tasks/test_scan_library.py`.
- Use PascalCase Vue component files and co-locate frontend tests as `<Component>.test.ts`, for example `frontend/src/v2/components/Scan/ScanPlatform.test.ts`.
- Primitive folders use `RFoo/RFoo.vue`, `RFoo/RFoo.stories.ts`, and `RFoo/index.ts`, as in `frontend/src/v2/lib/forms/RSelect/`.
- Treat `frontend/src/__generated__/` as generated OpenAPI output. Regenerate with `frontend/package.json`'s `generate` script and never hand-edit it.
- Name Alembic revisions with a four-digit sequence and descriptive suffix, for example `backend/alembic/versions/0106_hash_search_indexes.py`.

**Functions:**

- Use `snake_case` for Python functions, fixtures, and tests, with `_` for private helpers.
- Use `camelCase` for TypeScript functions and helpers, and `use` prefixes for composables such as `useGalleryVirtualItems`.
- Name test helpers for intent, such as `mountList`, `labels`, and `gotoHydrated`.
- Use behavior-oriented mock names, such as `mock_scan_platforms`, `call_broker`, and `getRoms`.

**Variables:**

- Use `snake_case` in Python and `camelCase` in TypeScript. Constants use `UPPER_SNAKE_CASE`.
- Prefer explicit domain names such as `rom_file`, `platform_id`, and `viewer_access_token`.
- Prefix intentionally unused TypeScript values with `_`, matching `frontend/eslint.config.js`.

**Types:**

- Use PascalCase for Python classes, enums, TypedDicts, and TypeScript interfaces/types.
- Type SQLAlchemy models with `Mapped[T]` and `mapped_column`, as in `backend/models/rom.py`.
- Use Python 3.13 union syntax and precise return annotations.
- Use generated OpenAPI types from `frontend/src/__generated__/` for backend-owned payloads. Keep local interfaces for frontend-only state.
- Keep TypeScript strict. `frontend/tsconfig.json` enables `noImplicitAny`; avoid `any` and double assertions.

## Code Style

**Formatting:**

- Run `trunk fmt` from the repository root. `.trunk/trunk.yaml` coordinates Black, isort, Prettier, shfmt, and related formatters.
- Python uses four-space indentation, Black-compatible formatting, trailing commas in multiline calls, and double-quoted strings.
- TypeScript and Vue use Prettier, semicolons, double quotes, trailing commas, and two-space indentation.
- Keep code, comments, identifiers, Markdown, and commit messages in English. Do not use em dashes.
- Keep comments short and explain only non-obvious reasons or invariants.

**Linting:**

- Run `trunk check` from the root. It covers Ruff, Black, isort, mypy, Bandit, ESLint, Prettier, dependency/security scanners, and format checks.
- Frontend ESLint rules live in `frontend/eslint.config.js`: PascalCase component tags, camelCase props, hyphenated template attributes, and unused-variable prefixes.
- Generated OpenAPI output is excluded by `.trunk/trunk.yaml` and `frontend/eslint.config.js`; do not lint or edit it directly.
- Keep backend checks compatible with `.trunk/configs/mypy.ini` and `.trunk/configs/ruff.toml`. Alembic files under `backend/alembic/` are excluded from mypy.
- Never bypass hooks with `--no-verify`.

## Import Organization

**Order:**

1. Standard-library or platform imports.
2. Third-party imports such as FastAPI, SQLAlchemy, Vue, Vitest, or Axios.
3. Project-local imports, grouped by layer or alias.
4. Type-only imports via `import type` or Python `TYPE_CHECKING`.

- Keep imports explicit and avoid wildcard imports.
- Patch the symbol in the namespace where production code looks it up, as in `backend/tests/endpoints/test_streaming.py`.
- Let configured Prettier import sorting settle frontend ordering.

**Path Aliases:**

- Use `@/` for shared frontend resources and `@v2` for v2 code, configured in `frontend/tsconfig.json` and `frontend/vitest.config.ts`.
- Import primitives from the `@v2/lib` barrel and v2 composites directly through `@/v2/...`.
- Avoid relative paths when an alias exists.
- Backend tests run from `backend/` and use imports rooted at `handler`, `models`, and `utils`.

## Error Handling

**Patterns:**

- Keep FastAPI endpoints thin: validate, enforce scopes and visibility, delegate, and serialize. Follow `backend/endpoints/roms/files.py`.
- Raise typed exceptions from `backend/exceptions/` when available. Use `HTTPException` for endpoint-specific behavior and preserve chaining with `raise ... from exc`.
- Security-sensitive lookups must 404-mask hidden resources. Preserve coverage in `backend/tests/endpoints/test_streaming.py`, `backend/tests/endpoints/test_states.py`, and `backend/tests/endpoints/test_screenshots.py`.
- Frontend failures follow shared v2 loading, notification, and permission patterns from `.claude/skills/frontend-v2-patterns/SKILL.md`.

## Logging

**Framework:** Structured backend logger and `console.error` for production-visible frontend errors.

**Patterns:**

- Backend tests attach `caplog.handler` directly to the `romm` logger when propagation is disabled, as in `backend/tests/endpoints/test_streaming.py`.
- Do not ship `console.log` or `console.warn`; remove development-only `console.debug` before a PR, per `.claude/skills/frontend-v2-components/SKILL.md`.

## Comments

**When to Comment:**

- Explain security boundaries, concurrency assumptions, compatibility constraints, and non-obvious fixture setup.
- Do not narrate visible control flow or explain a completed change.

**JSDoc/TSDoc:**

- Use concise docstrings for fixtures and helpers whose setup or domain semantics are not obvious, as in `frontend/e2e/fixtures/auth.ts` and `backend/tests/conftest.py`.
- Keep comments and documentation in English.

## Function Design

**Size:** Keep new production files at or below 500 logical lines. Extract a coherent helper before inflating a legacy monolith.

**Parameters:** Prefer typed, explicit parameters. Use pytest fixtures for shared setup and dependency injection.

**Return Values:** Use precise return types and assert observable behavior, security boundaries, or data contracts.

## Module Design

**Exports:** Prefer named exports. v2 composables expose one named `useFoo` export from `composables/useFoo/index.ts`.

**Barrel Files:** Use barrels for v2 primitives through `frontend/src/v2/lib/index.ts`. Import composites directly by path and do not add shortcut-only barrels.

## Quality Gates

- Backend changes require the affected pytest subset or full matrix plus `trunk fmt && trunk check`; see `.github/workflows/pytest.yml` and `.claude/skills/pre-pr-verification/SKILL.md`.
- Frontend changes require `npm run typecheck`, `npm test`, and `npm run build`. Run `npm run generate` before typecheck after API contract changes.
- New or modified v2 primitives require a Storybook story and interaction coverage where applicable. The harness is `frontend/test/storybook.test.ts`.
- Locale changes require `frontend/src/locales/check_i18n_locales.py` and `frontend/src/locales/check_i18n_sorted.py`.
- New migrations require upgrade and downgrade verification on PostgreSQL, MariaDB, and MySQL in `.github/workflows/migrations.yml`.
- New frontend work belongs under `frontend/src/v2/`; `.github/workflows/frontend-v1-frozen.yml` rejects frozen v1 paths without the sanctioned label.

---

_Convention analysis: 2026-10-15_
