#!/usr/bin/env bash
# Gaia Curation Environment Setup
# Configures isolated virtual environment (.venv) with portable ML/retrieval support,
# respecting Termux system site packages (never touching system pip), configuring
# model cache directories, installing project dependencies, executing bounded
# model warmup, producing fresh embeddings via CLI if missing or stale, and
# optionally generating a benchmark receipt.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env.sh"
cd "${REPO_ROOT}"

FORCE=0
CHECK_ONLY=0
RUN_BENCHMARK=0

for arg in "$@"; do
  case "$arg" in
    --force)
      FORCE=1
      ;;
    --check)
      CHECK_ONLY=1
      ;;
    --benchmark)
      RUN_BENCHMARK=1
      ;;
    -h|--help)
      echo "Usage: ./scripts/environment/setup.sh [--force] [--check] [--benchmark]"
      echo "  --check      Run lightweight dependency health check and exit"
      echo "  --force      Force recreation and reinstallation of .venv and embeddings"
      echo "  --benchmark  Run offline curation evaluation benchmark receipt after setup"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

# 1. Dependency Preflight Check First (Stale embeddings do NOT trigger reinstall!)
DEPS_HEALTHY=0
if "${PY}" "${SCRIPT_DIR}/doctor.py" --check-deps >/dev/null 2>&1; then
  DEPS_HEALTHY=1
fi

if [[ "${CHECK_ONLY}" -eq 1 ]]; then
  if [[ "${DEPS_HEALTHY}" -eq 1 ]]; then
    echo "[SETUP] Environment dependency health check: PASSED"
    exit 0
  else
    echo "[SETUP] Environment dependency health check: FAILED (environment requires setup)" >&2
    exit 1
  fi
fi

# 2. Dependency Installation Gate (Skip install if healthy and .venv exists)
if [[ "${DEPS_HEALTHY}" -eq 1 && -d "${REPO_ROOT}/.venv" && "${FORCE}" -eq 0 ]]; then
  echo "[SETUP] Environment dependencies are already healthy and .venv exists. Skipping install (pass --force to override)."
else
  IS_TERMUX=0
  if [[ -n "${TERMUX_VERSION:-}" ]] || [[ "${PREFIX:-}" =~ com\.termux ]] || [[ -d "/data/data/com.termux" ]]; then
    IS_TERMUX=1
  fi

  if [[ -d "${REPO_ROOT}/.venv" && "${FORCE}" -eq 1 ]]; then
    echo "==> Removing existing .venv (--force specified)..."
    rm -rf "${REPO_ROOT}/.venv"
  fi

  if [[ ! -d "${REPO_ROOT}/.venv" ]]; then
    echo "==> Creating isolated virtual environment at .venv..."
    if [[ "${IS_TERMUX}" -eq 1 ]]; then
      echo "==> Termux detected: enabling --system-site-packages for native torch/onnx reuse..."
      python3 -m venv --system-site-packages "${REPO_ROOT}/.venv"
    else
      python3 -m venv "${REPO_ROOT}/.venv"
    fi
  fi

  source "${SCRIPT_DIR}/env.sh"

  if [[ "${IS_TERMUX}" -eq 0 ]]; then
    echo "==> Cloud/Desktop environment: upgrading packaging tools inside .venv..."
    "${VENV_PIP}" install --upgrade pip setuptools wheel
  else
    echo "==> Termux environment: preserving system-managed pip; updating local venv tools safely..."
    "${VENV_PIP}" install --upgrade setuptools wheel
  fi

  echo "==> Installing editable package in local .venv..."
  if ! "${VENV_PIP}" install -e '.[dev,embeddings]'; then
    echo "[SETUP ERROR] Failed installing package with '.[dev,embeddings]' in local .venv." >&2
    echo "[SETUP ERROR] Ensure build tools (setuptools, wheel) are available and dependencies are resolvable." >&2
    exit 1
  fi

  echo "==> Warming declared model and executing bounded prefill smoke..."
  "${VENV_PY:-${PY}}" "${SCRIPT_DIR}/smoke.py" --warmup
fi

# Refresh env vars for venv paths
source "${SCRIPT_DIR}/env.sh"
EXEC_PY="${PY:-${VENV_PY}}"

# 3. Artifact Freshness and Embeddings Generation via CLI
ARTIFACT_FRESH=0
if "${EXEC_PY}" "${SCRIPT_DIR}/doctor.py" --check-artifact >/dev/null 2>&1; then
  ARTIFACT_FRESH=1
fi

if [[ "${ARTIFACT_FRESH}" -eq 1 && "${FORCE}" -eq 0 ]]; then
  echo "[SETUP] Embeddings artifact is already fresh. Skipping generation."
else
  echo "==> Embeddings artifact missing or stale: generating fresh embeddings via gaia dev embed..."
  GAIA_OPERATOR_OVERRIDE=1 "${EXEC_PY}" -m gaia_cli dev embed
fi

# 4. Optional Benchmark Receipt
if [[ "${RUN_BENCHMARK}" -eq 1 ]]; then
  echo "==> Running offline curation evaluation benchmark receipt..."
  "${EXEC_PY}" "${REPO_ROOT}/scripts/curation_benchmark.py" --output generated-output/curation/curation-eval.json
fi

# 5. Diagnostics and Health Report
echo "==> Generating environment diagnostics..."
"${EXEC_PY}" "${SCRIPT_DIR}/doctor.py"

echo "==> Gaia curation environment setup complete."
