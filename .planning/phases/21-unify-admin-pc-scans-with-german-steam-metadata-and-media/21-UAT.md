# Phase 21 UAT

Fixture: isolated Witcher-style PC fixture, planned identity `The Witcher.exe`

Environment authorization: BLOCKED. No authorized isolated browser and MariaDB
environment was available. The configured local test endpoint at `127.0.0.1:3306`
refused connections. Docker Compose, NAS mounts, Team4s services, and external
source-library paths were not used.

Source snapshot: Not run in a browser fixture. The isolated static source-safety
check passed before and after scan-path integration:
`cd backend && uv run pytest tests/integration/test_scan_source_immutability.py -x`
(2 passed).

New-game scan: BLOCKED pending the authorized isolated browser/database fixture.
German text and automatic placement on unclaimed overview/background surfaces were
not claimed as verified.

Existing UPDATE/COMPLETE refresh: BLOCKED pending the same authorized fixture.

Manual text/overview/background protection: BLOCKED pending the same authorized
fixture.

Phase 20 Media visibility/editability: BLOCKED pending the same authorized
browser fixture.

Outcome: BLOCKED

Evidence: The focused test command that includes database-backed scan tests cannot
start because MariaDB at `127.0.0.1:3306` is unavailable. No replacement
infrastructure was created. Resume only with an authorized isolated browser plus
disposable database environment, using no external source-library path.
