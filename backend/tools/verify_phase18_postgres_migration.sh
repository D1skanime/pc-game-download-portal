#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

postgres_container=""
first_failure=0

cleanup() {
	local status=$?

	if [[ $first_failure -eq 0 && $status -ne 0 ]]; then
		first_failure="$status"
	fi

	if [[ -n $postgres_container ]]; then
		docker rm -f "$postgres_container" >/dev/null 2>&1 || true
	fi

	trap - EXIT
	exit "$first_failure"
}

trap cleanup EXIT

required_compose_environment() {
	local name="$1"
	local value

	value="$(
		docker compose config --environment |
			awk -F= -v name="$name" '$1 == name { sub(/^[^=]*=/, ""); print; exit }'
	)"

	if [[ -z $value ]]; then
		printf 'Missing required Compose environment variable: %s\n' "$name" >&2
		return 1
	fi

	printf '%s' "$value"
}

postgres_user="$(required_compose_environment POSTGRES_USER)"
postgres_password="$(required_compose_environment POSTGRES_PASSWORD)"
compose_project="$(
	docker compose config --format json |
		awk -F'"' '/^[[:space:]]*"name"[[:space:]]*:/ { print $4; exit }'
)"

if [[ -z $compose_project ]]; then
	printf 'Could not determine the canonical Compose project name.\n' >&2
	exit 1
fi

mapfile -t compose_networks < <(
	docker network ls \
		--filter "label=com.docker.compose.project=$compose_project" \
		--filter 'label=com.docker.compose.network=default' \
		--format '{{.Name}}'
)

if [[ ${#compose_networks[@]} -ne 1 ]]; then
	printf 'Expected exactly one canonical Compose default network, found %s.\n' \
		"${#compose_networks[@]}" >&2
	exit 1
fi

suffix="$(date +%s)-$$"
postgres_container="phase18-postgres-$suffix"
postgres_database="phase18_migration_$suffix"

docker run \
	--detach \
	--name "$postgres_container" \
	--network "${compose_networks[0]}" \
	--env "POSTGRES_USER=$postgres_user" \
	--env "POSTGRES_PASSWORD=$postgres_password" \
	--env "POSTGRES_DB=$postgres_database" \
	postgres:16-alpine >/dev/null

postgres_ready=0
for attempt in $(seq 1 30); do
	if docker exec "$postgres_container" \
		pg_isready -q -U "$postgres_user" -d "$postgres_database"; then
		postgres_ready=1
		break
	fi

	sleep 1
done

if [[ $postgres_ready -ne 1 ]]; then
	printf 'Disposable PostgreSQL container did not become ready within 30 seconds.\n' >&2
	exit 1
fi

run_alembic() {
	docker compose exec -T --workdir /app/backend romm-dev env \
		ROMM_DB_DRIVER=postgresql \
		DB_HOST="$postgres_container" \
		DB_PORT=5432 \
		DB_NAME="$postgres_database" \
		DB_USER="$postgres_user" \
		DB_PASSWD="$postgres_password" \
		ROMM_AUTH_SECRET_KEY=phase18-postgres-migration-verifier \
		uv run alembic "$@"
}

run_alembic heads
run_alembic upgrade head
run_alembic downgrade -1
run_alembic upgrade head
