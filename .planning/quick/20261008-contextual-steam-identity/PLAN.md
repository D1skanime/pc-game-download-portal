# Quick Plan: Contextual Steam identity resolution for PC components

## Goal

Resolve Steam metadata from a DLC/Expansion context through the trusted IGDB relationship first, so components such as Witcher 3 New Quest can use their Steam app ID even when Steam search and the parent `dlc` list omit the entry.

## Changes

1. Extend IGDB related-game metadata to retain a Steam external-game ID when IGDB exposes one.
2. In DLC component matching, hydrate those related Steam IDs directly through Steam `appdetails`, then apply the existing `type=dlc` and parent-game validation.
3. Keep the generic Steam search as a fallback only when no trusted related Steam ID exists.
4. Use an existing component metadata name as the initial UI query instead of falling back to `parent + DLC` when the installer filename is generic.
5. Add focused tests for external Steam ID extraction, direct hydration, and the component search label.

## Safety

- Main-game matching remains unchanged.
- RomM's DLC/Expansion classification remains authoritative; Steam's `dlc` is only the provider type.
- No Steam IDs are hardcoded.
- Existing storage, media, and metadata persistence paths remain unchanged.

## Verification

- Focused backend and frontend tests pass.
- Dev service restarts successfully.
- Live New Quest component opens with its actual title and can resolve the trusted Steam ID when present in refreshed IGDB metadata.
