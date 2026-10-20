#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
stack_relative='examples/portainer-stack.yml'
source_revision="$(git -C "${repo_root}" rev-parse HEAD)"
source_branch="$(git -C "${repo_root}" branch --show-current)"
run_id="$(date -u +%Y%m%d%H%M%S)-${RANDOM}-${RANDOM}"
project="pgdp-proof-${run_id}"
work_root="$(mktemp -d "/tmp/pgdp-fresh-proof.${run_id}.XXXXXX")"
clone_root="${work_root}/clone"
env_file="${work_root}/portainer.env"
rendered_file="${work_root}/rendered.yml"
logs_file="${work_root}/logs.txt"
cleanup_log="${work_root}/cleanup.txt"
summary_file="${repo_root}/.planning/phases/32-pgdp-namensumstellung-fresh-installation/32-03-SUMMARY.md"
app_container="${project}-app"
db_container="${project}-db"
selected_port=''
cleanup_result='not-run'
db_health='not-observed'
heartbeat='not-observed'
image_digest='not-observed'
empty_volumes='not-observed'
log_scan='not-observed'

# shellcheck disable=SC2329 # Called by the EXIT trap through cleanup.
write_summary() {
	local status="$1"
	local cleanup_state="$2"
	local summary_directory
	summary_directory="$(dirname -- "${summary_file}")"
	mkdir -p "${summary_directory}"
	{
		echo '# Phase 32 Plan 03: Fresh PGDP Stack Proof'
		echo
		echo "Result: ${status}"
		echo
		echo '## Proof identity'
		echo
		echo "- Source checkout: ${repo_root}"
		echo "- Source branch: ${source_branch}"
		echo "- Source revision: ${source_revision}"
		echo '- Clean clone: git clone --no-local from the verified source checkout.'
		echo "- Disposable Compose project: ${project}"
		echo '- Provider credentials: blank.'
		echo '- Synthetic paths: temporary paths under the proof workspace only.'
		echo
		echo '## Evidence'
		echo
		echo "- Static naming gate in clean clone: passed before build."
		echo "- Rendered Compose parity and collision checks: passed before create."
		echo "- Empty disposable volume labels and pre-start contents: ${empty_volumes}."
		echo "- MariaDB health: ${db_health}."
		echo "- Application heartbeat /api/heartbeat: ${heartbeat}."
		echo "- Image digest: ${image_digest}."
		echo "- Synthetic-secret log scan: ${log_scan}."
		echo "- Cleanup: ${cleanup_state}."
		echo
		echo '## Retained-name allowlist'
		echo
		echo 'The proof consumes 32-NAMING-INVENTORY.md. Compatibility-owned ROMM_* runtime keys, /romm and /assets/romm paths, schema/provider identifiers, browser/cache keys, and upstream URLs remain retained. PGDP is the only product-owned operator/deployment wrapper.'
		echo
		echo '## Commands'
		echo
		echo '    bash scripts/verify-pgdp-naming.sh'
		echo '    bash scripts/verify-portainer-stack.sh'
		echo '    docker compose config, build, create, start, logs, down --volumes'
		echo '    curl --fail http://127.0.0.1:<synthetic-port>/api/heartbeat'
		echo
		echo '## Limitations'
		echo
		echo '- This proves a fresh installation path only. It does not migrate, adopt, inspect, delete, or modify any existing database, media, game library, NAS mount, old RomM volume, or live service.'
		echo '- The proof uses synthetic secrets and temporary bind paths. It does not prove production credentials, NAS permissions, provider availability, or upgrade compatibility.'
		echo '- The checked-out branch is not pushed or merged by this proof.'
	} >"${summary_file}"
}

# shellcheck disable=SC2329 # Registered as the EXIT trap.
cleanup() {
	local exit_status="$1"
	local compose_status=0
	set +e
	if [[ -f ${env_file} && -d ${clone_root} ]]; then
		docker compose --project-name "${project}" --project-directory "${clone_root}/examples" \
			--env-file "${env_file}" -f "${clone_root}/${stack_relative}" \
			down --volumes --remove-orphans >"${cleanup_log}" 2>&1
		compose_status="$?"
	fi
	local project_containers project_volumes app_containers db_containers
	project_containers="$(docker ps -aq --filter "label=com.docker.compose.project=${project}")" || compose_status=1
	project_volumes="$(docker volume ls -q --filter "label=com.docker.compose.project=${project}")" || compose_status=1
	app_containers="$(docker ps -aq --filter "name=^${app_container}$")" || compose_status=1
	db_containers="$(docker ps -aq --filter "name=^${db_container}$")" || compose_status=1
	if [[ ${compose_status} -eq 0 ]] &&
		[[ -z ${project_containers} ]] &&
		[[ -z ${project_volumes} ]] &&
		[[ -z ${app_containers} ]] &&
		[[ -z ${db_containers} ]]; then
		cleanup_result='passed, only generated project resources were removed'
	else
		cleanup_result='FAILED, generated resources remain or Compose cleanup failed'
	fi
	case "${work_root}" in
	/tmp/pgdp-fresh-proof.*) rm -rf -- "${work_root}" ;;
	*)
		echo "refusing unexpected temporary path: ${work_root}" >&2
		cleanup_result='FAILED, unexpected temporary path'
		;;
	esac
	write_summary "${exit_status}" "${cleanup_result}"
	if [[ ${cleanup_result} == FAILED* ]]; then
		exit 1
	fi
	exit "${exit_status}"
}
trap 'cleanup "$?"' EXIT

for command_name in docker git curl grep find awk; do
	command -v "${command_name}" >/dev/null || {
		echo "${command_name} is required" >&2
		exit 1
	}
done
test -n "${source_branch}"
observed_output="$(git -C "${repo_root}" status --short)"
test -z "${observed_output}"

for candidate_port in 18080 18081 18082 18083 18084 18085 18086 18087 18088 18089; do
	if ! (echo >/dev/tcp/127.0.0.1/"${candidate_port}") 2>/dev/null; then
		selected_port="${candidate_port}"
		break
	fi
done
test -n "${selected_port}" || {
	echo 'no disposable host port available' >&2
	exit 1
}

git clone --no-local --branch "${source_branch}" "${repo_root}" "${clone_root}" >/dev/null
clone_revision="$(git -C "${clone_root}" rev-parse HEAD)"
test "${clone_revision}" = "${source_revision}"

library_path="${work_root}/library"
assets_path="${work_root}/assets"
config_path="${work_root}/config"
mkdir -p "${library_path}" "${assets_path}" "${config_path}"
db_password="synthetic-db-${project}"
db_root_password="synthetic-root-${project}"
auth_secret="synthetic-auth-${project}"
cat >"${env_file}" <<EOF
PGDP_PROJECT_NAME=${project}
PGDP_IMAGE=pc-game-download-portal:${project}
PGDP_CONTAINER_NAME=${app_container}
PGDP_DB_CONTAINER_NAME=${db_container}
PGDP_TZ=UTC
PGDP_HTTP_PORT=${selected_port}
PGDP_LIBRARY_PATH=${library_path}
PGDP_ASSETS_PATH=${assets_path}
PGDP_CONFIG_PATH=${config_path}
PGDP_DB_NAME=pgdp_proof
PGDP_DB_USER=pgdp_proof
PGDP_DB_PASSWORD=${db_password}
PGDP_DB_ROOT_PASSWORD=${db_root_password}
PGDP_AUTH_SECRET_KEY=${auth_secret}
PGDP_SCREENSCRAPER_USER=
PGDP_SCREENSCRAPER_PASSWORD=
PGDP_SCREENSCRAPER_DEV_ID=
PGDP_SCREENSCRAPER_DEV_PASSWORD=
PGDP_RETROACHIEVEMENTS_API_KEY=
PGDP_STEAMGRIDDB_API_KEY=
PGDP_IGDB_CLIENT_ID=
PGDP_IGDB_CLIENT_SECRET=
PGDP_HASHEOUS_API_ENABLED=false
EOF

observed_output="$(docker ps -aq --filter "label=com.docker.compose.project=${project}")"
test -z "${observed_output}"
observed_output="$(docker volume ls -q --filter "label=com.docker.compose.project=${project}")"
test -z "${observed_output}"
observed_output="$(docker ps -aq --filter "name=^${app_container}$")"
test -z "${observed_output}"
observed_output="$(docker ps -aq --filter "name=^${db_container}$")"
test -z "${observed_output}"

bash "${clone_root}/scripts/verify-pgdp-naming.sh"
bash "${clone_root}/scripts/verify-portainer-stack.sh"
docker compose --project-name "${project}" --project-directory "${clone_root}/examples" \
	--env-file "${env_file}" -f "${clone_root}/${stack_relative}" config >"${rendered_file}"
grep -Fq "name: ${project}" "${rendered_file}"
grep -Fq "source: ${library_path}" "${rendered_file}"
grep -Fq 'target: /romm/library' "${rendered_file}"
grep -Fq 'read_only: true' "${rendered_file}"
grep -Fq 'DB_HOST: pgdp-db' "${rendered_file}"
grep -Fq 'MARIADB_DATABASE: pgdp_proof' "${rendered_file}"
if grep -Fq '/home/d1sk/romm' "${rendered_file}"; then
	exit 1
else
	test "$?" -eq 1
fi
if grep -E 'romm_(mysql|resources|redis)_data|romm-db-dev|Team4s|Docker/Media' "${rendered_file}"; then
	exit 1
else
	test "$?" -eq 1
fi

docker compose --project-name "${project}" --project-directory "${clone_root}/examples" \
	--env-file "${env_file}" -f "${clone_root}/${stack_relative}" build
image_digest="$(docker image inspect "pc-game-download-portal:${project}" --format '{{.Id}}')"

docker compose --project-name "${project}" --project-directory "${clone_root}/examples" \
	--env-file "${env_file}" -f "${clone_root}/${stack_relative}" create

for volume_name in "${project}_pgdp_mysql_data" "${project}_pgdp_resources" "${project}_pgdp_redis_data"; do
	docker volume inspect "${volume_name}" >/dev/null
	volume_project="$(docker volume inspect "${volume_name}" --format '{{index .Labels "com.docker.compose.project"}}')"
	test "${volume_project}" = "${project}"
	docker run --rm -v "${volume_name}:/data:ro" alpine:3.23 sh -ec 'test -z "$(find /data -mindepth 1 -maxdepth 1 -print -quit)"'
done
empty_volumes='passed, all generated volumes labeled for the disposable project and empty before start'

docker compose --project-name "${project}" --project-directory "${clone_root}/examples" \
	--env-file "${env_file}" -f "${clone_root}/${stack_relative}" start

for ((attempt = 0; attempt < 60; attempt++)); do
	db_health="$(docker inspect "${db_container}" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' 2>/dev/null || true)"
	[[ ${db_health} == healthy ]] && break
	sleep 5
done
test "${db_health}" = healthy

for ((attempt = 0; attempt < 60; attempt++)); do
	if curl --fail --silent --show-error --max-time 5 "http://127.0.0.1:${selected_port}/api/heartbeat" >"${work_root}/heartbeat.json"; then
		heartbeat='passed'
		break
	fi
	sleep 5
done
test "${heartbeat}" = passed

docker exec "${app_container}" getent hosts pgdp-db | grep -Eq '(^|[[:space:]])pgdp-db([[:space:]]|$)'
docker inspect "${app_container}" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -Fq 'DB_HOST=pgdp-db'
docker inspect "${app_container}" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -Fq 'DB_NAME=pgdp_proof'
docker inspect "${db_container}" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -Fq 'MARIADB_DATABASE=pgdp_proof'
docker inspect "${db_container}" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -Fq 'MARIADB_USER=pgdp_proof'
docker inspect "${app_container}" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -Fq 'SCREENSCRAPER_USER='

docker compose --project-name "${project}" --project-directory "${clone_root}/examples" \
	--env-file "${env_file}" -f "${clone_root}/${stack_relative}" logs --no-color >"${logs_file}"
if grep -Fq "${db_password}" "${logs_file}"; then
	exit 1
else
	test "$?" -eq 1
fi
if grep -Fq "${db_root_password}" "${logs_file}"; then
	exit 1
else
	test "$?" -eq 1
fi
if grep -Fq "${auth_secret}" "${logs_file}"; then
	exit 1
else
	test "$?" -eq 1
fi
log_scan='passed, synthetic database and auth secrets absent from Compose logs'

exit 0
