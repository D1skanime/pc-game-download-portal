# Phase 29 Validation Architecture

## Automated

- Overview component tests cover role labels, one PC release field, theme/genre navigation, stable query parameters, and locale-aware display.
- Locale parity: python3 frontend/src/locales/check_i18n_locales.py
- Locale sorted keys: python3 frontend/src/locales/check_i18n_sorted.py
- Focused Vitest component tests.
- npm run typecheck
- npm run build

## Sampling

- Wave 1: focused component tests after display-model changes.
- Wave 2: locale parity/sorted scripts plus typecheck.
- Wave 3: browser UAT on German, English, and French.

## Manual

- Confirm theme and genre chips are keyboard-accessible.
- Confirm clicking a theme filters PC games without using translated labels as identity.
- Confirm PC release appears once and changes formatting with locale.
- Confirm publisher/developer/participating-company wording is not misleading for Witcher 3.

## Out of scope

- No external package installation.
