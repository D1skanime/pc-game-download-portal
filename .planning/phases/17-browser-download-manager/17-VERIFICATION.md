---
phase: 17-browser-download-manager
verified: 2026-09-24
status: complete
browser_matrix: chromium_passed_firefox_edge_waived
---

# Phase 17 Verification Report

## Result

Phase 17 is accepted for its browser-only product scope. The installed desktop
client is not a prerequisite or delivery path. Chromium completed the required
live isolated UAT cases. Firefox and Edge were explicitly waived by the product
owner and are documented as waivers, not as compatibility passes.

## Verified user outcomes

| Outcome                                                        | Result                                                                                                                          |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Select main game, updates, DLCs, extras, or permitted files    | PASS: component and member selection produces immutable manifests.                                                              |
| Download original files without desktop software or server ZIP | PASS: Standard attachment handoff and Enhanced direct streaming were observed.                                                  |
| Transfer a large original file                                 | PASS: 5 GiB ISO transferred and verified by SHA-256.                                                                            |
| Control multi-file transfers                                   | PASS: 40-member Enhanced queue completed with configured bounded concurrency.                                                   |
| Resume safely                                                  | PASS: Range plus validator resume completed; changed source failed closed with `412`.                                           |
| Show truthful status and history                               | PASS: Standard uses server `served`, Enhanced uses local checksum `verified`; cancellation, retry and removal were live-tested. |
| Keep source roots unchanged                                    | PASS: isolated source was read-only, direct streaming was used, and no ZIP or staging workflow was observed.                    |

## Remaining non-product limitation

The standalone host pytest fixture cannot reach its configured test database at
`127.0.0.1:3306`. This is an environment limitation, not an unresolved live
product failure: the isolated UAT stack used MariaDB successfully for all
observed flows.

## Evidence

- `17-DOWNLOAD-EVIDENCE.md`
- `17-BROWSER-MATRIX.md`
- live Chromium UI and native directory-picker runs on the isolated `3344`
  stack
