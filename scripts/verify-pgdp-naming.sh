#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
contract="${repo_root}/docs/zockarchive-branding-contract.md"
for command_name in git grep find; do
	command -v "${command_name}" >/dev/null || {
		echo "${command_name} is required" >&2
		exit 1
	}
done
test -s "${contract}"
grep -Fq '# ZockArchive branding and compatibility contract' "${contract}"
grep -Fq '## Retained compatibility' "${contract}"
surface_count=0
required_count=0
# Exact path and line records distinguish compatibility from visible identity.
mapfile -t contract_records <"${contract}"
for record in "${contract_records[@]}"; do
	IFS='|' read -r kind path value <<<"${record}"
	case "${kind}" in
	require)
		test -f "${repo_root}/${path}"
		grep -Fq -- "${value}" "${repo_root}/${path}" || {
			echo "current identity assertion failed: ${path}" >&2
			exit 1
		}
		required_count=$((required_count + 1))
		;;
	surface)
		test -f "${repo_root}/${path}"
		surface_count=$((surface_count + 1))
		while IFS= read -r line; do
			grep -Fxq -- "retain|${path}|${line}" "${contract}" || {
				echo "unclassified retained name: ${path}:${line}" >&2
				exit 1
			}
		done < <(grep -i -E 'romm|pgdp|pc-game-download-portal' "${repo_root}/${path}" || true)
		;;
	*) continue ;;
	esac
done
test "${surface_count}" -gt 0
test "${required_count}" -gt 0
test ! -e "${repo_root}/frontend/src/RomM.vue"
legacy_logo="$(find "${repo_root}/frontend/assets/logos" -maxdepth 1 -type f -iname 'romm_logo*' -print -quit)"
test -z "${legacy_logo}"
if git -C "${repo_root}" grep -n -I -E 'ROMM_(DB_PASSWORD|LIBRARY_PATH|ASSETS_PATH|CONFIG_PATH|HTTP_PORT)' -- . ':!scripts/verify-pgdp-naming.sh' ':!scripts/verify-portainer-stack.sh' ':!.planning/**' >/dev/null; then
	echo "legacy operator alias detected outside the verifier allowlist" >&2
	exit 1
fi
product_owned_paths=('examples/portainer-stack.yml' 'examples/portainer.env.example' 'examples/docker-compose.example.yml' 'docker/Dockerfile' 'docker/init_scripts' 'frontend/index.html' 'frontend/src/PGDP.vue' 'env.template' 'pyproject.toml')
if git -C "${repo_root}" grep -n -I -E 'Docker/Media|/home/d1sk/romm|romm_(mysql|resources|redis)_data|romm-db-dev' -- "${product_owned_paths[@]}"; then
	echo "live-state or old deployment identity detected in product-owned paths" >&2
	exit 1
fi
echo "ZockArchive tracked identity and retained-name contract passed"
