# Phase 10 Validation Strategy

| Layer       | Proof                                                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Unit        | Component grammar, manifest digesting, ambiguity, and provider candidate normalization.                                        |
| Integration | Read-only fixture scan, persistence, candidate search/apply transaction, and local LaunchBox media selection.                  |
| Frontend    | Vitest covers candidate selection, disabled apply state, unresolved component display, and provider errors.                    |
| E2E         | A test fixture scans a PC folder, opens the game, reviews candidates, applies one, and confirms source data remains unchanged. |

Mandatory gate: run the source-tree sentinel before and after the complete PC fixture
flow. A differing relative-path/size/digest tree fails the phase.
