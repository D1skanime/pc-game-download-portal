#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
inventory="${repo_root}/.planning/phases/32-pgdp-namensumstellung-fresh-installation/32-NAMING-INVENTORY.md"
for command_name in git grep find; do
	command -v "${command_name}" >/dev/null || {
		echo "${command_name} is required" >&2
		exit 1
	}
done
test -s "${inventory}"
grep -Fq 'PGDP_*' "${inventory}"
grep -Fq 'sole product-owned operator wrapper surface' "${inventory}"
grep -Fq 'Retained-name allowlist' "${inventory}"
grep -Fq '/romm' "${inventory}"
grep -Fq 'Disposition counts' "${inventory}"
for required_file in "${repo_root}/examples/portainer-stack.yml" "${repo_root}/examples/portainer.env.example" "${repo_root}/frontend/index.html" "${repo_root}/frontend/src/PGDP.vue" "${repo_root}/frontend/public/site.webmanifest"; do
	test -f "${required_file}" || {
		echo "required PGDP surface is missing: ${required_file}" >&2
		exit 1
	}
done
test ! -e "${repo_root}/frontend/src/RomM.vue"
! find "${repo_root}/frontend/assets/logos" -maxdepth 1 -type f -iname 'romm_logo*' -print -quit | grep -q .
grep -Fq 'PGDP' "${repo_root}/examples/portainer-stack.yml"
grep -Fq 'PGDP_' "${repo_root}/examples/portainer.env.example"
grep -Fq 'PGDP' "${repo_root}/frontend/index.html"
grep -Fq 'PGDP' "${repo_root}/frontend/public/site.webmanifest"
if git -C "${repo_root}" grep -n -I -E 'ROMM_(DB_PASSWORD|LIBRARY_PATH|ASSETS_PATH|CONFIG_PATH|HTTP_PORT)' -- . ':!scripts/verify-pgdp-naming.sh' ':!scripts/verify-portainer-stack.sh' ':!.planning/**' >/dev/null; then
	echo "legacy operator alias detected outside the verifier allowlist" >&2
	exit 1
fi
controlled_paths=('examples/portainer-stack.yml' 'examples/portainer.env.example' 'examples/docker-compose.example.yml' 'backend/config/__init__.py' 'backend/pytest.ini' 'backend/romm_test/setup.sql' 'frontend/package.json' 'frontend/src/main.ts')
is_retained_occurrence() {
	case "$1" in
	*'/romm'* | *'ROMM_'* | *'romm_session'* | *'romm_csrftoken'* | *'romm-api-cache'*)
		return 0
		;;
	*'romm-chunk-reload-at'* | *'rommapp/romm'* | *'romm.app'* | *'docs.romm.app'* | *'RomM Switch Library'*)
		return 0
		;;
	esac
	return 1
}
unclassified=0
while IFS= read -r match; do
	[[ -z ${match} ]] && continue
	if ! is_retained_occurrence "${match}"; then
		echo "unclassified RomM occurrence in controlled surface: ${match}" >&2
		unclassified=1
	fi
done < <(git -C "${repo_root}" grep -n -I -i -E 'romm|rommapp|romm\.app' -- "${controlled_paths[@]}" || true)
test "${unclassified}" -eq 0
product_owned_paths=('examples/portainer-stack.yml' 'examples/portainer.env.example' 'examples/docker-compose.example.yml' 'docker/Dockerfile' 'docker/init_scripts' 'frontend/index.html' 'frontend/src/PGDP.vue' 'env.template' 'pyproject.toml')
if git -C "${repo_root}" grep -n -I -E 'Docker/Media|/home/d1sk/romm|romm_(mysql|resources|redis)_data|romm-db-dev' -- "${product_owned_paths[@]}"; then
	echo "live-state or old deployment identity detected in product-owned paths" >&2
	exit 1
fi
echo "PGDP naming inventory and retained-name allowlist gate passed"
