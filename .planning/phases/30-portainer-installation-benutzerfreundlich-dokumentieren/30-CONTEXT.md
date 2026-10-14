# Phase 30 Context

## Objective

Make the Git-based Portainer installation understandable and reproducible for operators on Synology, QNAP, and standard Linux hosts, without changing the application's storage architecture or committing secrets and runtime data.

## User-provided acceptance intent

- Explain the Portainer stack, build context, image behavior, volumes, read-only library mount, ports, persistence, and required configuration.
- Document every operator-facing environment variable, including secure password generation with openssl rand -hex 32.
- Create a complete German installation guide using Swiss spelling.
- Cover NAS preparation, Git-based Portainer deployment, first start, functional checks, updates, backups, and rollback.
- Explain path and permission differences across Synology, QNAP, and Linux without inventing universal host paths.
- Cross-check all documentation against the actual Compose stack, Dockerfile, entrypoint, and supported runtime behavior.
- Update README links to the current repository and the complete guide.
- Keep application behavior unchanged except for technical corrections required to make the installation contract truthful.

## Constraints

- Canonical implementation and planning checkout: /home/d1sk/pc-game-download-portal on team4s-linux.
- Do not commit real credentials, personal NAS paths, ROMs, media, database dumps, or runtime artifacts.
- Keep the external library read-only.
- Keep the Portainer stack separate from the development Compose stack.
- Do not claim a clean deployment test unless it was actually run. Record blocked or unavailable infrastructure explicitly.
