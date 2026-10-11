# Phase 23 Source Coverage Audit

## Sources examined

| Source       | Item                                                                                                             | Coverage                                                                                                            |
| ------------ | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Goal         | Persist German, English, and further configured Steam text variants per app and display the UI-language variant. | 23-01 acquires normalized variants, 23-02 persists them for parents and components, 23-03 exposes and renders them. |
| Requirement  | STEAM-02, stable localized structured Steam metadata without overwriting manual or IGDB-owned values.            | 23-01 and 23-02.                                                                                                    |
| Requirement  | STEAM-04, Steam provenance is exposed consistently through API and v2.                                           | 23-03.                                                                                                              |
| Requirement  | STEAM-05, malformed, regional, timeout, and rate-limit responses remain non-fatal.                               | 23-01 and 23-02.                                                                                                    |
| Research     | Bounded server-side configured language list, current primary language plus English by default.                  | 23-01.                                                                                                              |
| Research     | Additive `steam_metadata.text_variants`, canonical base tags, and no provider/browser fetch on locale switch.    | 23-01 and 23-02.                                                                                                    |
| Research     | English fallback after UI base-language selection, then legacy summary only when variants are absent.            | 23-03.                                                                                                              |
| Research     | Preserve manual and non-Steam/provider-owned display text.                                                       | 23-02 and 23-03.                                                                                                    |
| Research     | Detail-only payload and isolated Docker UAT with no NAS, Team4s, or real library.                                | 23-03.                                                                                                              |
| Context D-01 | Missing selected language uses English Steam description.                                                        | 23-03 Task 2.                                                                                                       |
| Context D-02 | Store multiple available Steam language variants rather than overwrite one summary.                              | 23-01 and 23-02.                                                                                                    |
| Context idea | Keep language provenance such as `de` and `en` per variant.                                                      | 23-01 and 23-02.                                                                                                    |

## Intentional boundaries

- Steam's existing JSON columns already hold provider-owned metadata on `Rom` and `RomComponentMetadata`; adding the backwards-compatible `text_variants` JSON member requires no SQL DDL or data rewrite. Existing records continue to use their legacy summary until a later Steam enrichment refresh adds variants.
- This phase does not translate IGDB, manual, or other provider text; change artwork, DLC matching, Phase 22 queue behavior; or fetch Steam when a browser language changes.
