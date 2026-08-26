# Phase 8: Bounded V1 Removal - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove the frozen v1 frontend and all v1-only compatibility paths so the fork boots directly into one v2 interface. Preserve the v2 runtime's shared stores, services, generated types, authentication, pairing, theme, router, and overlays. Work is divided into independently compilable deletion waves with focused regression checks. Browser smoke validation remains Phase 9.
</domain>

<decisions>
## Implementation Decisions

### Removal Scope

- **D-01:** Remove v1 in clear, independently compilable waves rather than one large deletion.
- **D-02:** Commit and run focused checks after every deletion wave; fix a regression before starting the next wave.
- **D-03:** Physically delete frozen v1 views, components, layouts, console surfaces, banners, fallbacks, and compatibility code from the repository.
- **D-04:** Before deletion, move every v2-required dependency currently under a v1 path to a neutral canonical shared path.

### Route Inventory

- **D-05:** Maintain an explicit route inventory classifying every legacy route as a real v2 view, a redirect to an equivalent v2 function, or a deliberate removal.
- **D-06:** Redirect any unsupported legacy route to its functional v2 equivalent whenever one exists.
- **D-07:** Map legacy console and special-purpose deep links to the closest functional v2 route.
- **D-08:** Remove `NotReady` entirely. No v1 or placeholder fallback remains after supported routes are covered.

### Preference Cleanup

- **D-09:** Remove the v1 `uiVersion` preference silently, with no migration notice.
- **D-10:** Remove v1 UI-mode fields and behavior from both frontend and backend persistence/contracts.
- **D-11:** Preserve neutral user preferences such as theme, language, and gallery settings.
- **D-12:** Do not retain a hidden configuration flag or developer fallback to v1.

### Regression Scope

- **D-13:** Defer browser smoke testing to Phase 9.
- **D-14:** Add an automated route-inventory test that proves each supported route has a real v2 target or declared redirect and no deleted v1 reference.
- **D-15:** Add a small mocked v2 boot/import suite for auth, pairing, theme, router, shared stores, API services, generated types, and overlays.
- **D-16:** Keep Phase 8 verification targeted: typecheck plus focused route and boot/import tests, not broad live testing.

### the agent's Discretion

- Exact deletion-wave boundaries, route-equivalence mapping, neutral module locations, redirect mechanics, and focused test implementation.
</decisions>

<canonical_refs>

## Canonical References

### Milestone Scope

- `.planning/ROADMAP.md` - Phase 8 goal, requirements V2-01 through V2-05, and success criteria.
- `.planning/REQUIREMENTS.md` - Formal v1 removal acceptance requirements.
- `.planning/PROJECT.md` - v2-only product constraint and immutable archive project boundary.

### Repository Rules and Architecture

- `CLAUDE.md` - v2-only frontend direction, generated contracts, test requirements, and no-v1 rule.
- `.planning/codebase/CONVENTIONS.md` - Frontend naming, generated-code, and test conventions.
- `.planning/codebase/STRUCTURE.md` - Current frontend routing, v1/v2 layout, and shared resource structure.
- `.planning/codebase/TESTING.md` - Focused Vitest, typecheck, and route/runtime regression conventions.

### Carried-Forward Decisions

- `.planning/phases/07-v2-storage-administration-experience/07-CONTEXT.md` - v2 storage route and shared v2 implementation constraints.
- `.planning/phases/06-safe-lifecycle-and-legacy-migration/06-CONTEXT.md` - v2 administration remains the active user interface and preserves source safety.
  </canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `frontend/src/v2/router/routes.ts` and `frontend/src/plugins/router.ts` own the current v1/v2 named-view switch and route registry.
- `frontend/src/v2/layouts/`, `frontend/src/v2/views/`, and `frontend/src/v2/components/` provide the active v2 surface to retain.
- `frontend/e2e/` and co-located v2 Vitest suites provide existing focused test patterns.

### Established Patterns

- The frontend imports generated API types from `frontend/src/__generated__/` and shared services/stores from canonical locations.
- V2 is the active rewrite; v1 directories are frozen and must not receive new behavior.
- Typecheck and focused Vitest suites provide low-cost safety gates; browser E2E is intentionally deferred.

### Integration Points

- Remove `uiVersion` gating from frontend layout, route resolution, user settings, and any backend preference contract.
- Replace v1 named-view/fallback routing with one v2 route registry and deliberate redirects.
- Move v2-required shared dependencies out of paths scheduled for deletion before removing v1 source.
  </code_context>

<specifics>
## Specific Ideas

The v2-only cutover must not leave a placeholder `NotReady` screen, a hidden v1 switch, or an untracked legacy route. Existing user-facing neutral preferences remain intact.
</specifics>

<deferred>
## Deferred Ideas

- Full browser smoke validation for login, pairing, and navigation is deferred to Phase 9 by decision D-13.
</deferred>

---

_Phase: 08-bounded-v1-removal_
_Context gathered: 2026-08-26_
