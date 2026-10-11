# Portainer deployment

Use portainer-stack.yml from Portainer's Stacks -> Add stack -> Git
repository flow. Select the main branch and set the compose path to
examples/portainer-stack.yml.

Copy the variables from portainer.env.example into Portainer's environment
section, replace every placeholder, and create the host directories before
deploying. ROMs and media stay on the NAS and are mounted into the container;
they are never loaded from GitHub.

The stack builds the checked-out fork with docker/Dockerfile. Set ROMM_IMAGE
only when intentionally using a compatible prebuilt image. Optional metadata
provider credentials may remain blank; the corresponding provider is then
unavailable but installation remains valid.

Required operator values:

- ROMM_LIBRARY_PATH: existing ROM/library root, mounted read-only.
- ROMM_ASSETS_PATH: writable saves/states/assets directory.
- ROMM_CONFIG_PATH: writable persistent config directory.
- ROMM_DB_PASSWORD, ROMM_DB_ROOT_PASSWORD, ROMM_AUTH_SECRET_KEY: unique
  secrets that belong in Portainer, never in Git.

After deployment, wait for both services to become healthy, open the configured
HTTP port, and complete the first-login flow.
