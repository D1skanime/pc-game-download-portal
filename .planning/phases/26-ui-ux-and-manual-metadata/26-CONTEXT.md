---
phase: 26
name: ui-ux-and-manual-metadata
status: planned
created: 2026-10-09
---

# Phase 26 Context

## Goal

Close the remaining UI/UX gaps discovered during Linux Dev UAT and add
user-friendly, language-scoped manual metadata editing without creating a
second metadata or provider architecture.

## Decisions

- Reuse the existing ROM, DLC, expansion, metadata ownership, permission,
  language, and provider abstractions.
- A manual description override is stored per ROM-like entity and locale.
- For the same locale, manual content wins over provider content.
- Provider scans may refresh provider data, but must not overwrite manual text.
- Clearing a manual override restores the normal provider/fallback chain.
- Parent-game, DLC, and expansion detail surfaces use the same contract.
- Existing animation-default, sharp-background, and soundtrack-role fixes are
  regression scope only; they are not reimplemented.
- UI feedback from live UAT is collected in this phase: detail tabs should read
  Overview, Game Download or Patcher, Media, then Files.
- The PC Game Download local-image action must be named for what it does, such
  as "Use local images", because it selects images from downloaded DLC/Extra
  components and does not perform an online cover search.
- Cover search must be directly discoverable, have an accessible label, and
  explain when SteamGridDB is disabled; users must not need to know provider IDs.
- Crawled provider values such as release date and genres must remain visible
  even when no manual override exists. Manual fields must make provenance and
  override behavior explicit instead of appearing silently empty.
- A manually entered YouTube video ID must be validated and either rendered in
  the existing Overview media surface or clearly reported as unsupported; it
  must never be silently stored without visible effect.
- User-facing filesystem paths must resolve through the active StorageRoot and
  PlatformStorageMapping instead of displaying the legacy `/romm/library` prefix.
- PC header download must open the same Game Download selection screen as the
  Game Download tab; direct link-copy actions are not useful for PC packages.
- DLC and expansion detail routes use the same scoped composition as the
  parent game: Overview, Game Download, Media, then Files. Their media
  overview placement and deletes target only the selected component; the background remains inherited from the parent game.
- DLC-Übersichtsmedien sind anklickbar und öffnen dieselbe vorhandene Galerie- bzw.
  Viewer-Interaktion wie beim Hauptspiel; die Aktion bleibt auf die Komponente begrenzt.
- DLC- und Expansion-Daten können über ein komponentenbezogenes „…“-Menü
  wie beim Hauptspiel geöffnet, bearbeitet und gespeichert werden, ohne den
  Parent-Datensatz zu verändern.
- DLC- und Expansion-Cover verwenden denselben Cover-Suchdialog wie das
  Hauptspiel; Suche, Auswahl und Speichern bleiben auf die Komponente begrenzt.

## Out of scope

- New storage, mapping, scanning, or metadata-provider architectures.
- Changing the established parent-game scan flow.
- Separating artwork by language unless an existing provider contract requires it.

## Quality gates

- No duplicate domain model or API for metadata ownership.
- Full locale parity for every new user-facing string.
- New or changed source files remain focused and below the repository size rule.
- Linux verification plus browser UAT evidence are required before completion.
