# Steam Supplemental Metadata and DLC Design

## Goal

Supplement missing PC metadata from Steam without replacing existing IGDB-owned
values, and expose Steam DLC relationships for isolated browser UAT.

## Scope

- Store Steam genres, categories, and features only when the corresponding
  IGDB-derived field is empty.
- Preserve every existing IGDB value and all operator-authored values.
- Resolve Steam DLC identities returned by a parent application into explicit
  PC component relationships, retaining the Steam app ID and localized name.
- Use a new, isolated Cyberpunk 2077 fixture with the Phantom Liberty DLC for
  browser UAT. The fixture must not access a NAS or a real game library.

## Data Flow

1. Steam app-details returns localized genres, categories, feature categories,
   and DLC app IDs for an eligible PC parent game.
2. The Steam adapter normalizes non-empty localized values and retains provider
   identity for each DLC.
3. The merge layer fills only empty IGDB-derived metadata fields. Existing
   IGDB and manual values remain authoritative.
4. The PC component path persists DLC records after a durable parent identity.
   Provider errors and incomplete DLC details are non-destructive no-ops.
5. The first imported Steam artwork becomes the visible game cover when an
   operator has not selected a cover. All imported Steam screenshots appear in
   the game's overview gallery by default. The existing Media UI remains the
   place to remove, suppress, select, or reorder candidates.
6. Operator-selected cover and gallery choices remain authoritative and are
   never replaced or reordered by a later Steam scan.

## Tags

Steam's normal app-details response does not provide stable public tags.
Tags are explicitly excluded from this change. They require a separate
provider endpoint and a dedicated provenance contract.

## Verification

- Unit tests cover empty-field enrichment, IGDB/manual preservation, malformed
  Steam data, and DLC provider failure isolation.
- Isolated UAT scans Cyberpunk 2077 as a new PC game, verifies German Steam
  metadata, visible cover, overview gallery, and Phantom Liberty as a related
  DLC, then verifies UPDATE and COMPLETE preserve manual and IGDB values.
- The source fixture manifest is identical before and after all scans.
