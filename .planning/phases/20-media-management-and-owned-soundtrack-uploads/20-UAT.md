---
phase: 20
plan: "08"
status: approved
language: de
created: 2026-09-28
---

# Phase 20 - Browser-UAT: Medienverwaltung und eigene Soundtracks

## Sicherheitsgrenze

Bitte nur Witcher 3 in der v2-Media-Oberfläche prüfen. Alle Aktionen dürfen
nur RomM-eigene Medien betreffen. Nicht ändern: Quellbibliothek, NAS, Team4s
oder Docker Compose.

Automatisiert bestätigt: MariaDB- und PostgreSQL-Migrationszyklen, OpenAPI-
Generierung, Typecheck, Produktions-Build, Locale-Prüfungen sowie 91 Vitest-
Dateien mit 818 Tests.

## Freigabeprotokoll

**Ergebnis:** APPROVED

Der Nutzer hat die Phase-20-UAT nach dem Legacy-Media-Backfill freigegeben.
Für Witcher 3 zeigt Media die migrierten Screenshots und Artwork-Kandidaten;
der Management-Workflow wurde akzeptiert. Diese Nachprüfung betrifft nur
RomM-eigene Katalog- und Resource-Medien. Sie bestätigt keine Änderung an der
Quellbibliothek, dem NAS, Team4s oder Docker Compose.

**Erneut geprüfter Migrationsfall:** Legacy-ROM 13 (Witcher 3), dessen
persistierte RomM-Medien durch Revision 0129 als verwaltbare Kandidaten
sichtbar sind.

## Nachtrag: lokale und hochgeladene Hintergrundmusik (2026-09-29)

**Ergebnis:** APPROVED

Im isolierten Phase-9-UAT-Stack wurde Witcher 3 (ROM 13) geprüft. Zwei lokale
MP3-Dateien im `OST`-Ordner wurden nach einem einmaligen Windows-Komplettscan
als Soundtrack-Dateien erkannt. Zusätzlich wurde ein RomM-eigener,
hochgeladener Soundtrack als Hintergrundkandidat ausgewählt. Die Wiedergabe
funktionierte nach dem Wechsel auf die aktive Witcher-Detailseite. Der Nutzer
hat diesen UAT-Fall ausdrücklich freigegeben.

Der während der Prüfung aufgedeckte fehlende RQ-Worker im isolierten Stack
wurde nur für den einzelnen Testscan temporär gestartet; drei wartende,
veraltete UAT-Scan-Jobs wurden zuvor verworfen. Es gab keine Änderung an NAS,
Team4s, Docker Compose oder einer echten Quellbibliothek.

## Vorbereitung

- [ ] Angemeldet, v2 aktiviert, Witcher 3 geöffnet, Reiter **Media** gewählt.
- [ ] Schreibberechtigung für Verwaltungsaktionen vorhanden.
- [ ] Für reine Betrachtung auch mit einem Benutzer ohne Schreibrecht prüfen:
      Medien sichtbar, Verwaltungsaktionen nicht sichtbar.

## Themes, Größen und Eingabe

Für jede Zelle prüfen: lesbare Karten und Reihen, keine Überlappung oder
horizontales Scrollen, verständliche Tooltips/Aria-Labels an Icon-Aktionen.

| Ansicht    | Dunkel            | Hell              |
| ---------- | ----------------- | ----------------- |
| xs, 320 px | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL |
| sm         | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL |
| md         | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL |
| Desktop    | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL |

| Modalität | Prüfen                                           | Ergebnis          |
| --------- | ------------------------------------------------ | ----------------- |
| Maus      | Refresh, Auswahl, Upload, Sortierung, Löschen    | [ ] PASS [ ] FAIL |
| Tastatur  | Tab, Enter, Escape, Fokus ohne Falle             | [ ] PASS [ ] FAIL |
| Touch     | xs-Ziele mindestens 44 px, Upload und Sortierung | [ ] PASS [ ] FAIL |
| Gamepad   | Reiter, Aktionen, Dialog-Abbruch und Player      | [ ] PASS [ ] FAIL |

## Screenshots und Artwork

- [ ] `Provider-Medien aktualisieren` lädt neu, ohne bestätigte Auswahl oder
      Reihenfolge unbemerkt zu verändern.
- [ ] `In Übersicht anzeigen` ist nur eine Platzierung, kein Löschen.
- [ ] Screenshot oder Artwork als Hintergrund hinzufügen und entfernen;
      sichtbare Ordnungsnummer prüfen.
- [ ] Erlaubtes Bild hochladen: Fortschritt, Ergebnis und RomM-eigener Ursprung
      sind klar sichtbar.
- [ ] Mindestens zwei Hintergründe mit `Nach oben` / `Nach unten` ordnen; erste
      und letzte Zeile erklären deaktivierte Bewegungen.
- [ ] Provider-Medium und hochgeladenes Artwork: Abbruch belässt alles; nach
      Bestätigung wird nur RomM-eigener Speicher gelöscht.

## Bewegung und Soundtrack

- [ ] Mit zwei Hintergründen bei normaler Bewegung nur auf aktiver Detailseite
      in der festgelegten Reihenfolge rotieren lassen.
- [ ] Bei **Bewegung reduzieren** bleibt nur der erste Hintergrund statisch,
      ohne periodischen Wechsel oder Preload. Nach Deaktivierung nur bei zwei
      Hintergründen und aktiver Detailseite wieder Rotation.
- [ ] Erlaubte Audiodatei hochladen, in Soundtrack aufnehmen, zwei Tracks
      ordnen. Listenreihenfolge, Vorheriger/Nächster und Warteschlange sind gleich.
- [ ] Einen hochgeladenen, RomM-eigenen Track unabhängig von der manuellen
      Soundtrack-Warteschlange als Hintergrundmusik markieren. Witcher 3
      verlassen und erneut auf der aktiven Detailseite öffnen: Die gemeinsame
      Auswahl aus lokalen und aktiven hochgeladenen Hintergrund-Tracks ist
      berechtigt zur zufälligen Wiedergabe. Ein nicht markierter oder inaktiver
      Upload wird nicht gewählt. Eine Browser-Autoplay-Sperre wird getrennt
      vom manuellen Player-Ergebnis dokumentiert.
- [ ] Wiedergabe, Pause, Suche, Lautstärke, Download, Vorheriger und Nächster
      prüfen.
- [ ] Aktiven Track löschen: Wiedergabe stoppt, Bestätigung ist erforderlich,
      Kandidat und Platzierungen verschwinden erst nach Bestätigung.
- [ ] Akzeptiertes, nicht dekodierbares Format testen: begrenzte Fehlermeldung
      mit Wiederholen, Katalogeintrag bleibt erhalten, keine Transkodierung.

## Fehler- und Konfliktzustände

- [ ] Leere Screenshots, Artwork und Soundtrack zeigen passende Erklärung und
      nur zulässige Aktion.
- [ ] Ungültiger Upload nennt Datei und Grund, erneuter Versuch möglich.
- [ ] Netzwerkfehler bewahrt bestätigte Liste/Reihenfolge und bietet Wiederholen.
- [ ] Parallel geänderte Reihenfolge stellt Serverreihenfolge wieder her und
      zeigt Konflikthinweis.

## Ergebnis

**Gesamtergebnis:** [ ] APPROVED [ ] FAIL

**Datum, Tester, Browser/Version:**

**Defekte mit reproduzierbaren Schritten:**

1.

2.

3.

Nach vollständiger Prüfung `approved` zurückmelden oder konkrete Defekte mit
Reproduktionsschritten angeben.
