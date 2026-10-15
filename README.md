# PC Game Download Portal

PGDP ist eine eigenständige Edition zur Verwaltung einer bestehenden PC-Spielebibliothek, ohne Quelldateien oder Ordner umzustrukturieren oder zu verändern.

Diese Edition verbindet die bekannte ROM-Bibliotheksverwaltung mit einem schreibgeschützten PC-Bibliotheksworkflow, eigenen PC-Spielkomponenten, Metadaten-gestützter DLC-Zuordnung, Medienverwaltung, verifizierten Browser-Downloads und einer reproduzierbaren Docker-Bereitstellung für NAS-Systeme.

## Was diese Edition bietet

- Externe PC-Bibliotheksverzeichnisse mit Read-only-Schutz und Plattform-zu-Speicher-Zuordnung.
- Katalogeinträge für Hauptspiele, Installer, Updates, DLC, Patches, Handbücher und optionale Dateien.
- Hash-basierte Download-Manifeste für ausgewählte PC-Komponenten.
- Browser-Downloads mit Fortschritt, Pause, Fortsetzen, Wiederholung, Abbruch und Verlauf.
- Metadaten-Zuordnung für PC-Spiele und DLC über IGDB, Steam und weitere Anbieter.
- Deutsche Steam-Metadaten mit kontrollierter Sprache und Fallback-Regeln.
- Medienverwaltung für Screenshots und Artwork mit Löschen, Duplikat-Schutz, Hintergrundauswahl und Übersichtsbild.
- Responsive Übersichten für Desktop- und Tablet-Bildschirme.
- Git-basierte Portainer-Bereitstellung, die ROM-Dateien, Medien, Zugangsdaten und Datenbankzustand ausserhalb von Git hält.

## Entwicklungsmeilensteine

Während der Entwicklung wurden unter anderem folgende Funktionen abgeschlossen:

1. Unveränderliche Speichergrundlage für bestehende Spielearchive.
2. Read-only-Grenze für Scans und Katalogoperationen.
3. Verwaltung und Validierung von Plattform-Speicherzuordnungen.
4. Aktive v2-Speicherarchitektur mit klaren Datenbereichen.
5. Sichere Migration bestehender Legacy-Daten.
6. Vollständige v2-Verwaltung für Speicher und Bibliothek.
7. PC-Integrationsmodell und PC-spezifische Detailansichten.
8. PC-Medien- und DLC-Navigation.
9. IGDB-Metadatenzuordnung und DLC-Medienverarbeitung.
10. Unveränderliche Download-Manifeste und fortsetzbare Browser-Übertragungen.
11. Browser-Downloadverwaltung mit Warteschlange und Wiederherstellung.
12. Steam-Metadaten für PC-Spiele und DLC.
13. Robuste PC-Scans, IGDB-Zuordnung und sichere DLC-Anreicherung.
14. Medienverwaltung, Screenshot-Raster und Upload eigener Soundtracks.
15. Mehrsprachige Steam-Metadaten mit deutschen und englischen Varianten.
16. Aktuelle UI- und UX-Verbesserungen sowie manuelle Metadatenbearbeitung.
17. Reproduzierbarer Portainer- und Docker-Deploy mit persistentem Speicher, Startprüfungen und Clean-Install-Validierung.

## Interaktive UI-Demos

Die Aufnahmen zeigen workflowspezifische Abläufe mit synthetischen Demodaten. Sie enthalten keine ROM-Dateien, persönlichen Konten, privaten Medien oder Zugangsdaten.

|                        PC-Downloadsteuerung                        |                       Medien- und Artwork-Workflow                       |
| :----------------------------------------------------------------: | :----------------------------------------------------------------------: |
| ![PC-Downloadsteuerung](docs/screenshots/pc-download-controls.gif) | ![Medien- und Artwork-Workflow](docs/screenshots/media-artwork-flow.gif) |

## Installation mit Portainer

Der unterstützte Bereitstellungsweg ist ein Docker-Compose-Stack, der über Portainer verwaltet wird. Die Stack-Datei liegt unter [examples/portainer-stack.yml](examples/portainer-stack.yml), die sichere Variablenvorlage unter [examples/portainer.env.example](examples/portainer.env.example).

Die vollständige deutsche Anleitung steht in [docs/PORTAINER_INSTALL.md](docs/PORTAINER_INSTALL.md).

### Voraussetzungen

- Portainer mit Unterstützung für Git-basierte Docker-Compose-Stacks.
- Ein NAS-Verzeichnis mit der bestehenden PC- und ROM-Bibliothek.
- Schreibbare NAS-Verzeichnisse für Assets und Konfiguration.
- Genügend Speicher für den Anwendungs-Build und MariaDB-Daten.
- Optional Konten und API-Schlüssel für Metadatenanbieter.

### Aus GitHub bereitstellen

1. Öffne in Portainer Stacks und wähle Add stack.
2. Wähle Git repository.
3. Verwende die Repository-URL https://github.com/D1skanime/pc-game-download-portal.git.
4. Verwende als Branch oder Referenz main.
5. Verwende als Compose-Pfad examples/portainer-stack.yml.
6. Übernimm die Variablen aus examples/portainer.env.example in den Portainer-Bereich für Umgebungsvariablen.
7. Ersetze alle Platzhalter und setze die drei NAS-Pfade.
8. Prüfe, dass die Spielebibliothek read-only eingebunden wird.
9. Deploye den Stack.

Der Git-Stack baut das ausgecheckte Repository mit docker/Dockerfile. Damit enthält die Bereitstellung den Code der ausgewählten Git-Revision. Behalte die MariaDB- und Ressourcen-Volumes bei Updates und Redeployments.

### Erforderliche Variablen

| Variable              | Zweck                                                    |
| --------------------- | -------------------------------------------------------- |
| PGDP_LIBRARY_PATH     | Bestehende ROM- und PC-Bibliothek, read-only eingebunden |
| PGDP_ASSETS_PATH      | Schreibbares Verzeichnis für Assets, Saves und States    |
| PGDP_CONFIG_PATH      | Schreibbares Konfigurationsverzeichnis                   |
| PGDP_DB_PASSWORD      | Passwort des MariaDB-Anwendungsbenutzers                 |
| PGDP_DB_ROOT_PASSWORD | Separates MariaDB-root-Passwort                          |
| PGDP_AUTH_SECRET_KEY  | Langer zufälliger Authentifizierungsschlüssel            |
| PGDP_HTTP_PORT        | Auf den Container gemappter NAS-Port                     |
| PGDP_TZ               | Zeitzone des Containers                                  |

Erzeuge eindeutige Secrets, zum Beispiel:

    openssl rand -hex 32

Trage echte Werte nur in Portainer oder einem unterstützten Secret-Store ein. Committe niemals ausgefüllte ENV-Dateien, API-Schlüssel, Passwörter, Tokens oder persönliche Pfade.

### Optionale Metadatenanbieter

Die Anbieter-Variablen dürfen leer bleiben. Die Anwendung startet trotzdem; der jeweilige Anbieter bleibt dann deaktiviert.

- SCREENSCRAPER_USER
- SCREENSCRAPER_PASSWORD
- RETROACHIEVEMENTS_API_KEY
- STEAMGRIDDB_API_KEY
- IGDB_CLIENT_ID
- IGDB_CLIENT_SECRET
- HASHEOUS_API_ENABLED

Ein fehlender Anbieter-Schlüssel ist kein Installationsfehler, sondern nur eine fehlende Provider-Konfiguration. Die Cover-Suche bleibt beispielsweise solange nicht verfügbar, bis der ausgewählte Anbieter gültige Zugangsdaten hat.

### Speicher und Persistenz

Erstelle die drei Host-Verzeichnisse vor dem Deployment. Binde die Quellbibliothek read-only ein, damit Scans sie nicht umorganisieren oder verändern können. Halte Ressourcen, Assets, Konfiguration, Redis-Daten und MariaDB-Daten in persistenten Docker-Volumes oder schreibbaren Host-Mounts.

Binde die NAS-Bibliothek nicht über /romm/resources oder /romm/assets ein. Diese Pfade haben andere Besitz- und Schreibregeln.

### Erster Start und Updates

Warte, bis pgdp und pgdp-db als healthy angezeigt werden. Öffne den konfigurierten HTTP-Port und schliesse die Erstanmeldung ab. Der normale Start übernimmt Umgebungsvorbereitung, Migrationen und Healthchecks automatisch.

Für ein Update wählst du in Portainer die gewünschte main-Revision und deployest den Git-Stack erneut. Behalte Datenbank- und Ressourcen-Volumes. Sichere die Datenbank vor grösseren Updates. Ersetze niemals die Spielebibliothek durch einen Git-Checkout.

### Deployment prüfen

Führe die Prüfung in einem Linux-Checkout aus:

    bash scripts/verify-portainer-stack.sh

Die Prüfung weist Entwicklerpfade, getrackte ENV-Dateien und getrackte Laufzeitordner wie Games, Docker und Media zurück.

## Daten- und Datenschutzgrenzen

Das Repository enthält Anwendungscode, Deployment-Vorlagen, Tests und synthetische Dokumentationsdemos. Folgende Daten bleiben auf dem Installationshost:

- ROM-Dateien und PC-Installer.
- Heruntergeladenes Artwork, Screenshots und weitere Medien.
- Datenbank- und Cache-Inhalte.
- NAS-Pfade.
- API-Schlüssel, Passwörter und Authentifizierungs-Secrets.
- Benutzerkonten und persönliche Bibliotheksmetadaten.

## Lokale Entwicklung

Lies CLAUDE.md für Repository-Regeln und die kanonische Linux-Entwicklungsumgebung.

Für den Entwicklungsstack:

    cp env.template .env
    docker compose up -d

Der produktionsähnliche Portainer-Stack ist vom Entwicklungs-Compose getrennt. Verwende für eine NAS-Bereitstellung die Portainer-Dateien und halte deren Umgebungswerte ausserhalb von Git.

## Fehlerbehebung

- Bei einer fehlenden erforderlichen Variable: Prüfe Variablennamen und Platzhalter, ohne Secrets in Logs oder Screenshots offenzulegen.
- Bei einem fehlerhaften pgdp-db-Healthcheck: Prüfe Datenbankpasswörter und das persistente Volume.
- Bei leerer Bibliothek: Prüfe, ob der Pfad auf dem NAS-Host existiert und für Docker sichtbar ist, nicht nur auf einer Arbeitsplatzmaschine.
- Bei nicht verfügbarer Metadatensuche: Prüfe die Zugangsdaten des ausgewählten Anbieters. Die Basisinstallation bleibt ohne Metadatenanbieter verwendbar.
- Wenn ein Update unverändert aussieht: Prüfe, ob Portainer die gewünschte Revision ausgecheckt und den Anwendungscontainer neu gebaut hat.

Für die vollständige Installations-, Backup- und Rollback-Anleitung siehe [docs/PORTAINER_INSTALL.md](docs/PORTAINER_INSTALL.md).
