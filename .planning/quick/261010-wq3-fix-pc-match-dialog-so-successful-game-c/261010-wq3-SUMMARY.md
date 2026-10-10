---
status: complete
commit: d76af10e2
---

# Close PC MatchRomDialog after successful assignment

Separated PC assignment success from the post-assignment refresh so the v2 MatchRomDialog closes immediately after parent-game or component metadata assignment resolves, while refresh failures remain non-blocking.

Changes:

- PC parent-game and component assignment API calls remain behind their existing target guards and payload/version/media selection logic.
- Assignment success now clears loading state, shows the existing success snackbar, and closes the dialog before awaiting the optional refresh callback.
- Refresh rejection is isolated from assignment failure handling and logged through the existing console error mechanism.
- Assignment rejection still keeps the dialog open and uses the existing update-failure snackbar path.
- Added focused regression coverage for close-before-refresh ordering and refresh error isolation while retaining endpoint guards.
- No backend, API contract, locale, generated type, deployment, or unrelated dirty-work changes were made.

Verification:

- Focused Vitest: npm run test -- --run src/v2/components/Dialogs/MatchRomDialog.test.ts, 4 passed.
- Frontend typecheck: npm run typecheck, passed.
- git diff --check HEAD~2 HEAD, passed.
- No deployment performed.

Deviations from the planning artifact:

- The supplied plan was marked planning-only and said not to implement or commit. The user explicitly authorized execution, implementation, regression coverage, and an atomic commit, so the plan was executed as an implementation quick task.
- The remote non-interactive shell did not expose npm by default. Verification used the installed Node v24.19.0 runtime at /home/d1sk/.nvm/versions/node/v24.19.0/bin without changing project configuration.
- The remote host lacks apply_patch; guarded exact-text edits were applied through stdin and verified by focused tests and diff inspection.

Commits:

- 1ceeb049a fix(261010-wq3): close PC match dialog before refresh
- d76af10e2 test(261010-wq3): cover PC match close timing

No user setup required.
