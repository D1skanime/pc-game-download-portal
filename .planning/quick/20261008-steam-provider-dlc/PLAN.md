---
name: steam-provider-dlc
status: in_progress
---

# Steam provider display and DLC matching

## Scope

Fix the v2 PC metadata candidate UI so Steam candidates retain a Steam-specific cover field and provider badge. Preserve the existing conservative DLC contract: IGDB establishes the component relationship, Steam enriches validated DLC metadata, and missing Steam catalog entries never become false matches.

## Tasks

1. Add a typed Steam cover field to the match-dialog adapter and render it through the existing provider-source helpers.
2. Add a focused frontend regression test proving a Steam candidate is not reported as IGDB.
3. Verify the existing backend DLC paths and document the Steam/IGDB responsibility boundary.
4. Run focused frontend checks, restart the Linux dev service, and verify the live dialog with Steam selected.

## Guardrails

- Work only in the verified Linux checkout.
- Do not require users to know Steam App IDs.
- Do not auto-match a folder name to an arbitrary Steam product.
- Reject soundtracks, bundles, demos, and unrelated products.
