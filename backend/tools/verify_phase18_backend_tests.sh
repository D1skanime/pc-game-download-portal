#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

test_database=""
base_path=""
database_user=""
root_password=""
first_failure=0

compose_environment() {
	local name="$1"
	local fallback="$2"
	local value

	value="$(
		docker compose config --environment |
			awk -F= -v name="${name}" '$1 == name { sub(/^[^=]*=/, ""); print; exit }'
	)"

	printf '%s' "${value:-${fallback}}"
}

# shellcheck disable=SC2329
cleanup() {
	local status=$?

	if [[ ${first_failure} -eq 0 && ${status} -ne 0 ]]; then
		first_failure="${status}"
	fi

	if [[ ${test_database} =~ ^phase18_tests_[0-9]+_[0-9]+$ ]]; then
		docker compose exec -T romm-db-dev \
			mariadb -u root "-p${root_password}" \
			-e "REVOKE ALL PRIVILEGES ON \`${test_database}\`.* FROM '${database_user}'@'%'; DROP DATABASE IF EXISTS \`${test_database}\`" \
			>/dev/null 2>&1 || true
	fi

	if [[ ${base_path-} =~ ^/tmp/phase18-backend-tests-[0-9]+_[0-9]+$ ]]; then
		docker compose exec -T romm-dev rm -rf "${base_path}" >/dev/null 2>&1 || true
	fi

	trap - EXIT
	exit "${first_failure}"
}

trap cleanup EXIT

database_user="$(compose_environment DB_USER romm)"
database_password="$(compose_environment DB_PASSWD romm)"
root_password="$(compose_environment DB_ROOT_PASSWD rootpassword)"
suffix="$(date +%s)_${RANDOM}"
test_database="phase18_tests_${suffix}"
base_path="/tmp/phase18-backend-tests-${suffix}"
auth_key="phase18-backend-tests-${suffix}"

if [[ ! ${test_database} =~ ^phase18_tests_[0-9]+_[0-9]+$ ]]; then
	printf 'Generated test schema name is invalid.\n' >&2
	exit 1
fi

if [[ ! ${database_user} =~ ^[A-Za-z0-9_]+$ ]]; then
	printf 'Compose database username contains unsupported characters.\n' >&2
	exit 1
fi

docker compose exec -T romm-db-dev \
	mariadb -u root "-p${root_password}" \
	-e "CREATE DATABASE \`${test_database}\`; GRANT ALL PRIVILEGES ON \`${test_database}\`.* TO '${database_user}'@'%'; FLUSH PRIVILEGES" \
	>/dev/null

docker compose exec -T romm-dev mkdir -p "${base_path}/library"

pytest_environment="$(printf '%s\n' \
	"ROMM_BASE_PATH=${base_path}" \
	'DB_HOST=romm-db-dev' \
	'DB_PORT=3306' \
	"DB_NAME=${test_database}" \
	"DB_USER=${database_user}" \
	"DB_PASSWD=${database_password}" \
	'ROMM_DB_DRIVER=mariadb' \
	'IGDB_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
	'IGDB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
	'RETROACHIEVEMENTS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
	'MOBYGAMES_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
	'SCREENSCRAPER_USER=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
	'SCREENSCRAPER_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
	'STEAMGRIDDB_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' \
	'LAUNCHBOX_API_ENABLED=true' \
	"ROMM_AUTH_SECRET_KEY=${auth_key}" \
	'ENABLE_RESCAN_ON_FILESYSTEM_CHANGE=true' \
	'ENABLE_SCHEDULED_RESCAN=true' \
	'ENABLE_SCHEDULED_UPDATE_SWITCH_TITLEDB=true' \
	'ENABLE_SCHEDULED_UPDATE_LAUNCHBOX_METADATA=true' \
	'LOGLEVEL=DEBUG' \
	'DEV_MODE=false' \
	'OIDC_ENABLED=false')"

set +e
docker compose exec -T --workdir /app/backend romm-dev env \
	ROMM_BASE_PATH="${base_path}" \
	DB_HOST=romm-db-dev \
	DB_PORT=3306 \
	DB_NAME="${test_database}" \
	DB_USER="${database_user}" \
	DB_PASSWD="${database_password}" \
	ROMM_DB_DRIVER=mariadb \
	ROMM_AUTH_SECRET_KEY="${auth_key}" \
	uv run pytest -o "env=${pytest_environment}" \
	tests/adapters/services/test_steam.py \
	tests/handler/metadata/test_steam_handler.py \
	tests/handler/metadata/test_steam_merge.py \
	tests/handler/metadata/test_pc_match_handler.py \
	tests/endpoints/roms/test_pc_metadata.py \
	tests/endpoints/sockets/test_scan.py \
	tests/models/test_pc_igdb_metadata.py \
	tests/handler/database/test_pc_igdb_enrichment.py \
	tests/handler/test_scan_handler.py -q
pytest_status=$?
set -e

if [[ ${pytest_status} -ne 0 ]]; then
	first_failure="${pytest_status}"
fi

exit "${pytest_status}"
