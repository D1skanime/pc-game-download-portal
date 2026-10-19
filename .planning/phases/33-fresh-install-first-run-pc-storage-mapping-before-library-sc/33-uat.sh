#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(dirname "${0}")"
cd "${SCRIPT_DIR}"
PHASE_DIR="${PWD}"
HOST_OS="$(uname -s)"
test "${HOST_OS}" = Linux
cd /home/d1sk/pc-game-download-portal
REPO_ROOT="$(git rev-parse --show-toplevel)"
test "${REPO_ROOT}" = "${PWD}"
exec python3 "${REPO_ROOT}/backend/tools/phase33_uat.py" "$@"
