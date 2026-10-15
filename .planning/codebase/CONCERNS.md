# Codebase Concerns

**Analysis Date:** 2026-10-15

## Tech Debt

**Monolithic backend hotspots:**

- Issue: Production modules exceed the repository's 500-line decomposition rule: `backend/handler/database/roms_handler.py` is 4696 lines, `backend/adapters/services/igdb.py` 4584, `backend/endpoints/roms/__init__.py` 2264, and `backend/handler/filesystem/roms_handler.py` 1331.
- Files: `backend/handler/database/roms_handler.py`, `backend/adapters/services/igdb.py`, `backend/endpoints/roms/__init__.py`, `backend/handler/filesystem/roms_handler.py`, `CLAUDE.md`
- Impact: Storage, metadata, downloads, and scans share a large regression surface and are difficult to audit for read-only boundary preservation.
- Fix approach: Extract bounded provider, query-projection, download-response, and scanner-policy modules one boundary at a time, with focused tests.

**Runtime and deployment configuration has no parity contract:**

- Issue: Settings are duplicated across `backend/config/__init__.py`, `env.template`, `examples/portainer-stack.yml`, `examples/portainer.env.example`, and operator docs.
- Files: `backend/config/__init__.py`, `env.template`, `examples/portainer-stack.yml`, `examples/portainer.env.example`, `scripts/verify-portainer-stack.sh`
- Impact: A setting may exist in runtime code but be impossible to configure through the documented deployment.
- Fix approach: Maintain a checked matrix of runtime-only, stack-exposed, secret, and unsupported settings, and enforce it in the Portainer validator.

## Known Bugs

**Development Compose uses the retired checkout and a writable library:**

- Symptoms: `docker-compose.yml:27-29` mounts `/home/d1sk/romm/Games` and `/home/d1sk/romm/Docker/Media`, while `CLAUDE.md` identifies `/home/d1sk/pc-game-download-portal` as canonical. The parent `/app/romm/library` mount is writable and only the PC overlay is read-only.
- Files: `docker-compose.yml`, `CLAUDE.md`, `.planning/PROJECT.md`
- Impact: Development tests can inspect an empty or unrelated archive and violate the archive-safety assumption.
- Fix approach: Parameterize host paths or use task-owned fixtures, and mount the entire external library `:ro`.

**GSD project state contains obsolete operational assumptions:**

- Symptoms: `.planning/PROJECT.md:72` still calls `/home/d1sk/romm` canonical and says v1 remains a compatibility surface. The repository guide names `/home/d1sk/pc-game-download-portal` and treats v1 as frozen legacy.
- Files: `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/v1.0-v1.0-MILESTONE-AUDIT.md`, `.planning/research/STACK.md`, `CLAUDE.md`
- Impact: GSD plans and validation can run against the backup checkout or target the wrong frontend surface.
- Fix approach: Refresh planning/research artifacts, remove stale `/home/d1sk/romm` commands, and assert the canonical path before GSD writes.

**Portainer provider integrations are only partially wired:**

- Symptoms: `examples/portainer-stack.yml:40-48` forwards only ScreenScraper, RetroAchievements, SteamGridDB, IGDB, and Hasheous. Runtime code also supports MobyGames, Steam language settings, LaunchBox, Playmatch, TheGamesDB, Flashpoint, HowLongToBeat, OIDC, Sentry, and proxy settings.
- Files: `examples/portainer-stack.yml`, `examples/portainer.env.example`, `backend/config/__init__.py:105-208`, `backend/config/__init__.py:250-273`, `env.template`
- Impact: Adding an unforwarded variable in Portainer has no effect because Compose does not pass arbitrary stack variables into the container.
- Fix approach: Forward supported settings such as `MOBYGAMES_API_KEY`, `STEAM_API_*`, `LAUNCHBOX_API_ENABLED`, `PLAYMATCH_API_ENABLED`, `PLAYMATCH_API_URL`, `TGDB_API_ENABLED`, `FLASHPOINT_API_ENABLED`, and `HLTB_API_ENABLED`, then assert them in rendered Compose.

**Portainer database image is mutable:**

- Symptoms: `examples/portainer-stack.yml:81` uses `mariadb:11.3` while `docker/Dockerfile` pins build inputs with digests.
- Impact: A redeploy can pull a different database image during a catalog migration.
- Fix approach: Pin the exact MariaDB digest and make `scripts/verify-portainer-stack.sh` reject mutable production image references.

## Security Considerations

**HowLongToBeat trusts mutable GitHub branch content:**

- Risk: `backend/handler/metadata/hltb_handler.py:169` reads from `raw.githubusercontent.com/rommapp/romm/refs/heads/master`, then uses the returned text as the search endpoint at lines 199-209.
- Files: `backend/handler/metadata/hltb_handler.py`
- Current mitigation: Shared HTTP client and ten-second timeout.
- Recommendations: Pin a reviewed commit, allowlist scheme and host, and cache a known-good endpoint.

**Build-time provider secrets persist in the final image:**

- Risk: `examples/portainer-stack.yml:17-25` passes ScreenScraper developer credentials as build args; `docker/Dockerfile:228-233` promotes them to final-image `ENV` values.
- Files: `examples/portainer-stack.yml`, `docker/Dockerfile`, `docs/PORTAINER_INSTALL.md:209-218`
- Current mitigation: Documentation prohibits committing the values.
- Recommendations: Use BuildKit secret mounts or runtime-only injection and inspect image config/layers in CI.

## Performance Bottlenecks

**Provider and ROM database handlers are monolithic:**

- Problem: The 4696-line ROM handler and 4584-line IGDB adapter mix query, provider, automation, and scan paths.
- Files: `backend/handler/database/roms_handler.py`, `backend/adapters/services/igdb.py`, `backend/endpoints/sockets/scan.py`
- Improvement path: Measure query/provider latency and extract bounded services with explicit timeout and cancellation behavior.

**HLTB initialization performs blocking network discovery:**

- Problem: `HLTBHandler.initialize()` synchronously fetches a mutable endpoint and security token.
- Files: `backend/handler/metadata/hltb_handler.py:192-237`, `backend/startup.py`
- Improvement path: Use cached token state with expiry and make provider readiness refreshable without blocking startup.

## Fragile Areas

**Container health does not cover background services:**

- Files: `docker/init_scripts/init`, `docker/init_scripts/docker-entrypoint.sh`, `examples/portainer-stack.yml:67-77`
- Why fragile: Valkey, migrations, Gunicorn, RQ, watchers, and frontend/static services are shell-orchestrated, but the healthcheck only probes `/api/heartbeat`.
- Safe modification: Preserve PID/signal handling and add readiness diagnostics for worker, queue, and persistence dependencies.
- Test coverage: `scripts/verify-portainer-stack.sh` validates YAML shape only, not the production runtime.

**Generated API types and localized descriptions can drift:**

- Files: `backend/endpoints/responses/rom.py`, `frontend/src/__generated__/models/SSDescriptionVariant.ts`, `frontend/src/v2/composables/useManualDescription/index.ts`, `frontend/src/v2/views/GameDetails.vue`, `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`
- Why fragile: `npm run generate` is manual and parent/component views maintain separate provider-resolution inputs and precedence paths.
- Safe modification: Regenerate after backend schema changes, typecheck, and document one parent/component resolution contract.
- Test coverage: Resolver unit tests exist, but no end-to-end contract test covers generated schema plus parent and component payloads.

**File-serving policy is split across HTTP and infrastructure:**

- Files: `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/handler/filesystem/base_handler.py`, `backend/utils/nginx.py`
- Why fragile: Authorization, containment, database identity, and nginx `X-Accel-Redirect` behavior are separate contracts.
- Safe modification: Centralize policy-aware responses and test the production nginx path for symlinks, mutation races, encoded separators, and ranges.
- Test coverage: Application tests do not prove nginx opening the authorized target after filesystem mutation.

## Scaling Limits

**Large modules have no enforced ownership ceiling:**

- Current capacity: `backend/handler/database/roms_handler.py` is 4696 lines and `backend/adapters/services/igdb.py` is 4584 lines.
- Limit: Each new query or provider branch increases regression surface without an automated size gate.
- Scaling path: Enforce the 500-line target for new files and require explicit exceptions for legacy modules.

**Development source mounts are not portable:**

- Current capacity: `docker-compose.yml` assumes `/home/d1sk/romm` and writable source content.
- Limit: Missing paths yield empty tests; writable mounts contradict production archive safety.
- Scaling path: Parameterize host paths, default source content to read-only, and use isolated fixtures.

## Dependencies at Risk

**HowLongToBeat uses an undocumented upstream contract:**

- Risk: Search depends on a mutable GitHub file and reverse-engineered token flow from `howlongtobeat.com`.
- Impact: Upstream changes can disable metadata without a repository release.
- Migration plan: Version the provider contract, add recorded compatibility tests, and make fallback explicit.

**Production deployment uses mutable image tags:**

- Risk: `mariadb:11.3` is not immutable.
- Impact: Database behavior can change independently of application review.
- Migration plan: Pin a digest and verify it in CI.

## Missing Critical Features

**Deployment integration parity check:**

- Problem: No automated inventory compares `backend/config/__init__.py`, `env.template`, Portainer YAML, and operator documentation.
- Blocks: Reliable configuration of supported metadata, authentication, observability, and proxy integrations.

**Production readiness health contract:**

- Problem: `GET /api/heartbeat` does not expose worker, queue, Valkey, watcher, or scheduled-job readiness.
- Blocks: Operators cannot distinguish a usable service from a partially degraded deployment through container health.

## Test Coverage Gaps

**Portainer runtime integration:**

- What's not tested: Clean stack deployment, MariaDB migration, internal Valkey, RQ worker, read-only library access, and provider configuration.
- Files: `examples/portainer-stack.yml`, `examples/portainer.env.example`, `scripts/verify-portainer-stack.sh`, `docker/init_scripts/init`
- Risk: Static validation can pass while runtime integrations are missing or unhealthy.
- Priority: High

**Configuration parity:**

- What's not tested: Every provider and auth variable in `env.template` is intentionally exposed or excluded in Portainer.
- Files: `env.template`, `backend/config/__init__.py`, `examples/portainer-stack.yml`, `docs/PORTAINER_INSTALL.md`
- Risk: Operators cannot enable integrations that appear supported.
- Priority: High

**Canonical-path and mount safety:**

- What's not tested: Validation rejects `/home/d1sk/romm` in executable Compose/planning commands and confirms the complete library mount is read-only.
- Files: `docker-compose.yml`, `.planning/PROJECT.md`, `scripts/verify-portainer-stack.sh`, `CLAUDE.md`
- Risk: GSD phases can inspect the wrong checkout and invalidate evidence.
- Priority: High

**Mutable provider and localized-description behavior:**

- What's not tested: HLTB malformed endpoint/token expiry/recovery, and identical locale precedence across parent and PC component views.
- Files: `backend/handler/metadata/hltb_handler.py`, `backend/tests/handler/metadata`, `backend/endpoints/roms/pc_metadata.py`, `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`
- Risk: Provider changes can disable operations, and component views can silently lose localized fallback behavior.
- Priority: Medium

---

_Concerns audit: 2026-10-15_
