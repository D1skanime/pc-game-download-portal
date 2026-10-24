# ZockArchive (ZA)

ZockArchive is a self-hosted PC and console game library, metadata manager and download portal. It connects an existing archive to a catalog without reorganizing or changing source files or directories.

- Register external read-only libraries and platform-to-storage mappings.
- Browse PC main games, installers, updates, DLC, patches, manuals and optional files.
- Match metadata with IGDB, Steam and other optional providers.
- Manage screenshots, artwork, backgrounds and uploaded soundtracks.
- Download selected PC components using verified manifests, resumable browser transfers and download history.
- Browse console libraries and play supported titles through the existing browser players.

## Install and operate

Use the Git-source [Portainer stack](examples/portainer-stack.yml) and [environment template](examples/portainer.env.example). The [English installation guide](docs/PORTAINER_INSTALL.md) covers host paths, secrets, first startup, providers, backups, updates and rollback.

Repository: <https://github.com/D1skanime/zockarchive>
Releases: <https://github.com/D1skanime/zockarchive/releases>
Issues: <https://github.com/D1skanime/zockarchive/issues>

Portainer builds the selected Git revision with `docker/Dockerfile`. The local image tag remains `pc-game-download-portal:portainer` and can be overridden with `PGDP_IMAGE`. This local build tag is not evidence of a published registry image. Registry aliases and external accessibility are described in the installation guide.

Keep the original archive mounted at `/romm/library:ro`. Store database, resources, Redis data, assets and configuration separately. Preserve existing stack names, host paths and volumes when updating.

## Compatibility

The product name is ZockArchive, abbreviated ZA. Existing `PGDP_*` and `ROMM_*` keys, `pgdp` services/project defaults, database names, persistent volumes, storage paths, browser/session/cache keys and native desktop identifiers remain compatibility contracts.

The canonical development checkout remains `/home/d1sk/pc-game-download-portal` on `team4s-linux`. A repository URL change does not move that directory or migrate packages, credentials, data or Portainer settings.

## Documentation and development

- [Developer setup](DEVELOPER_SETUP.md)
- [Contributor guide](CONTRIBUTING.md), including required AI-assistance disclosure
- [Backend architecture](docs/BACKEND_ARCHITECTURE.md)
- [Frontend architecture](docs/FRONTEND_ARCHITECTURE.md)
- [External read-only library operations](docs/external-read-only-library-operations.md)
- [Repository and execution rules](CLAUDE.md)

The Windows checkout is a coordination/reference workspace. Implementation, GSD, tests and commits run in the verified canonical Linux checkout. Synthetic proof fixtures must never be replaced with production NAS or user data.

## Workflow demonstrations

These recordings use synthetic data without ROM files, private accounts, media or credentials. They may show earlier product artwork or copy.

| PC download controls                                               | Media and artwork workflow                                             |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| ![PC download controls](docs/screenshots/pc-download-controls.gif) | ![Media and artwork workflow](docs/screenshots/media-artwork-flow.gif) |

## Assets and verification limits

Current navigation, authentication and bootstrap use text identity. Final supplied artwork is pending. App icons, public/PWA icons and desktop installer icons have separate owners, documented in the frontend architecture and desktop README. Native installer identity remains unchanged for upgrade compatibility.

Source and isolated tests do not establish live Synology/QNAP/Portainer acceptance, physical controller acceptance or registry package availability. These checks require their respective environments and authorization.

## Origin and license

ZockArchive derives from [upstream RomM](https://github.com/rommapp/romm), a self-hosted ROM manager and player. Upstream documentation and provider integrations remain attributed to their owners. Upstream donation and community accounts do not belong to ZockArchive.

The project retains the [AGPL license](LICENSE), copyright notices, author attribution and source history. Historical planning and decision records retain the names used when written.
