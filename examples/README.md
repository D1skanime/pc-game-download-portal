# Portainer deployment examples

Use portainer-stack.yml from Portainer's Stacks > Add stack > Git repository
flow.

Repository:

    https://github.com/D1skanime/pc-game-download-portal.git

Compose path:

    examples/portainer-stack.yml

Copy the variables from portainer.env.example into Portainer's environment
section. Replace placeholders, create the host directories first, and keep the
source game library readable by the Docker daemon but mounted read-only in the
container.

The stack builds the checked-out Git fork with docker/Dockerfile. The
PGDP_IMAGE value is the tag for that build. Change it only when intentionally
using a compatible prebuilt image. Optional provider credentials may remain
blank.

See docs/PORTAINER_INSTALL.md for the complete German installation guide.
