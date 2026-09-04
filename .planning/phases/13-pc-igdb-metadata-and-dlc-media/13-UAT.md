---
status: partial
phase: 13-pc-igdb-metadata-and-dlc-media
source: 13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-PLAN.md
started: 2026-09-04T21:30:09Z
updated: 2026-09-04T21:34:00Z
---

## Current Test

[testing paused, blocker in Test 1]

## Tests

### 1. Parent-IGDB-Metadaten nach Windows-Scan

expected: Scanne einen Windows-Haupttitel mit einer eindeutigen IGDB-Zuordnung. Auf seiner Detailseite zeigt die Übersicht den PC-Veröffentlichungstermin, den Hauptentwickler, Publisher und Themen. Cover und Screenshots sind in RomM gespeichert und sichtbar.
result: issue
reported: "nope klappt ga rnicht"
severity: blocker

### 2. Eindeutig verknüpfter DLC besitzt eigene Metadaten und Medien

expected: Öffne danach den eindeutig verknüpften DLC. Seine Detailseite und sein Medien-Tab zeigen nur seine eigenen Metadaten, Cover und Screenshots, ohne Medien des Haupttitels.
result: pending

### 3. Mehrdeutiger oder ungelöster DLC bleibt unverändert

expected: Ein mehrdeutiger oder ungelöster DLC bleibt ohne neu übernommene Metadaten und Medien unverändert.
result: pending

### 4. Eigentumsgrenzen bleiben intakt

expected: Haupttitel- und DLC-Medien vermischen sich nicht. Der externe Quellbaum bleibt durch den Scan unverändert, nur RomM-eigene Medien werden ergänzt.
result: pending

### 5. Responsive und Eingabeprüfung

expected: Haupttitel und DLC sind in heller und dunkler Ansicht bei xs, md und xl mit Maus, Tastatur und Gamepad ohne Fokusfalle bedienbar.
result: pending

## Summary

total: 5
passed: 0
issues: 1
pending: 4
skipped: 0
blocked: 0

## Gaps

- truth: "Ein Windows-Haupttitel mit eindeutiger IGDB-Zuordnung zeigt nach dem Scan PC-Veröffentlichungstermin, Hauptentwickler, Publisher, Themen sowie RomM-eigene Medien."
  status: failed
  reason: "User reported: nope klappt ga rnicht"
  severity: blocker
  test: 1
  root_cause: "Beim Speichern der von IGDB gelieferten Haupttitel-Metadaten wird das temporäre Feld url_artworks in das SQLAlchemy-Update für die Rom-Tabelle übernommen. Die Tabelle besitzt keine solche Spalte, daher bricht der PUT /api/roms/{id} mit sqlalchemy.exc.CompileError: Unconsumed column names: url_artworks ab."
  artifacts:
  - path: "backend/handler/metadata/igdb_handler.py"
    issue: "Liefert url_artworks zusätzlich zu persistierbaren Metadaten."
  - path: "backend/handler/database/roms_handler.py"
    issue: "Übernimmt das transiente Feld in das Datenbank-Update."
    missing:
  - "url_artworks vor dem Rom-Update ausfiltern und nur für den Medienimport verwenden."
  - "Regressionstest für das Speichern eines IGDB-Treffers mit Artwork ergänzen."
    debug_session: ".planning/debug/phase13-parent-igdb-artwork-update.md"
