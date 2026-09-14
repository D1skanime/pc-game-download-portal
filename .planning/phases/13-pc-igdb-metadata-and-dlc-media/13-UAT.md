---
status: testing
phase: 13-pc-igdb-metadata-and-dlc-media
source: 13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-PLAN.md
started: 2026-09-04T21:30:09Z
updated: 2026-09-14T15:25:00Z
---

## Current Test

number: gap-closure
name: DLC-UX-Nachtest
expected: |
Die vier dokumentierten DLC-UX-Lücken sind in der laufenden UAT-Instanz behoben.
awaiting: user response for gap closure retest

## Tests

### 1. Parent-IGDB-Metadaten nach Windows-Scan

expected: Scanne einen Windows-Haupttitel mit einer eindeutigen IGDB-Zuordnung. Auf seiner Detailseite zeigt die Übersicht den PC-Veröffentlichungstermin, den Hauptentwickler, Publisher und Themen. Cover und Screenshots sind in RomM gespeichert und sichtbar.
result: pass

### 2. Eindeutig verknüpfter DLC besitzt eigene Metadaten und Medien

expected: Öffne danach den eindeutig verknüpften DLC. Seine Detailseite und sein Medien-Tab zeigen nur seine eigenen Metadaten, Cover und Screenshots, ohne Medien des Haupttitels.
result: pass
evidence: A Woman's Lot imports its own cover, artwork, and six IGDB screenshots. The live DLC page renders all six screenshot images and its May 28, 2019 PC release date.

### 3. Mehrdeutiger oder ungelöster DLC bleibt unverändert

expected: Ein mehrdeutiger oder ungelöster DLC bleibt ohne neu übernommene Metadaten und Medien unverändert.
result: pass
evidence: The user confirmed that Cyberpunk 2077 component `redmod` appears only under `Klassifizierung erforderlich`, with no details or metadata-search action and no metadata or media.

### 4. Eigentumsgrenzen bleiben intakt

expected: Haupttitel- und DLC-Medien vermischen sich nicht. Der externe Quellbaum bleibt durch den Scan unverändert, nur RomM-eigene Medien werden ergänzt.
result: pass
evidence: The user confirmed that parent and DLC media are separated.
issue: DLC media cannot open images in a fullscreen, browseable lightbox like parent game media. `PcDlcMediaTab.vue` renders only role labels and delete controls, without image URLs or the existing `RCarousel` lightbox. The Files tab renders owned DLC media as unlabeled Download buttons without filename, role, size, digest, or preview. The Notes tab renders missing `common.title`, `common.description`, and `common.public` keys literally, and its public/private control does not explain its state. After a successful DLC-note save, the page retains a stale component version, causing a subsequent media upload to receive 409 Conflict while showing the missing `common.error` key. Reloading the page refreshes the version and permits the upload, but the uploaded media remains indistinguishable in the current UI.

### 5. Responsive und Eingabeprüfung

expected: Haupttitel und DLC sind in heller und dunkler Ansicht bei xs, md und xl mit Maus, Tastatur und Gamepad ohne Fokusfalle bedienbar.
result: pass
evidence: The user confirmed responsive layouts, light and dark themes, and keyboard and gamepad navigation.

## Summary

total: 5
passed: 5
issues: 4
pending: 0
skipped: 0
blocked: 0

## Gaps

- DLC images lack the parent-media fullscreen, browseable lightbox interaction.
- DLC media management and file downloads lack sufficient identity and preview information to tell images apart.
- DLC Notes has missing labels and an unclear public/private control.
- Saving a DLC note makes a later media upload fail with a stale-version conflict and an unhelpful missing-key error.

## Gap Closure Retest

implementation: 13-05-PLAN.md
result: pending
checks:

- Open `Medien` for `A Woman's Lot`: every entry has a preview, role and MIME type; selecting a preview opens a fullscreen gallery with previous/next browsing.
- Open `Dateien`: owned-media rows show their role, MIME type and image preview before their `Herunterladen` action.
- Open `Notizen`: title, content and visibility are translated; the visibility button states `Öffentlich` or `Privat`.
- Save a note, then immediately upload an image under `Medien`: the upload succeeds without a 409 conflict or literal `common.error` text.
