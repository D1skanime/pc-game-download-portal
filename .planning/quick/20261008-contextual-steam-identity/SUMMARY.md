# Quick Summary: Contextual Steam identity resolution for PC components

## Result

Implemented contextual Steam resolution for PC DLC components. Related IGDB
expansions and DLCs now retain a Steam external-game ID when IGDB provides one.
The matcher hydrates that Steam app directly through `appdetails` and keeps
the existing DLC type and parent-game validation. Generic Steam search remains
the fallback when no trusted relationship is available.

The PC component matcher also prefers the component metadata name for its
initial search label, so a generic installer folder no longer produces a
misleading parent-game query.

## Verification

- Linux preflight passed for `/home/d1sk/romm` on branch
  `codex/pc-module-analysis`.
- Python AST syntax check passed.
- Focused backend tests passed: `2 passed, 39 deselected`.
- Direct Steam hydration smoke test passed with a synthetic DLC relation.
- Frontend focused test execution was unavailable because Node is not
  installed on the Linux host; no frontend test failure was observed.

## Safety
