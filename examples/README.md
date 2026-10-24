# ZockArchive deployment examples

Use `portainer-stack.yml` from Portainer's **Stacks > Add stack > Git repository** flow.

- Repository: <https://github.com/D1skanime/zockarchive.git>
- Reference: `main` or a reviewed release revision
- Compose path: `examples/portainer-stack.yml`

Copy `portainer.env.example` into Portainer's environment section. Replace placeholders and create the host directories first. The Docker daemon must be able to read the source archive, mounted read-only in the container.

The stack builds the selected Git revision using `docker/Dockerfile`. `PGDP_IMAGE` defaults to the existing local tag `pc-game-download-portal:portainer`. It is not an advertised public image. Preserve project, service, database, volume and host-path overrides.

`docker-compose.example.yml` is a manual prebuilt-image example. Its local `pc-game-download-portal:latest` tag must already be built or supplied by an operator who verified its provenance. It is not a verified registry publication.

Optional provider credentials may remain blank. ScreenScraper source builds need the two `PGDP_SCREENSCRAPER_DEV_*` build inputs as well as personal credentials.

See the [English installation guide](../docs/PORTAINER_INSTALL.md) for retained operator keys, backups, updates and external verification limits.
