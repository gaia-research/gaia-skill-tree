# Portable Curation Environment Harness

This document defines the operational architecture, scripts, and contracts for the Gaia semantic curation environment tooling suite (`scripts/environment/*`), implemented per `CURATION-UPGRADE.md`.

The harness provides deterministic, isolated, and portable environment setup, lightweight diagnostic verification, maintenance error aggregation, and genuine Termux / aarch64 runtime benchmarking across developer machines, CI/CD runners, and native mobile environments.

---

## Architecture & Principles

1. **Isolation & Non-Interference (`env.sh`):**
   - Centralizes `GAIA_MODEL_CACHE`, `HF_HOME`, and `SENTENCE_TRANSFORMERS_HOME` (defaulting to checkout-local `.gaia/models`).
   - Automatically prefixes `PYTHONPATH` with active-branch `src/` to ensure current checkout modules take precedence over site-packages.
   - Discovers and exports virtual environment interpreter (`.venv/bin/python`), preferring newly created or existing `.venv` over stale initial `python3` fallback while preserving explicit caller overrides (`GAIA_PYTHON`).
   - Never modifies global git, npm, pip, or system configurations.
2. **Lightweight Diagnostics & Fast Startup (`doctor.py` <= 300 lines):**
   - Inspects dependency installation via `importlib.util.find_spec` and `importlib.metadata.version` only; **never imports `torch`, `sentence_transformers`, or `onnxruntime`** into the diagnostic process.
   - Inspects core runtime and dev dependencies (`jinja2`, `jsonschema`, `yaml`, `questionary`, `pytest`).
   - Resolves CLI package version by preferring project metadata (`pyproject.toml`) and installed metadata over stale module `__version__ = "0.1.0"`.
   - Core retrieval configuration API is **strictly required**; fails visibly on load errors instead of masking them with silent fallbacks.
   - Separates readiness into **dependencies readiness (`deps_ready`)** vs. **artifact freshness (`artifact_ready`)**, preventing `setup.sh` from unnecessarily reinstalling virtualenv dependencies due to stale embedding artifacts.
3. **Secret Safety by Design:**
   - Evaluates `TYPESAFE_API_KEY` as a boolean presence flag only (`JEV_API_KEY` is unsupported).
   - Secret tokens are never read, printed, or serialized in human or JSON outputs.
   - Secret scanning audits `git diff origin/main...HEAD` plus staged and unstaged working-tree changes, reporting matching file paths only (**never line numbers or matched content**).
4. **Honest Platform Proof & Full Semantic Matching:**
   - **Platform presence alone is NOT proven:** Detecting genuine Android aarch64 platform signals marks the runtime as `provisional`, not `proven`.
   - Proven runtime verification requires an actual matching successful smoke receipt (`generated-output/curation/termux-smoke.json`) generated on Android aarch64 under the active retrieval model, revision, backend, **pooling, normalization, query prefix, and semantic fingerprint**. A stale smoke receipt cannot prove a new or modified configuration.
   - `termux-smoke.sh` and `smoke.py --termux` **MUST return non-zero on non-Android / non-aarch64 platforms**.
5. **Real Functional Maintenance & Evaluation (`maintenance.sh`):**
   - Invokes real CLI entrypoints (`python -m gaia_cli`).
   - Aggregates errors across all steps rather than aborting prematurely, reporting total errors at completion.
   - `--benchmark` executes the real offline evaluation benchmark (`scripts/curation_benchmark.py`), not a warmup placeholder.
   - `--refresh` regenerates embeddings and performs an immediate verification recheck.

---

## Tooling Suite Overview

| File | Type | Primary Role |
|---|---|---|
| `scripts/environment/env.sh` | Bash | Centralizes caches, active-branch `PYTHONPATH`, and venv interpreter paths |
| `scripts/environment/setup.sh` | Bash (`set -euo pipefail`) | Bootstraps `.venv` with `[dev,embeddings]`, warms up, generates fresh embeddings via CLI, optional benchmark |
| `scripts/environment/doctor.py` | Python 3 (<= 300 lines) | Inspects active source, lightweight deps, retrieval, freshness, receipts, and Android proof |
| `scripts/environment/maintenance.sh` | Bash (`set -euo pipefail`) | Runs steward scan, validation, PR guards, secret scan, focused tests, and evaluation benchmark |
| `scripts/environment/termux-smoke.sh` | Bash (`set -euo pipefail`) | Orchestrates genuine Termux / Android aarch64 runtime verification and receipt emission |
| `scripts/environment/smoke.py` | Python 3 | Executes bounded synthetic warmup or genuine Android runtime verification with latency profiling |

---

## Command Reference

### 1. Environment Initialization (`env.sh`)

Sourced by shell scripts or interactive sessions to configure environment variables consistently without global mutations.

```bash
source scripts/environment/env.sh
```

- Sets `GAIA_MODEL_CACHE`, `HF_HOME`, `SENTENCE_TRANSFORMERS_HOME` to `.gaia/models`.
- Sets `PYTHONPATH` with `<repo_root>/src`.
- Sets `PY` to `.venv/bin/python` if present, preserving any existing caller `PY` override, otherwise falling back to `python3`.

---

### 2. Environment Setup (`setup.sh`)

Bootstraps an isolated virtual environment with required dependencies, warms the model, ensures embeddings freshness, and optionally generates an evaluation benchmark receipt.

```bash
# Standard setup (skips reinstall if deps healthy, skips embed if artifact fresh)
./scripts/environment/setup.sh

# Force re-creation and reinstallation of .venv and embeddings
./scripts/environment/setup.sh --force

# Check dependency readiness only (non-destructive)
./scripts/environment/setup.sh --check

# Setup environment and run offline evaluation benchmark receipt
./scripts/environment/setup.sh --benchmark
```

**Workflow and Contracts:**
1. **Preflight Dependency Check:** Evaluates `doctor.py --check-deps`. If dependencies are healthy and `.venv` exists, skips package reinstallation. Stale embedding artifacts do not trigger reinstall.
2. **Termux vs. Cloud / Desktop:**
   - **Termux:** Uses `python3 -m venv --system-site-packages .venv` to reuse native system packages (`python-torch`). Preserves system pip and safely upgrades venv `setuptools wheel`.
   - **Cloud / Desktop:** Bootstraps standard `.venv` and upgrades `pip setuptools wheel`.
3. **Editable Package Install:** Installs `.[dev,embeddings]` in local `.venv` without swallowed pip errors or fallbacks. If package installation fails, exits actionably with error code 1.
4. **Bounded Prefill Warmup:** Executes `smoke.py --warmup` using shared `getSentenceTransformer`, an isolated temporary synthetic registry (zero repo mutations), document encoding via `embed_skills`, synthetic candidate `Browser Session Controller` matching `browser-control` for valid positive mapping, and real packet self-validation.
5. **Fresh Embeddings Generation:** Evaluates `doctor.py --check-artifact`. If the embedding artifact is missing or stale, invokes `python -m gaia_cli dev embed` to generate fresh embeddings matching the active registry. If already fresh, skips generation.
6. **Optional Benchmark:** If `--benchmark` is specified, executes `scripts/curation_benchmark.py`.
7. **Diagnostics:** Runs `doctor.py` to print a consolidated health report.

---

### 3. Environment Doctor (`doctor.py`)

Provides lightweight, non-heavy diagnostic visibility into the local curation runtime.

```bash
# Concise terminal status summary
python scripts/environment/doctor.py

# Health check (exits 0 if healthy, 1 if broken)
python scripts/environment/doctor.py --check

# Check dependencies readiness only
python scripts/environment/doctor.py --check-deps

# Check embedding artifact freshness only
python scripts/environment/doctor.py --check-artifact

# Machine-readable JSON output
python scripts/environment/doctor.py --json

# Secret sanity scanner on changed tracked files (reports file paths only)
python scripts/environment/doctor.py --scan-secrets
```

**Inspected Dimensions:**
- **Source Import:** Confirms `gaia_cli` imports directly from `src/gaia_cli` on the active branch; reports version from `pyproject.toml` or installed package metadata.
- **Dependencies (Lightweight):** Queries `importlib.util.find_spec` and `importlib.metadata.version` for core modules (`jinja2`, `jsonschema`, `yaml`, `questionary`, `pytest`) and ML modules (`torch`, `sentence_transformers`, `numpy`, `onnxruntime`) without importing heavy runtime libraries.
- **Retrieval Configuration:** Strictly loads `loadRetrievalConfig` via core API; reports failure on errors. Default checks declared production default model only.
- **Artifact Freshness:** Evaluates `registry/embeddings.json` via `embeddingStatus` (semantic fingerprint and config matching).
- **Typesafe Credential Security:** Boolean presence check for `TYPESAFE_API_KEY` (`JEV_API_KEY` is unsupported).
- **Rubric Principles:** Reads version from `src/gaia_cli/data/curation/principles.json`.
- **Curation Eval Receipt:** Discovers latest evaluation receipt and verifies matching active model, `corpus_sha256`, and `catalog_sha256`.
- **Termux Proof:** Validates genuine Android/aarch64 platform markers. Marked `provisional` unless an actual matching successful smoke receipt is verified under the full active semantic configuration (model, revision, backend, pooling, normalize, prefix, fingerprint).

---

### 4. Maintenance Runner (`maintenance.sh`)

Executes regular development passes, PR guards, and health verification with error aggregation.

```bash
# Standard local maintenance pass
./scripts/environment/maintenance.sh

# Offline pass (explicitly records skipped git fetch)
./scripts/environment/maintenance.sh --offline

# Refresh embeddings if stale, then recheck freshness
./scripts/environment/maintenance.sh --refresh

# Run real offline curation evaluation benchmark
./scripts/environment/maintenance.sh --benchmark

# Execute all PR guards
./scripts/environment/maintenance.sh --all-guards
```

**Pass Sequence:**
1. Verify `python -m gaia_cli` entrypoint.
2. Git fetch & prune origin (skipped in `--offline` mode).
3. Read-only steward scan (`gaia steward scan`).
4. Registry validation (`gaia dev validate`).
5. PR guards (`scripts/pr_guards.py`).
6. Secret sanity scanner (`doctor.py --scan-secrets`).
7. Focused semantic and curation tests:
   ```bash
   pytest tests/test_curation_*.py tests/test_dev_prefill.py tests/test_dev_ratify.py tests/test_embeddings.py tests/test_jev*.py -q
   ```
8. Artifact freshness check: counts stale embeddings as warnings; when stale without `--refresh`, reports `NEEDS REFRESH` in summary and exits with code 2 (exit 1 if errors exist).
9. Embedding refresh (`--refresh`): regenerates embeddings, rechecks freshness, and records `[EVALUATION-NEEDED]` visibly per the `regenerate -> evaluate -> record` lifecycle.
10. Real evaluation benchmark (`scripts/curation_benchmark.py` when `--benchmark` is specified).
11. Aggregated error summary (exits with total error count, code 2 on stale-only, or code 0 on clean pass).

---

### 5. Termux Runtime Smoke (`termux-smoke.sh` & `smoke.py`)

Performs real model and prefill verification on Android / Termux aarch64 hardware.

```bash
# Run Termux smoke test (writes receipt to generated-output/curation/termux-smoke.json)
./scripts/environment/termux-smoke.sh

# Direct python helper invocation
python scripts/environment/smoke.py --termux --output generated-output/curation/termux-smoke.json

# Candidate smoke override with custom model and embeddings
python scripts/environment/smoke.py --termux --model BAAI/bge-small-en-v1.5 --embeddings generated-output/curation/bge.json

# Bounded warmup execution
python scripts/environment/smoke.py --warmup
```

**Smoke Workflow & Contracts:**
1. **Platform Validation:** Requires genuine Android aarch64 runtime; exits non-zero on non-Android platforms.
2. **Embeddings Artifact Verification:** Requires `embeddingStatus` to report `fresh` for the inspected embeddings artifact. If missing or stale, exits with non-zero code and provides clear remediation instructions (`gaia dev embed`). **No silent fallback to unverified embeddings or arbitrary catalog subsets (`catalog[:25]`).** Validates artifact structure via `load_embeddings`.
3. **Model Load:** Loads declared model (or `--model` override) using shared `getSentenceTransformer` with active revision, backend, and pooling applied.
4. **Direct Vector Extraction:** Extracts vector for test query using `embed_query` and profiles direct encoding latency and dimensionality.
5. **Real Prefill Query (No Precomputed Vector Shortcut):** Invokes `buildPrefillPacket` with `precomputedVector=None` so the real query encoder path executes against the active model and configuration. Uses valid candidate ID `smoke/termux` and schema lane `source-repository` with transparent recorded fixture fetcher for synthetic capability `Browser Session Controller` (`low-level browser DOM/cookie/navigation operations`), yielding a genuine positive mapping against `browser-control`. Empty recall is acknowledged as a valid retrieval outcome, never masked as an encoder or dimension failure.
6. **Packet Self-Validation:** Invokes `selfValidatePacket(packet)` and verifies that zero validation errors occur and no L4 resolution blocks exist in discovery packets.
7. **Full Semantic Receipt Emission:** Records full semantic configuration in receipt (`model`, `revision`, `backend`, `dimensions`, `pooling`, `normalize`, `query_prefix`, `fingerprint`), latencies, peak RSS, and dependency versions.
8. **Error Sanitization:** All exceptions and diagnostics redact potential secret keys and tokens.
