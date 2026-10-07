# Quick Task Plan

**Goal:** Make Steam visible in the setup wizard with correct localized copy and the same global enablement and heartbeat semantics already used by Settings and scanning.

**Scope:** Keep this change limited to the existing setup metadata list, setup locale resources, and focused frontend tests. Steam is flag-only: it does not require an API key, it is globally activated by `STEAM_API_ENABLED`, and its runtime status comes from the existing metadata heartbeat. Do not add a new toggle, config store, provider abstraction, or parallel Steam configuration path.

1. **Add focused regression coverage before implementation.** Create `frontend/src/v2/components/Auth/SetupStepMetadata.test.ts` using the existing heartbeat-store mock/stub style. Cover that enabled Steam is rendered separately from SteamGridDB, that the component probes the existing heartbeat with the provider value `steam`, that `STEAM_API_ENABLED=false` renders Steam as disabled without probing it, and that enabled heartbeat results map to the flag-only status vocabulary (available, checking, unreachable rather than API-key-missing/invalid). Extend `frontend/src/stores/heartbeat.test.ts` only where needed to keep explicit provider parity coverage for Steam versus SteamGridDB. Assert the setup copy keys used for Steam are present in both `frontend/src/locales/en_US/setup.json` and `frontend/src/locales/de_DE/setup.json`; if the test imports locale JSON, keep assertions focused on the exact Steam description and setup instruction. Run the focused Vitest files and confirm the new behavior is initially red before production changes.

2. **Expose Steam in the setup wizard by reusing the existing provider contract.** Modify only `frontend/src/v2/components/Auth/SetupStepMetadata.vue` to add a `Steam` catalog entry with the existing Steam asset, provider key `steam`, `requiresKey: false`, and `disabled: !m.STEAM_API_ENABLED`. Keep `probeAll()` on `heartbeat.fetchMetadataHeartbeat(source.key)` so the setup view uses the same `/heartbeat/metadata/steam` path as Settings and scanning. Preserve the current flag-only status behavior: disabled means provider disabled, a successful probe means available, and a failed probe means unreachable. The Steam setup copy must explicitly say that no API key is needed and that activation is global through `STEAM_API_ENABLED`; do not add a setup-local toggle or config mutation. Run the focused setup and heartbeat tests plus `cd frontend && npm run typecheck`.

3. **Add localized Steam setup copy and validate locale/provider parity.** Add the Steam description and setup-instruction keys to the setup locale resources, with authoritative English in `frontend/src/locales/en_US/setup.json` and German in `frontend/src/locales/de_DE/setup.json`. Propagate the same keys to every other existing `setup.json` locale file so the repository's enforced locale-key parity remains valid, using the established provider terminology and preserving alphabetical key ordering. Do not alter unrelated metadata text. Run `python3 frontend/src/locales/check_i18n_locales.py`, `python3 frontend/src/locales/check_i18n_sorted.py`, the focused Vitest coverage, and `cd frontend && npm run typecheck`.

**Files expected to change:**

- `frontend/src/v2/components/Auth/SetupStepMetadata.vue`
- `frontend/src/v2/components/Auth/SetupStepMetadata.test.ts`
- `frontend/src/stores/heartbeat.test.ts` (only if parity coverage needs a targeted update)
- `frontend/src/locales/*/setup.json` for the two new Steam keys

**Acceptance criteria:**

- Steam appears in the setup wizard independently of SteamGridDB.
- Steam is marked enabled/disabled from `heartbeat.METADATA_SOURCES.STEAM_API_ENABLED`.
- Enabled Steam is probed through the existing `fetchMetadataHeartbeat("steam")` path and shows available or unreachable based on that result.
- Setup copy in English and German clearly states that Steam needs no API key and is enabled globally with `STEAM_API_ENABLED`.
- Locale parity, locale sorting, focused tests, and frontend typechecking pass.
