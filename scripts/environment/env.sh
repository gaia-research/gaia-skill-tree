#!/usr/bin/env bash
# Common environment initialization for Gaia curation tooling.
# Centralizes cache locations, active-branch PYTHONPATH, and venv interpreter.
# Never modifies global git, npm, or system configurations.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"

# Centralize cache directories (repository-local or respect existing GAIA_MODEL_CACHE)
export GAIA_MODEL_CACHE="${GAIA_MODEL_CACHE:-${REPO_ROOT}/.gaia/models}"
export HF_HOME="${GAIA_MODEL_CACHE}"
export SENTENCE_TRANSFORMERS_HOME="${GAIA_MODEL_CACHE}"
mkdir -p "${GAIA_MODEL_CACHE}"

# Centralize PYTHONPATH pointing to active branch src
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

# Locate venv interpreter and pip (preferring installed venv over stale python3/system fallback)
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  export VENV_PY="${REPO_ROOT}/.venv/bin/python"
  export VENV_PIP="${REPO_ROOT}/.venv/bin/pip"
  if [[ -n "${GAIA_PYTHON:-}" ]]; then
    export PY="${GAIA_PYTHON}"
  elif [[ -z "${PY:-}" || "${PY}" == "python3" || "${PY}" == "python" || "${PY}" == "${PREFIX:-}/bin/python"* || "${PY}" == "/usr/bin/python"* || "${PY}" == "/usr/local/bin/python"* ]]; then
    export PY="${VENV_PY}"
  fi
else
  export VENV_PY=""
  export VENV_PIP=""
  export PY="${GAIA_PYTHON:-${PY:-${PYTHON:-python3}}}"
fi
