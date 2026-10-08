# Quick Plan: Controlled Steam Catalog Fallback

## Goal

Add a narrow fallback to the official Steam Store search endpoint so searches can still produce candidate app IDs when Steam's `/api/storesearch` endpoint returns no usable items, without weakening existing DLC identity validation.

## Constraints

- Implement only in the canonical Linux checkout `/home/d1sk/romm`.
- Keep `/api/storesearch` as the primary source.
- Parse only Steam's JSON search response and its `results_html` payload.
- Keep existing `get_app_details` validation: supported type (`game`/`dlc`), matching app ID, and parent-game validation for DLC matching.
- Do not hardcode DLC IDs, infer DLCs from folder names, or accept soundtracks/bundles/tools.
- Preserve unrelated worktree changes.

## Changes

1. Add a small parser and fallback request in `backend/adapters/services/steam.py`.
2. Return normalized `SteamStoreSearchItem` candidates only for numeric IDs and non-empty titles.
3. Use the fallback only when the primary API has no valid candidates, with de-duplication.
4. Add focused unit coverage for parser behavior and primary-source precedence.
5. Run syntax/type checks, restart `romm-dev`, and perform a live Steam search sanity check.

## Verification

- Parser ignores malformed IDs and empty titles.
- Existing API results prevent an unnecessary fallback request.
- Candidate hydration and existing DLC parent/type checks remain unchanged.
- A missing official catalog relationship remains a safe no-match, not a fabricated match.
