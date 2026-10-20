#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
stack="${repo_root}/examples/portainer-stack.yml"
env_file="${repo_root}/examples/portainer.env.example"
entrypoint="${repo_root}/docker/init_scripts/docker-entrypoint.sh"
for command_name in docker git grep; do
	command -v "${command_name}" >/dev/null || {
		echo "${command_name} is required" >&2
		exit 1
	}
done
test -f "${stack}" && test -f "${env_file}" && test -f "${entrypoint}"
rendered="$(mktemp)"
trap 'rm -f "${rendered}"' EXIT
docker compose --env-file "${env_file}" -f "${stack}" config >"${rendered}"
assert_rendered() {
	grep -Fq -- "$1" "${rendered}" || {
		echo "missing rendered-stack assertion: $1" >&2
		exit 1
	}
}
assert_absent() {
	if grep -Fq -- "$1" "${rendered}"; then
		echo "forbidden rendered-stack reference: $1" >&2
		exit 1
	fi
}
grep -Eq '^name: pgdp$' "${rendered}"
grep -Eq '^  pgdp:$' "${rendered}"
grep -Eq '^  pgdp-db:$' "${rendered}"
assert_rendered 'container_name: pgdp'
assert_rendered 'container_name: pgdp-db'
assert_rendered 'image: pc-game-download-portal:portainer'
assert_rendered 'DB_HOST: pgdp-db'
assert_rendered 'DB_NAME: pgdp'
assert_rendered 'DB_USER: pgdp-user'
assert_rendered 'MARIADB_DATABASE: pgdp'
assert_rendered 'MARIADB_USER: pgdp-user'
assert_rendered 'target: /var/lib/mysql'
assert_rendered 'target: /romm/resources'
assert_rendered 'target: /redis-data'
assert_rendered 'target: /romm/library'
assert_rendered 'target: /romm/assets'
assert_rendered 'target: /romm/config'
assert_rendered 'read_only: true'
assert_rendered 'condition: service_healthy'
assert_rendered 'ROMM_AUTH_SECRET_KEY'
assert_rendered 'healthcheck:'
grep -Fq 'context: ..' "${stack}"
for key in PGDP_PROJECT_NAME PGDP_IMAGE PGDP_LIBRARY_PATH PGDP_ASSETS_PATH PGDP_CONFIG_PATH; do
	grep -Fq "${key}=" "${env_file}"
done
grep -Fq 'https://github.com/D1skanime/pc-game-download-portal.git' "${repo_root}/examples/README.md"
grep -Fq 'https://github.com/D1skanime/pc-game-download-portal.git' "${repo_root}/docs/PORTAINER_INSTALL.md"
for forbidden in '/home/d1sk/romm' 'romm_mysql_data' 'romm_resources' 'romm_redis_data' 'romm-db-dev' 'rommapp/romm:phase27' 'Docker/Media' '/path/to/'; do
	assert_absent "${forbidden}"
done
if git -C "${repo_root}" grep -n -I -E 'ROMM_(DB_PASSWORD|LIBRARY_PATH|ASSETS_PATH|CONFIG_PATH|HTTP_PORT)' -- . ':!scripts/verify-pgdp-naming.sh' ':!scripts/verify-portainer-stack.sh' ':!.planning/**' >/dev/null; then
	echo "legacy PGDP operator alias detected" >&2
	exit 1
fi
if git -C "${repo_root}" ls-files | grep -E '(^|/)\.env$' >/dev/null; then
	echo "tracked .env file detected" >&2
	exit 1
fi
for pattern in '(^|/)Games(/|$)' '(^|/)Docker/Media(/|$)'; do
	if git -C "${repo_root}" ls-files | grep -E "${pattern}" >/dev/null; then
		echo "tracked runtime library/media path detected: ${pattern}" >&2
		exit 1
	fi
done
grep -Fq 'grep "_FILE$"' "${entrypoint}"
# shellcheck disable=SC2016 # Match the literal entrypoint variable names.
grep -Fq 'Both ${var_name_no_suffix} and ${var_name}' "${entrypoint}"
grep -Fq 'exec "$@"' "${entrypoint}"
echo "PGDP Portainer render, parity, mount, secret, and hygiene contract passed"
