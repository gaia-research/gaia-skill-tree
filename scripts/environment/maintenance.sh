#!/usr/bin/env bash
# Gaia Curation Environment Maintenance
# Runs steward scan, registry validation, PR guards, secret scan, focused curation
# tests, and embedding freshness verification with error aggregation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env.sh"
cd "${REPO_ROOT}"

OFFLINE=0
REFRESH=0
BENCHMARK=0
ALL_GUARDS=0

for arg in "$@"; do
  case "$arg" in
    --offline)
      OFFLINE=1
      ;;
    --refresh)
      REFRESH=1
      ;;
    --benchmark)
      BENCHMARK=1
      ;;
    --all-guards)
      ALL_GUARDS=1
      ;;
    -h|--help)
      echo "Usage: ./scripts/environment/maintenance.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --offline      Skip network git fetch/prune"
      echo "  --refresh      Regenerate embeddings if stale, then recheck"
      echo "  --benchmark    Run real offline curation evaluation benchmark"
      echo "  --all-guards   Run all PR guards (default: changed-path guards)"
      echo "  -h, --help     Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

ERRORS=0
WARNINGS=0

echo "================================================================"
echo " Gaia Curation Environment Maintenance Pass"
echo "================================================================"

# Step 0: Verify real python -m gaia_cli execution
echo "--> Verifying CLI entrypoint (python -m gaia_cli)..."
if ! "${PY}" -m gaia_cli --version >/dev/null 2>&1; then
  echo "[ERROR] python -m gaia_cli failed to execute!" >&2
  ERRORS=$((ERRORS + 1))
fi

# Step 1: Git Fetch & Prune (Optional --offline)
if [[ "${OFFLINE}" -eq 0 ]]; then
  echo "--> Step 1: Git fetch & prune origin..."
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git remote get-url origin >/dev/null 2>&1; then
    if ! git fetch --prune origin; then
      echo "[WARN] git fetch --prune origin failed or unreachable; continuing in local mode"
      WARNINGS=$((WARNINGS + 1))
    fi
  else
    echo "[INFO] No git remote 'origin' detected; skipping fetch."
  fi
else
  echo "--> Step 1: [OFFLINE] Explicitly skipping network git fetch."
fi

# Step 2: Gaia Steward Scan (Read-only scan; NOT run or dispatch)
echo "--> Step 2: Gaia Steward scan (read-only scan)..."
if ! "${PY}" -m gaia_cli steward scan; then
  echo "[ERROR] Gaia Steward scan failed!" >&2
  ERRORS=$((ERRORS + 1))
fi

# Step 3: Registry & Schema Validation
echo "--> Step 3: Registry validation (gaia dev validate)..."
if ! "${PY}" -m gaia_cli dev validate; then
  echo "[ERROR] gaia dev validate failed!" >&2
  ERRORS=$((ERRORS + 1))
fi

# Step 4: Applicable PR Guards
echo "--> Step 4: Determining and executing applicable PR guards..."
GUARDS_ARGS=""
if [[ "${ALL_GUARDS}" -eq 1 ]]; then
  GUARDS_ARGS="--all"
fi
if ! "${PY}" scripts/pr_guards.py ${GUARDS_ARGS}; then
  echo "[ERROR] Applicable PR guards failed!" >&2
  ERRORS=$((ERRORS + 1))
fi

# Step 5: Secret sanity scan (comparing baseline branch + staged + worktree, reports path not line)
echo "--> Step 5: Secret sanity scanner..."
if ! "${PY}" "${SCRIPT_DIR}/doctor.py" --scan-secrets; then
  echo "[ERROR] Secret sanity scan detected potential leaks!" >&2
  ERRORS=$((ERRORS + 1))
fi

# Step 6: Focused Curation and Semantic Tests
echo "--> Step 6: Running curation, prefill, ratify, embeddings, and jev tests..."
if ! "${PY}" -m pytest \
    tests/test_curation_*.py \
    tests/test_dev_prefill.py \
    tests/test_dev_ratify.py \
    tests/test_embeddings.py \
    tests/test_jev*.py \
    -q; then
  echo "[ERROR] Focused tests failed!" >&2
  ERRORS=$((ERRORS + 1))
fi

# Step 7: Embedding Freshness & Optional Refresh
echo "--> Step 7: Verifying embedding artifact freshness..."
STALE_ARTIFACT=0
EVALUATION_NEEDED=0

if ! "${PY}" "${SCRIPT_DIR}/doctor.py" --check-artifact >/dev/null 2>&1; then
  echo "[WARN] Embedding artifacts are stale or out-of-sync."
  WARNINGS=$((WARNINGS + 1))
  STALE_ARTIFACT=1
  if [[ "${REFRESH}" -eq 1 ]]; then
    echo "--> [REFRESH] Generating embeddings..."
    if ! "${PY}" -c "
import sys
from gaia_cli.embeddings import generate_embeddings
res = generate_embeddings(registry_path='.')
if res is None:
    sys.exit(1)
"; then
      echo "[ERROR] Embedding regeneration failed (returned None or failed)!" >&2
      ERRORS=$((ERRORS + 1))
    else
      echo "--> [REFRESH] Rechecking artifact freshness after generation..."
      if ! "${PY}" "${SCRIPT_DIR}/doctor.py" --check-artifact >/dev/null 2>&1; then
        echo "[ERROR] Embeddings remain stale after regeneration attempt!" >&2
        ERRORS=$((ERRORS + 1))
      else
        echo "[OK] Embeddings successfully regenerated and verified fresh."
        echo "[EVALUATION-NEEDED] Semantic artifact was regenerated. Run 'scripts/curation_benchmark.py' to evaluate and record receipt (lifecycle: regenerate -> evaluate -> record)."
        STALE_ARTIFACT=0
        EVALUATION_NEEDED=1
      fi
    fi
  else
    echo "[INFO] Pass --refresh to update stale embeddings."
  fi
else
  echo "[OK] Embedding artifacts are fresh."
fi

# Step 8: Real Benchmark (--benchmark)
if [[ "${BENCHMARK}" -eq 1 ]]; then
  echo "--> Step 8: Running real curation retrieval evaluation benchmark..."
  if ! "${PY}" scripts/curation_benchmark.py; then
    echo "[ERROR] Curation retrieval benchmark failed!" >&2
    ERRORS=$((ERRORS + 1))
  fi
fi

# Step 9: Error Aggregation & Summary
echo "================================================================"
echo " Maintenance Summary:"
echo " - Errors: ${ERRORS}"
echo " - Warnings: ${WARNINGS}"
if [[ "${STALE_ARTIFACT}" -eq 1 ]]; then
  echo " - Status: NEEDS REFRESH (embedding artifacts are stale)"
fi
if [[ "${EVALUATION_NEEDED}" -eq 1 ]]; then
  echo " - Evaluation: EVALUATION-NEEDED (run scripts/curation_benchmark.py to benchmark and record receipt)"
fi
echo "================================================================"

if [[ "${ERRORS}" -gt 0 ]]; then
  echo "[MAINTENANCE] FAILED with ${ERRORS} error(s)." >&2
  exit 1
fi

if [[ "${STALE_ARTIFACT}" -eq 1 ]]; then
  echo "[MAINTENANCE] NEEDS REFRESH: Embedding artifact is stale. Run with --refresh to regenerate." >&2
  exit 2
fi

echo "[MAINTENANCE] PASSED: All maintenance checks completed cleanly."
exit 0
