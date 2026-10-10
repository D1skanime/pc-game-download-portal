---
quick_task: 261010-skc
slug: match-pc-dlc-overview-media-image-grid-t
title: Match PC DLC overview media image grid to main game overview layout
status: complete
created: 2026-10-10
---

# Plan: PC-DLC-Übersicht an das Main-Game-Bildraster angleichen

## Ziel

Die in der PC-DLC-Übersicht platzierten Bilder sollen exakt denselben responsiven Screenshot-Grid-Vertrag verwenden wie die Bilder in der Main-Game-Übersicht. Die bestehende gemeinsame `ScreenshotsTab`-Architektur wird wiederverwendet; es wird kein zweites Layout-System eingeführt.

## Befund / aktuelle Ursache

- `OverviewTab.vue` rendert die Main-Game-Screenshots über `ScreenshotsTab` mit `layout="overview"`.
- `ScreenshotsTab.vue` kapselt dafür den vorhandenen Overview-Grid-Vertrag (`auto-fit`, Mindestbreite und den gemeinsamen Small-Breakpoint).
- `PcDlcDetail.vue` rendert `overviewMedia` bereits über `ScreenshotsTab`, übergibt aber nicht `layout="overview"`.
- Zusätzlich existiert in `PcDlcDetail.vue` für `.pc-dlc-detail__media` ein eigenes Grid mit `minmax(18rem, 1fr)`. Dieses konkurriert mit dem gemeinsamen Screenshot-Grid und führt dazu, dass DLC-Bilder anders bzw. kleiner angeordnet werden.

## Umsetzung

### 1. Gemeinsamen Layout-Vertrag verwenden

Datei: `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`

- Den bestehenden `ScreenshotsTab`-Aufruf im `overviewMedia`-Abschnitt um `layout="overview"` ergänzen.
- `overviewMedia` und die bestehende Platzierungs-/Sortierlogik unverändert lassen; sie liefert weiterhin ausschließlich die für die DLC-Übersicht platzierten Medien in Positionsreihenfolge.
- Das lokale, nicht mehr benötigte `.pc-dlc-detail__media`-Grid entfernen bzw. auf die reine Abschnitts-/Container-Verantwortung reduzieren, damit keine zweite Spaltenlogik die gemeinsame Komponente überschreibt.
- Keine Kopie der Grid-CSS-Regeln aus `ScreenshotsTab.vue` anlegen.

### 2. Fokussierte Regression abdecken

Datei: `frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts`

- Einen Test ergänzen oder den bestehenden Test für die DLC-Übersicht erweitern, der den gerenderten `ScreenshotsTab`-Prop `layout` auf `"overview"` prüft.
- Die vorhandene Prüfung beibehalten, dass nur aktive, positiv positionierte `overviewPlacements` gerendert werden und der gemeinsame Viewer weiterhin alle ausgewählten Medien erhält.
- Eine Source-/Style-Regressionsprüfung ergänzen, falls erforderlich, dass `PcDlcDetail.vue` kein eigenes `grid-template-columns` für die Medienübersicht mehr definiert. Die Prüfung soll die Wiederverwendung von `ScreenshotsTab` schützen, nicht konkrete Browser-Pixelwerte festschreiben.

### 3. Verifikation

- Fokussierte Vitest-Dateien für `PcDlcDetail` und den gemeinsamen `ScreenshotsTab` ausführen.
- Frontend-Typecheck ausführen.
- Live die PC-DLC-Übersicht auf Desktop und kleinem Viewport prüfen: dieselbe responsive Spaltenanzahl/Mindestbreite und denselben Bildzuschnitt wie bei der Main-Game-Übersicht.
- Bestehende unabhängige Dirty-Changes im Checkout unangetastet lassen.

## Akzeptanzkriterien

1. PC-DLC-Übersichtsbilder rendern über `ScreenshotsTab` mit `layout="overview"`.
2. Main Game und PC DLC teilen exakt die bestehende responsive Overview-Grid-Implementierung.
3. Für PC DLC existiert keine parallele Spalten-/Grid-Architektur.
4. Aktive DLC-Overview-Platzierungen, Reihenfolge und Lightbox-Verhalten bleiben unverändert.
5. Fokussierte Tests und Typecheck bestehen.

## Nicht im Umfang

- Keine Änderung an Media-Upload, Delete, Placement-API oder Datenmodell.
- Keine Änderung an der Main-Game-Übersicht oder am gemeinsamen `ScreenshotsTab`-Raster selbst, sofern die Wiederverwendung ohne Anpassung ausreicht.
- Kein Deployment.
