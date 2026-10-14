#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
stack="${repo_root}/examples/portainer-stack.yml"
env_file="${repo_root}/examples/portainer.env.example"
entrypoint="${repo_root}/docker/init_scripts/docker-entrypoint.sh"

command -v docker >/dev/null || {
	echo "docker is required" >&2
	exit 1
}
test -f "${stack}" && test -f "${env_file}" && test -f "${entrypoint}"

rendered="$(mktemp)"
trap 'rm -f "${rendered}"' EXIT
docker compose --env-file "${env_file}" -f "${stack}" config >"${rendered}"

! grep -Fq '/home/d1sk/romm' "${rendered}"
! grep -Fq 'Docker/Media' "${rendered}"
! grep -Fq '/path/to/' "${rendered}"
grep -Fq 'target: /romm/library' "${rendered}"
grep -Fq 'read_only: true' "${rendered}"
grep -Fq 'condition: service_healthy' "${rendered}"
grep -Fq 'ROMM_AUTH_SECRET_KEY' "${rendered}"
grep -Fq 'target: /var/lib/mysql' "${rendered}"
grep -Fq 'target: /romm/resources' "${rendered}"
grep -Fq 'target: /redis-data' "${rendered}"
grep -Fq 'context: /' "${rendered}" || grep -Fq 'context: ..' "${stack}"
grep -Fq 'pc-game-download-portal:portainer' "${env_file}"
! grep -Fq 'rommapp/romm:phase27' "${env_file}"
grep -Fq 'ROMM_LIBRARY_PATH' "${env_file}"
grep -Fq 'ROMM_ASSETS_PATH' "${env_file}"
grep -Fq 'ROMM_CONFIG_PATH' "${env_file}"
grep -Fq 'https://github.com/D1skanime/pc-game-download-portal.git' "${repo_root}/examples/README.md"
grep -Fq 'https://github.com/D1skanime/pc-game-download-portal.git' "${repo_root}/docs/PORTAINER_INSTALL.md"
! grep -Fq 'https://github.com/D1skanime/pc-romm.git' "${repo_root}/README.md" "${repo_root}/examples/README.md" "${repo_root}/docs/PORTAINER_INSTALL.md"

# The production image's existing entrypoint remains the only secret/bootstrap
# adapter. These assertions prevent a future stack edit from bypassing it.
grep -Fq 'grep "_FILE$"' "${entrypoint}"
grep -Fq 'Both ${var_name_no_suffix} and ${var_name}' "${entrypoint}"
grep -Fq 'exec "$@"' "${entrypoint}"

if git -C "${repo_root}" ls-files | grep -E '(^|/).env(.|$)' >/dev/null; then
	echo "tracked env file detected" >&2
	exit 1
fi

for pattern in '(^|/)Games(/|$)' '(^|/)Docker/Media(/|$)'; do
	if git -C "${repo_root}" ls-files | grep -E "${pattern}" >/dev/null; then
		echo "tracked runtime library/media path detected: ${pattern}" >&2
		exit 1
	fi
done

echo "Portainer stack startup and persistence contract passed"
