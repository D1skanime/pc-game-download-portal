---
status: testing
phase: 13-pc-igdb-metadata-and-dlc-media
source: 13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-PLAN.md
started: 2026-09-04T21:30:09Z
updated: 2026-09-04T21:43:30Z
---

## Current Test

number: 2
name: Eindeutig verknüpfter DLC besitzt eigene Metadaten und Medien
expected: |
Öffne danach den eindeutig verknüpften DLC. Seine Detailseite und sein Medien-Tab zeigen nur seine eigenen Metadaten, Cover und Screenshots, ohne Medien des Haupttitels.
awaiting: user response

## Tests

### 1. Parent-IGDB-Metadaten nach Windows-Scan

expected: Scanne einen Windows-Haupttitel mit einer eindeutigen IGDB-Zuordnung. Auf seiner Detailseite zeigt die Übersicht den PC-Veröffentlichungstermin, den Hauptentwickler, Publisher und Themen. Cover und Screenshots sind in RomM gespeichert und sichtbar.
result: pass

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
passed: 1
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

[none yet]
