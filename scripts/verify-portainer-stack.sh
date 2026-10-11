#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
stack="${repo_root}/examples/portainer-stack.yml"
env_file="${repo_root}/examples/portainer.env.example"

command -v docker >/dev/null || {
	echo "docker is required" >&2
	exit 1
}
test -f "${stack}" && test -f "${env_file}"

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
grep -Fq 'ROMM_LIBRARY_PATH' "${env_file}"
grep -Fq 'ROMM_ASSETS_PATH' "${env_file}"
grep -Fq 'ROMM_CONFIG_PATH' "${env_file}"

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

echo "Portainer stack contract passed"
