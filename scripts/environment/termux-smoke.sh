#!/usr/bin/env bash
# Gaia Termux Smoke Test Runner
# Verifies genuine Termux / Android aarch64 runtime proof, executes direct model query
# and real Gaia prefill query with active retrieval config and actual generic catalog,
# and emits a structured receipt.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env.sh"
cd "${REPO_ROOT}"

DEFAULT_OUTPUT="${REPO_ROOT}/generated-output/curation/termux-smoke.json"
mkdir -p "$(dirname "${DEFAULT_OUTPUT}")"

# Forward arguments to smoke.py
exec "${PY}" "${SCRIPT_DIR}/smoke.py" --termux --output "${DEFAULT_OUTPUT}" "$@"
