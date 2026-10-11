#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

for service in romm-dev romm-db-dev romm-valkey-dev; do
	docker compose ps --status running "${service}" >/dev/null
done

bash backend/tools/verify_phase18_backend_tests.sh
