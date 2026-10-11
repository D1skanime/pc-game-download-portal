# Phase 27 Clean-Install UAT

Date: 2026-10-11
Environment: canonical Linux checkout /home/d1sk/romm, Docker Compose, disposable project phase27-uat

## Scenarios

| Scenario                                   | Result | Evidence                                                                                                                                                   |
| ------------------------------------------ | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Render stack with operator-style variables | PASS   | docker compose --env-file /tmp/phase27-uat/env -f examples/portainer-stack.yml config --quiet                                                              |
| Build the fork image from Git checkout     | PASS   | docker compose --env-file examples/portainer.env.example -f examples/portainer-stack.yml build --pull=false romm completed with image rommapp/romm:phase27 |
| Start database and application             | PASS   | Disposable MariaDB became healthy; application healthcheck became healthy                                                                                  |
| Existing startup/migration path            | PASS   | Application container started through the repository image entrypoint and reached healthy state; no alternate bootstrap was introduced                     |
| Configured library bind mount              | PASS   | Temporary operator library path was supplied through ROMM_LIBRARY_PATH and rendered as /romm/library:ro                                                    |
| Persistent managed state contract          | PASS   | Stack used named volumes for database, resources, and Redis state; disposable project was torn down after the run                                          |
| Optional provider credentials              | PASS   | Provider variables were blank in the synthetic UAT env; startup still reached healthy state                                                                |
| Secret safety                              | PASS   | No real credentials, ROMs, media, or database contents were used or added to Git                                                                           |

## Commands and cleanup

The test used synthetic values and temporary paths under /tmp/phase27-uat, with HTTP port 18080 and compose project phase27-uat. After the health checks, docker compose ... down -v --remove-orphans removed only that named disposable stack and its volumes.

Browser visual evidence was not required for this infrastructure phase; the authoritative service smoke check was the container healthcheck. The public installation path is documented in docs/PORTAINER_INSTALL.md.

## Conclusion

Clean-install UAT passed for the documented Git-to-Portainer contract. Operators must still supply their own host paths, database/auth secrets, and any metadata-provider keys they want to use.
