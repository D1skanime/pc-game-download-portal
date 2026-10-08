# Quick Plan: Context-aware PC component matching

## Goal

Make PC metadata matching honor the target context already carried by the UI. Main-game matching remains broad, while matching from a PC component (DLC/Expansion) only returns related component candidates and rejects ordinary games.

## Scope

- Preserve the existing `PcMatchTarget` and endpoint split.
- Use the persisted component kind and parent ROM as the backend source of truth.
- For DLC components, keep IGDB candidates limited to the parent relationships and keep Steam candidates limited to Steam DLC entries belonging to the parent game.
- Treat Steam `type=dlc` as the provider transport type for both RomM DLC and RomM Expansion concepts; do not change RomM's component classification.
- Keep main-game and base-component matching behavior unchanged.
- Add focused handler tests for accepted and rejected component candidates.

## Verification

- A normal main-game search still returns normal game candidates.
- A DLC/Expansion component search rejects Steam games, soundtracks, unrelated apps, and DLCs belonging to another parent.
- Related IGDB expansion/DLC candidates remain available.
- Existing frontend typecheck and focused tests pass.
