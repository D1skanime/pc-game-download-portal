# RomM PC Library Edition

A fork of RomM focused on managing an existing PC game archive without
reorganizing or modifying the source files.

This edition combines the familiar ROM library experience with a read-only PC
library workflow, explicit PC game components, metadata-assisted DLC matching,
media curation, verified browser downloads, and a reproducible Docker
deployment for NAS systems.

## What this edition adds

- Read-only external PC library roots and explicit platform-to-storage mappings.
- Catalog records for base games, installers, updates, DLC, patches, manuals,
  optional files, and required archive sets.
- Immutable, hash-backed download manifests for selected PC components.
- Browser downloads with progress, pause, resume, retry, cancel, and history
  controls.
- Metadata matching for PC games and DLC through the configured providers,
  including IGDB and Steam.
- German Steam metadata with controlled language and fallback behavior.
- Media management for screenshots and artwork, including delete actions,
  duplicate-safe ownership, background selection, and overview selection.
- Responsive overview layouts for desktop and tablet-sized screens.
- A Git-based Portainer deployment that keeps ROM files, media, credentials,
  and database state outside Git.

## Development milestones

The following capabilities were completed during the development of this
edition:

1. Established an immutable storage foundation for existing game archives.
2. Added a read-only policy boundary so scans and catalog operations cannot
   rewrite source files.
3. Defined storage mapping administration and validation contracts.
4. Designed the active v2 storage architecture and data boundaries.
5. Moved preview and read paths onto the new storage model.
6. Added safe lifecycle handling and migration support for legacy data.
7. Delivered the v2 storage administration experience.
8. Removed obsolete v1 storage surfaces from the active workflow.
9. Added operational proofs for storage immutability.
10. Added the PC integration model and PC-specific detail views.
11. Added local PC media and DLC navigation.
12. Added dedicated DLC detail pages for local PC components.
13. Added IGDB metadata matching and DLC media handling for PC content.
14. Added immutable download manifests for selected files.
15. Added direct resumable browser transfers.
16. Defined the cross-platform desktop transfer client contract.
17. Delivered the browser download manager with queue and recovery controls.
18. Integrated Steam metadata for PC games and DLC.
19. Hardened PC quick scans, IGDB matching, and safe DLC enrichment.
20. Added media management and owned soundtrack uploads.
21. Unified administrative PC scans with German Steam metadata and media.
22. Added bulk automation for PC game and DLC assignment.
23. Added multilingual Steam metadata with German and English variants.
24. Stabilized the v2 UI and removed remaining legacy boundaries.
25. Hardened scan and media integration across the complete PC workflow.
26. Added the current UI and UX improvements, manual metadata editing,
    screenshot grids, media actions, DLC matching, and metadata fallback
    behavior.
27. Added a reproducible Portainer and Docker deployment contract with
    persistent storage, startup checks, and clean-install verification.

## Interactive UI demos

These recordings show fork-specific workflows with synthetic demo data. They do
not contain ROM files, personal accounts, private media, or credentials.

|                        PC download controls                        |                       Media and artwork workflow                       |
| :----------------------------------------------------------------: | :--------------------------------------------------------------------: |
| ![PC download controls](docs/screenshots/pc-download-controls.gif) | ![Media and artwork workflow](docs/screenshots/media-artwork-flow.gif) |

The download recording shows component selection and browser download controls.
The media recording shows screenshot and artwork navigation, adding media to the
overview, and selecting a background.

## Installation with Portainer

The supported deployment path is a Docker Compose stack managed by Portainer.
The stack is stored in [examples/portainer-stack.yml](examples/portainer-stack.yml)
and the safe variable template is
[examples/portainer.env.example](examples/portainer.env.example).

### Prerequisites

- Portainer with Git-based Docker Compose stack support.
- A NAS directory containing the existing PC and ROM library.
- Writable NAS directories for assets and configuration.
- Enough space for the application build and MariaDB data.
- Optional metadata-provider accounts and API keys.

### Deploy from GitHub

1. Open Portainer and choose **Stacks**, then **Add stack**.
2. Select **Git repository**.
3. Set the repository URL to
   https://github.com/D1skanime/pc-game-download-portal.git.
4. Set the branch or reference to **main**.
5. Set the Compose path to **examples/portainer-stack.yml**.
6. Add the variables from
   [examples/portainer.env.example](examples/portainer.env.example) to the
   Portainer environment-variable section.
7. Replace every placeholder and set the three NAS paths.
8. Deploy the stack.

The Git stack builds the checked-out repository with docker/Dockerfile. This
means the deployed application contains the code from the selected Git
revision. Keep the MariaDB and resource volumes when redeploying or updating.

### Required variables

| Variable              | Purpose                                             |
| --------------------- | --------------------------------------------------- |
| ROMM_LIBRARY_PATH     | Existing ROM and PC library root, mounted read-only |
| ROMM_ASSETS_PATH      | Writable assets, saves, and state directory         |
| ROMM_CONFIG_PATH      | Writable persistent configuration directory         |
| ROMM_DB_PASSWORD      | MariaDB application-user password                   |
| ROMM_DB_ROOT_PASSWORD | Separate MariaDB root password                      |
| ROMM_AUTH_SECRET_KEY  | Long random authentication key                      |
| ROMM_HTTP_PORT        | NAS port mapped to the application port             |
| TZ                    | Container timezone                                  |

Generate unique secrets, for example:

```bash
openssl rand -hex 32
```

Enter real values only in Portainer or a supported secret store. Never commit
filled environment files, API keys, passwords, tokens, or personal paths.

### Optional metadata providers

Provider variables can remain empty. The application still starts and the
provider stays unavailable until its credentials are supplied.

- SCREENSCRAPER_USER
- SCREENSCRAPER_PASSWORD
- RETROACHIEVEMENTS_API_KEY
- STEAMGRIDDB_API_KEY
- HASHEOUS_API_ENABLED

A missing provider credential is a provider configuration gap, not an
installation failure. For example, cover search can remain unavailable until
the selected provider has valid credentials.

### Storage and persistence

Create the three host directories before deployment. Mount the source library
read-only so scans cannot reorganize or modify it. Keep application resources,
assets, configuration, Redis data, and MariaDB data on persistent Docker
volumes or writable host mounts.

Do not mount the NAS library over /romm/resources or /romm/assets. Those paths
have different ownership and write semantics.

### First start and updates

Wait until both romm and romm-db are healthy. Open the configured HTTP port and
complete the first-login flow. Normal startup performs environment preparation,
migrations, and health checks automatically.

For an update, select the desired main revision in Portainer and redeploy the
Git stack. Keep the database and resource volumes. Back up the database before
major upgrades. Never replace the ROM library with a Git checkout.

### Deployment verification

From a Linux checkout, validate the sanitized stack template with:

```bash
bash scripts/verify-portainer-stack.sh
```

The check rejects developer paths, tracked environment files, and tracked
runtime folders such as Games, Docker, and Media.

For the complete deployment notes, see
[docs/PORTAINER_INSTALL.md](docs/PORTAINER_INSTALL.md).

## Data and privacy boundaries

The repository contains application code, deployment templates, tests, and
synthetic documentation demos. The following stay on the installation host:

- ROM files and PC installers.
- Downloaded artwork, screenshots, and other media.
- Database and cache contents.
- NAS paths.
- Provider API keys, passwords, and authentication secrets.
- User accounts and personal library metadata.

## Local development

Read [CLAUDE.md](CLAUDE.md) for repository rules and the canonical Linux
development environment.

For the development stack:

```bash
cp env.template .env
docker compose up -d
```

The production-style Portainer stack is separate from the development compose
file. Use the Portainer files for a NAS deployment and keep their environment
values outside Git.

## Troubleshooting

- If Portainer reports a required-variable error, check the variable names and
  placeholders without exposing the secret in logs or screenshots.
- If romm-db is unhealthy, verify the database passwords and persistent volume.
- If the library is empty, verify that the path exists on the NAS host visible
  to Docker, not only on a workstation.
- If metadata search is unavailable, verify only the credentials for the
  selected provider. The base installation remains usable without metadata
  providers.
- If an update appears unchanged, confirm that Portainer pulled the intended
  Git revision and recreated the application container.

## Repository links

- [Portainer installation guide](docs/PORTAINER_INSTALL.md)
- [Portainer stack](examples/portainer-stack.yml)
- [Portainer environment template](examples/portainer.env.example)
- [Deployment verification script](scripts/verify-portainer-stack.sh)
- [Developer guide](CLAUDE.md)
