# Portainer-Installation für die PC Game Download Portal Edition

Diese Anleitung beschreibt die Installation des aktuellen Forks auf einem
Synology-NAS, QNAP-NAS oder einem normalen Linux-Server mit Docker und
Portainer. Sie richtet sich an Betreiber, die eine bestehende PC-Spiele-
bibliothek verwalten möchten, ohne deren Dateien oder Ordner umzuschreiben.

Die Anleitung verwendet die produktive Git-Stack-Datei
examples/portainer-stack.yml. Die Entwicklungsdatei docker-compose.yml ist
dafür nicht vorgesehen.

## 1. Was wird installiert?

Der Stack besteht aus zwei Diensten:

- romm: Weboberfläche, API, Scan- und Download-Funktionen.
- romm-db: MariaDB für Katalog, Benutzer, Einstellungen und Metadaten.

Zusätzlich werden Docker-Volumes und drei konfigurierbare NAS-Verzeichnisse
verwendet:

| Bereich          | Container-Pfad  | Zweck                                         |
| ---------------- | --------------- | --------------------------------------------- |
| Spielebibliothek | /romm/library   | Bestehende Spiele, immer read-only            |
| Assets           | /romm/assets    | Schreibbare Uploads, Saves, States und Assets |
| Konfiguration    | /romm/config    | Schreibbare Anwendungs-Konfiguration          |
| RomM-Ressourcen  | /romm/resources | Docker-verwaltete RomM-Ressourcen             |
| Redis/Valkey     | /redis-data     | Laufzeit- und Cache-Daten                     |
| MariaDB          | /var/lib/mysql  | Dauerhafte Katalogdaten                       |

Die Originalbibliothek wird mit :ro eingebunden. Scans und Metadaten-
aktualisierungen dürfen deshalb keine Dateien in der Originalbibliothek
umbenennen, löschen oder verändern.

## 2. Voraussetzungen

Du brauchst:

- einen laufenden Docker-Dienst;
- Portainer mit Unterstützung für Git-basierte Compose-Stacks;
- eine vorhandene Spielebibliothek, die vom Docker-Daemon erreichbar ist;
- ein beschreibbares Verzeichnis für Assets;
- ein beschreibbares Verzeichnis für Konfiguration;
- genügend Speicher für das Docker-Image und MariaDB;
- optional Zugangsdaten für Metadatenanbieter.

Die Pfade müssen auf dem Host gelten, auf dem Docker läuft. Ein Pfad, der nur
auf deinem PC sichtbar ist, ist für einen Docker-Daemon auf dem NAS nicht
automatisch verfügbar.

## 3. Ordner auf dem Host vorbereiten

### Synology DSM

Erstelle in File Station oder per SSH die benötigten freigegebenen Ordner.
Die folgenden Werte sind Beispiele für ein Volume namens volume1, keine
universellen Standardwerte:

    /volume1/Games
    /volume1/docker/pc-downloadportal/assets
    /volume1/docker/pc-downloadportal/config

Trage den tatsächlichen Pfad deiner NAS-Installation ein. Der Docker-Dienst
muss die Spielebibliothek lesen können. Assets und Konfiguration müssen
beschreibbar sein. Bei einer Installation über Container Manager kann die
Berechtigung des Docker-Benutzers oder der Gruppe docker relevant sein.

### QNAP

QNAP-Pfade hängen vom Namen des Storage Pools und der Freigabe ab. Verwende
den Pfad, den QNAP im Container- oder File-Station-Dialog für den Host
anzeigt. Übernimm keine Synology-Pfade. Lege beispielsweise eine Freigabe
für Spiele und eine separate, beschreibbare App-Freigabe für Assets und
Konfiguration an.

### Linux

Verwende absolute Pfade, die der Docker-Dienst lesen beziehungsweise
beschreiben kann, zum Beispiel:

    /srv/romm/library
    /srv/romm/assets
    /srv/romm/config

Auch diese Werte sind nur Beispiele. Prüfe vor dem Deployment mit ls -ld,
ob die Pfade existieren und die Berechtigungen passen.

Die drei Host-Verzeichnisse müssen vor dem Deployment existieren. Lege die
Spielebibliothek niemals in das Git-Checkout und mounte sie nicht über
/romm/resources oder /romm/assets.

## 4. Repository und Compose-Datei in Portainer

1. Öffne in Portainer Stacks und wähle Add stack.
2. Wähle Git repository.
3. Verwende als Repository-URL:

   https://github.com/D1skanime/pc-game-download-portal.git

4. Wähle als Branch oder Reference main.
5. Verwende als Compose path:

   examples/portainer-stack.yml

6. Trage die Variablen aus examples/portainer.env.example in den
   Environment-Variablenbereich von Portainer ein.
7. Ersetze alle Platzhalter und die drei Beispielpfade.
8. Prüfe vor dem Deploy, dass die Spielebibliothek read-only gemountet wird.
9. Klicke auf Deploy the stack.

### Build, image und ROMM_IMAGE

Der Stack hat sowohl build als auch image:

- build.context: .. zeigt aus dem Ordner examples auf den Git-Repository-Root.
- dockerfile: docker/Dockerfile ist die produktive Build-Datei.
- target: full-image wählt das vollständige Produktions-Image.
- image ist der lokale Tag, den Docker dem gebauten Image gibt.
- ROMM_IMAGE ist standardmässig pc-game-download-portal:portainer.

Der Standardpfad baut also den ausgecheckten Fork aus Git. ROMM_IMAGE ist
kein Ersatz für den Git-Checkout. Überschreibe den Wert nur, wenn du bewusst
ein kompatibles, bereits gebautes Image verwendest und dessen Herkunft,
Version und Funktionsvertrag geprüft hast. Trage niemals versehentlich ein
offizielles RomM-Image ein, wenn du den Fork installieren möchtest.

## 5. Umgebungsvariablen

### Allgemeine Anwendungseinstellungen

- COMPOSE_PROJECT_NAME: Name des Compose-Projekts. Standard ist romm.
- ROMM_CONTAINER_NAME: Containername der Anwendung.
- ROMM_DB_CONTAINER_NAME: Containername der Datenbank.
- TZ: Zeitzone des Containers, normalerweise UTC.
- ROMM_IMAGE: Tag des gebauten Fork-Images. Der dokumentierte Standard ist
  pc-game-download-portal:portainer.

### Netzwerk

- ROMM_HTTP_PORT: Host-Port. Der Container hört intern immer auf Port 8080.
  Wenn 8080 auf dem NAS belegt ist, kann beispielsweise 8180 verwendet
  werden. Danach öffnest du http://<NAS-IP>:8180.

### NAS-Verzeichnisse

- ROMM_LIBRARY_PATH: vorhandene Spielebibliothek. Erforderlich und
  read-only eingebunden.
- ROMM_ASSETS_PATH: erforderliches, beschreibbares Verzeichnis für Assets,
  Saves, States und weitere verwaltete Dateien.
- ROMM_CONFIG_PATH: erforderliches, beschreibbares Verzeichnis für die
  Konfiguration.

Synology-Beispiele:

    ROMM_LIBRARY_PATH=/volume1/Games
    ROMM_ASSETS_PATH=/volume1/docker/pc-downloadportal/assets
    ROMM_CONFIG_PATH=/volume1/docker/pc-downloadportal/config

Diese Werte sind Beispiele. Bei einem falschen Host-Pfad startet der Stack
möglicherweise nicht oder die Bibliothek bleibt leer.

### Datenbank und Sicherheit

- ROMM_DB_NAME: MariaDB-Datenbankname.
- ROMM_DB_USER: MariaDB-Anwendungsbenutzer.
- ROMM_DB_PASSWORD: erforderliches Passwort für RomM.
- ROMM_DB_ROOT_PASSWORD: erforderliches, anderes Passwort für MariaDB root.
- ROMM_AUTH_SECRET_KEY: erforderlicher geheimer Schlüssel für die
  Authentifizierung.

Generiere sichere Werte beispielsweise mit:

    openssl rand -hex 32

Verwende für ROMM_DB_PASSWORD, ROMM_DB_ROOT_PASSWORD und
ROMM_AUTH_SECRET_KEY separate Werte. Schreibe echte Werte nur in Portainer
oder in einen dafür vorgesehenen Secret-Store. Committe keine ausgefüllte
ENV-Datei.

### Optionale Metadatenanbieter

Diese Werte dürfen leer bleiben:

- SCREENSCRAPER_USER
- SCREENSCRAPER_PASSWORD
- RETROACHIEVEMENTS_API_KEY
- STEAMGRIDDB_API_KEY
- HASHEOUS_API_ENABLED

Fehlende Provider-Zugangsdaten verhindern nicht den Basisstart. Nur die
entsprechende Suche oder Anreicherung bleibt nicht verfügbar.

## 6. Erster Start

1. Warte, bis romm-db den Healthcheck bestanden hat.
2. Warte danach, bis auch romm als healthy angezeigt wird.
3. Öffne den konfigurierten Host-Port im Browser.
4. Lege den ersten Benutzer an oder melde dich mit dem vorgesehenen
   Administratorkonto an.
5. Öffne die Speicherverwaltung.
6. Erstelle oder prüfe die Plattform-Zuordnung zur read-only eingebundenen
   Spielebibliothek.
7. Führe zunächst einen kleinen Testscan aus.

Der produktive Entrypoint übernimmt die normale Umgebungsvorbereitung und die
Migrationen. Eine manuelle Datenbankmigration ist für einen normalen ersten
Start nicht nötig.

Wenn romm-db unhealthy bleibt, prüfe zuerst, ob ROMM_DB_PASSWORD in
Anwendung und MariaDB identisch ist und ob ROMM_DB_ROOT_PASSWORD gesetzt ist.
Wenn RomM nicht startet, prüfe die erforderlichen Variablen und die
Schreibrechte für Assets und Konfiguration.

## 7. Funktionstest

Führe nach dem ersten Start einen kleinen, kontrollierten Test durch:

1. Ordne die PC-Plattform dem richtigen Host-Unterordner zu.
2. Starte einen Scan mit einem Testspiel.
3. Prüfe, ob das Spiel gefunden und der Plattform zugeordnet wird.
4. Prüfe Titel und Metadaten.
5. Prüfe die Cover- und Provider-Suche, falls ein Provider konfiguriert ist.
6. Prüfe die Erkennung eines vorhandenen DLC- oder Erweiterungsordners.
7. Starte einen Browser-Download eines kleinen Testbestandteils.
8. Prüfe, ob der Download vollständig ist.
9. Vergleiche die ursprüngliche Spielebibliothek vor und nach dem Test.

Die Originaldateien und ihre Ordnerstruktur müssen unverändert bleiben. Bei
einem unerwarteten Schreibversuch den Stack stoppen und zuerst Mounts und
Berechtigungen prüfen.

## 8. Updates

Für ein Update:

1. Erstelle zuerst ein Backup von MariaDB und den RomM-Ressourcen.
2. Wähle in Portainer die gewünschte Revision oder den gewünschten Tag des
   Git-Repositories.
3. Ziehe die neue Revision und redeploye den Stack.
4. Behalte romm_mysql_data, romm_resources und die Host-Verzeichnisse.
5. Prüfe danach die Healthchecks und führe einen kurzen Funktionstest aus.

Die Spielebibliothek wird nicht durch Git ersetzt und darf nicht als Teil eines
Updates gelöscht oder neu kopiert werden.

## 9. Backups und Rollback

Sichere mindestens:

- das Docker-Volume romm_mysql_data;
- das Docker-Volume romm_resources;
- ROMM_ASSETS_PATH;
- ROMM_CONFIG_PATH;
- die Portainer-Stack-Variablen und Secrets über einen sicheren Secret-Store.

Die read-only Spielebibliothek muss nicht als Teil des RomM-Stack-Backups
kopiert werden, sollte aber nach deiner eigenen NAS-Backup-Strategie geschützt
sein.

Bei einem fehlerhaften Update:

1. Stoppe oder redeploye den Stack mit der vorherigen bekannten Git-Revision.
2. Verwende dieselben Datenbank-, Ressourcen-, Assets- und Config-Daten.
3. Starte die Healthchecks ab.
4. Prüfe Login, Bibliothek und einen kleinen Testdownload.
5. Führe kein Datenbank-Rollback ohne ein passendes Backup und eine
   versionskompatible Vorgehensweise durch.

## 10. Troubleshooting

- Required variable fehlt: Der Variablenname fehlt in Portainer oder enthält
  noch einen Platzhalter.
- Bibliothek leer: Der Host-Pfad ist aus Sicht des Docker-Daemons falsch, nicht
  gemountet oder der Container darf ihn nicht lesen.
- Import oder Scan scheitert: Prüfe, dass die Plattform auf den richtigen
  Container-Unterordner zeigt und die Bibliothek nicht schreibbar erwartet
  wird.
- Assets oder Saves können nicht geschrieben werden: Prüfe Besitzer und
  Schreibrechte von ROMM_ASSETS_PATH.
- Datenbank unhealthy: Prüfe beide Datenbankpasswörter und den dauerhaften
  MariaDB-Volume.
- Metadaten oder Cover fehlen: Prüfe nur die Zugangsdaten des betreffenden
  Providers. Der Basisbetrieb kann trotzdem funktionieren.
- Update zeigt alte Version: Prüfe in Portainer die ausgecheckte Revision und
  stelle sicher, dass der Anwendungscontainer neu gebaut wurde.

## 11. Technische Gegenprüfung

Die Repository-Prüfung kann im Linux-Checkout ausgeführt werden:

    bash scripts/verify-portainer-stack.sh

Sie rendert den Stack, prüft die read-only Bibliotheksbindung, Healthchecks,
persistente Zielpfade, erforderliche Variablen sowie Secret- und Laufzeitpfad-
Sicherheit. Eine echte Installation auf Synology oder QNAP gilt erst dann als
getestet, wenn sie auf dieser Plattform tatsächlich durchgeführt wurde.
