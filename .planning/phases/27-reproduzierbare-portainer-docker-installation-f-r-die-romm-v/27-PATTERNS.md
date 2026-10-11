# Phase 27 Existing Patterns

| Concern             | Existing pattern                                                  | Reuse rule                                                                 |
| ------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Production compose  | examples/docker-compose.example.yml                               | Extend or derive the portable stack; do not copy dev-only absolute mounts. |
| Development compose | docker-compose.yml                                                | Keep it for local hot reload; never use it as the Portainer contract.      |
| Application startup | docker/init_scripts/docker-entrypoint.sh                          | Reuse *_FILE loading, conflict checks, defaults, and envsubst.             |
| Persistent data     | Named DB/cache/resource volumes plus library/assets/config mounts | Make host paths configurable and preserve read-only library semantics.     |
| Provider config     | Existing provider environment variables                           | Keep providers optional and make missing credentials explicit.             |
| Verification        | Existing Docker compose and Linux test commands                   | Add render/secret/health checks around the install path.                   |
| Documentation       | Root README and examples templates                                | Link one canonical Portainer path with a safe env template.                |

## Anti-patterns

- Committing env files, database dumps, ROMs, screenshots, covers, generated media, or real keys.
- Reusing /home/d1sk/romm or another developer-specific absolute path.
- Adding an installer schema or alternate media/storage service.
- Treating container start alone as proof of a working installation.
