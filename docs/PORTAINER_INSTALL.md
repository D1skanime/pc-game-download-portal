# RomM fork installation with Portainer

This repository contains the application code and a Portainer stack template.
ROM files, downloaded media, database contents, host paths, and credentials are
operator-owned data and are not part of GitHub.

## Prerequisites

- Portainer with Docker Compose stack support
- A NAS directory for the read-only ROM library
- Writable directories for RomM assets and configuration
- Enough space for the Docker build and MariaDB volume
- Optional metadata-provider accounts and API keys

## Deploy from GitHub

1. In Portainer, choose Stacks, then Add stack, then Git repository.
2. Repository URL: https://github.com/D1skanime/pc-romm.git
3. Branch/reference: main
4. Compose path: examples/portainer-stack.yml
5. Add the variables from examples/portainer.env.example in Portainer's
   environment-variable section.
6. Replace every replace-with placeholder and set the three NAS paths.
7. Deploy the stack.

The Git-based flow is intentional: the stack builds the checked-out fork with
docker/Dockerfile, so the deployed image contains the code from main. If a
compatible prebuilt image is intentionally used, set ROMM_IMAGE to that image;
the image must contain the same application contract.

## Required variables

| Variable              | Meaning                                                 |
| --------------------- | ------------------------------------------------------- |
| ROMM_LIBRARY_PATH     | Existing ROM/library root. Mounted read-only.           |
| ROMM_ASSETS_PATH      | Writable uploaded saves, states, and assets directory.  |
| ROMM_CONFIG_PATH      | Writable persistent config directory.                   |
| ROMM_DB_PASSWORD      | MariaDB application-user password.                      |
| ROMM_DB_ROOT_PASSWORD | MariaDB root password, different from the app password. |
| ROMM_AUTH_SECRET_KEY  | Long random RomM auth key.                              |
| ROMM_HTTP_PORT        | NAS port mapped to RomM's port 8080.                    |
| TZ                    | Container timezone, normally UTC.                       |

Create unique values, for example:

    openssl rand -hex 32

Enter generated values directly into Portainer or use Portainer/Docker secrets
where the deployment environment supports secret files. Never put real values
in portainer.env.example, a Git commit, an issue, or a screenshot.

## Optional metadata providers

The provider variables may remain empty. RomM still starts and the provider is
simply unavailable until its credentials are supplied. Add only the providers
you actually use:

- SCREENSCRAPER_USER and SCREENSCRAPER_PASSWORD
- RETROACHIEVEMENTS_API_KEY
- STEAMGRIDDB_API_KEY
- HASHEOUS_API_ENABLED

Missing provider credentials are configuration gaps, not installation failures.

## Storage and persistence

Create the three host directories before deployment. The ROM library is mounted
read-only so scanning cannot rewrite the source archive. RomM resources,
Redis-compatible cache data, assets, config, and MariaDB use persistent Docker
volumes or writable host mounts as shown in the stack.

Do not mount the NAS ROM directory over /romm/resources or /romm/assets. Those
locations have different ownership and write semantics.

## First start and updates

Wait until both romm and romm-db are healthy. Open the configured HTTP port and
complete the first-login flow. The existing production entrypoint performs its
normal environment preparation and startup/migration path; no manual database
schema command is required for a normal first boot.

For an update, pull the desired main revision in Portainer and redeploy the Git
stack. Keep the MariaDB and resource volumes. Take a database backup before
major upgrades and never replace the ROM library with a Git checkout.

## Troubleshooting

- A required-variable error means Portainer did not provide one of the required
  values; the error must not include the secret itself.
- If romm-db is unhealthy, inspect database logs and verify the two passwords
  were entered consistently.
- If the library is empty, verify ROMM_LIBRARY_PATH is the NAS path visible to
  the Docker daemon, not a path from a workstation.
- If metadata search is unavailable, verify only that provider's credentials;
  the base installation remains usable without providers.

## Safety check

From a Linux checkout, run:

    bash scripts/verify-portainer-stack.sh

It renders the stack with the sanitized example values and rejects developer
paths, tracked env files, and tracked Games/Docker/Media runtime data.
