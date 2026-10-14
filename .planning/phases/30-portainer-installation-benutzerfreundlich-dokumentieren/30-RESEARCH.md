# Phase 30 Research

## Repository evidence

- Portainer files exist at examples/portainer-stack.yml, examples/portainer.env.example, examples/README.md, and docs/PORTAINER_INSTALL.md.
- The current guide and README still reference the historical repository URL https://github.com/D1skanime/pc-romm.git. The canonical remote is https://github.com/D1skanime/pc-game-download-portal.git.
- The stack uses a Git-relative build context of .. from examples/portainer-stack.yml and docker/Dockerfile with target full-image.
- The application service mounts the library read-only at /romm/library, writable assets at /romm/assets, writable config at /romm/config, named resources at /romm/resources, and named Redis data at /redis-data.
- MariaDB persists at the named volume target /var/lib/mysql and is gated by a healthcheck before the application starts.
- The published application port is host ROMM_HTTP_PORT to container port 8080.
- Required runtime values are enforced by Compose interpolation for library, assets, config, database password, database root password, and auth secret.
- Optional metadata provider values may be blank. The application reads STEAMGRIDDB_API_KEY, IGDB_CLIENT_ID, and IGDB_CLIENT_SECRET; IGDB credentials are issued through a Twitch Developer application.
- The current ENV example uses /srv/romm paths and phase27 as the image default. Those values need explicit explanation and a safe fork-build story.
- scripts/verify-portainer-stack.sh already renders the stack and checks read-only mounts, persistence targets, required variables, tracked env files, and developer/runtime path leaks.
- The production entrypoint handles environment preparation and *_FILE behavior, so the guide should point operators to Portainer variables or supported secrets instead of duplicating bootstrap logic.

## Planning implications

1. The stack comments and ENV template must explain the distinction between build context, build target, image tag, and an intentionally selected prebuilt image.
2. The default path examples must be visibly illustrative, with Synology examples called examples rather than universal defaults.
3. The guide must separate container paths from host paths and explain that NAS paths must be visible to the Docker daemon.
4. Verification must include rendered Compose config, repository-link consistency, secret/path safety, and a documented fresh-clone or explicit blocker result.
5. No application feature work is needed for the documentation scope.
6. Provider onboarding must explain where operators obtain credentials:
   SteamGridDB supplies a personal API key in its account/API area; IGDB
   credentials come from a Twitch Developer application and consist of
   IGDB_CLIENT_ID plus IGDB_CLIENT_SECRET. Secrets must remain outside Git.
