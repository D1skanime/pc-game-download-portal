# Phase 33 validation gates

All commands run in /home/d1sk/pc-game-download-portal. The gate is fail-closed:
the generated Compose JSON must contain exactly one read-only /fixture/Games bind
at /app/romm/library, retained browser evidence must be PASS, manifests must
match, and cleanup must remove the generated root, project, containers, and
volumes. Dirty compose files and backend/pgdp_test/ are never staged.

    PHASE_DIR=.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc
    bash -n "$PHASE_DIR/33-uat.sh"
    bash "$PHASE_DIR/33-uat.sh"
    python3 "$PHASE_DIR/33-evidence-validate.py" --state "$PHASE_DIR/state.json" --assert-cleanup

The browser command is recorded in state.json and exercises direct discovery,
known and unknown assignment, finish with ready=true, reload persistence,
Home/Scan readiness, terminology/path guards, and evidence capture.


## Resumed validation status

Use backend/tools/phase33_uat.py through the shell wrapper. It delegates target
authority, source snapshots, process startup, cleanup, and command recording to
the existing guarded Phase 34 runner. It preserves the original failure code,
writes state before teardown, and validates exact effective source mounts.
RUN_BROWSER=0 cannot manufacture passing browser evidence.

The latest stable frontend gate before plan 33-10 passed typecheck, 1,093 tests,
and build. Focused Phase 33 MariaDB tests passed 21; the subsequent shared
PC-alias regression suite passed 18. See 33-ACCEPTANCE-RECEIPTS.json. Reuse of an
unchanged frontend receipt requires an exact complete frontend source manifest
match; focused backend receipt reuse requires retained passing pytest XML.

Final acceptance remains pending plan 33-10 and the browser rerun. Host-side
synthetic additions for normal and scheduled discovery have explicit named
barriers. Each immutable application segment must match its own baseline, and
the validator permits only the two named new fixture files per addition.
Both exact Games binds must be read-only and reference the identical source.

## Final command-backed gates

The final f4dd7651 disposable invocation exited zero. The strict validator ran
before and after cleanup, with exact effective Compose and authoritative Docker
read-only bind checks. Browser status is PASS with all 22 named checks true.
The actual scan counts are 3/3, 1/1, 4/4 and 6/6 for initial, selected child,
normal complete and registered scheduled execution respectively.

Frontend receipt reuse is accepted only after exact complete frontend manifest
equality, all recorded command exits zero, 1,102 passing tests, build/typecheck,
and verified cleanup. Final production source equality is retained separately
in current-production-proof.json. No fake browser success or skipped required
gate is accepted. The optional physical gamepad remains BLOCKED with the actual
availability command and reason; human UAT remains pending.

The host synthetic controller adds only the two closed fixture names after
checking each immutable source baseline. The validator requires their exact
additions and rejects changes to existing Games files. Direct API POSTs use the
real browser CSRF cookie header; ROM file assertions use the protected detailed
ROM endpoint because gallery lists intentionally omit file entries by default.

Eight adversarial runner tests and scoped Trunk passed. See the receipt index
for the retained frontend, backend, schema, source, cleanup, live activation and
browser evidence. Historical schema runs are not presented as exact final
model coverage when their model/migration hashes differ.

Fresh final schema validation passed on MariaDB, MySQL and PostgreSQL, with
39/39/40 successful recorded commands, head-to-0138-to-head cycles, parity,
existing constraint/CRUD/locking checks and clean teardown. All three code
manifests equal the final browser and retained-identity regression snapshot.
See evidence/schema-final-source-parity.json and the hashed receipt index.
