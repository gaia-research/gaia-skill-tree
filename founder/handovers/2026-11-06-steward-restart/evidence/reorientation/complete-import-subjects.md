# Complete Unused-Import Subject Analysis — Read-Only / Pure Analysis

Source working-tree blob hashes:
- `src/gaia_cli/embeddings.py`: `a2b66b7d792255e74071bfff07f457b3b9942e9b`
- `scripts/ci_churn.py`: `56f075d2073c8ee7c1b6714e51e2e34e4f21ffe1`
- `scripts/contentEngine/generate_weekly_report.py`: `05320fd195aa1386f71f0a95a0781fa551fa7a90`

Roster debt IDs from `roster-fresh-postmerge-reconcile.json` (`summary.reobserve.freshOpenDebt`).

---

## 1. Raw Findings & Completeness per Subject

### A. `src/gaia_cli/embeddings.py`
- **Debt ID:** `debt:unused_import:src-gaia-cli-embeddings-py:d86386eea761c182`
- **Exact Findings from `DeadCodeSensor.analyze` (9 items):**
  1. Line 14: `date` (`from datetime import date`, `sideEffectPossible: False`)
  2. Line 17: `clearModelCache` (`from gaia_cli.curation.retrieval import clearModelCache`, `sideEffectPossible: False`)
  3. Line 17: `clear_model_cache` (`from gaia_cli.curation.retrieval import clear_model_cache`, `sideEffectPossible: False`)
  4. Line 17: `embedding_status` (`from gaia_cli.curation.retrieval import embedding_status`, `sideEffectPossible: False`)
  5. Line 17: `get_sentence_transformer` (`from gaia_cli.curation.retrieval import get_sentence_transformer`, `sideEffectPossible: False`)
  6. Line 17: `load_retrieval_config` (`from gaia_cli.curation.retrieval import load_retrieval_config`, `sideEffectPossible: False`)
  7. Line 17: `save_embeddings_atomic` (`from gaia_cli.curation.retrieval import save_embeddings_atomic`, `sideEffectPossible: False`)
  8. Line 17: `semantic_fingerprint` (`from gaia_cli.curation.retrieval import semantic_fingerprint`, `sideEffectPossible: False`)
  9. Line 17: `validate_vector` (`from gaia_cli.curation.retrieval import validate_vector`, `sideEffectPossible: False`)
- **Partial closure analysis:** Eliminating only `date` leaves 8 open findings in `DeadCodeSensor`. Because the sensor reports unused imports per file, the debt item remains OPEN. It **cannot** resolve the debt.
- **Compatibility / re-export contract:** The 8 retrieval functions are dual-named (camelCase/snake_case) convenience re-exports. Downstream packages (e.g. `packages/cli-npm/cli/embeddings.py` doing `from gaia_cli.embeddings import *`) rely on `gaia_cli.embeddings` re-exporting them. Eliminating them alters module exports and risks breaking external consumers.
- **Existing tests & offline coverage:** `tests/test_embeddings.py` and `tests/test_curation_retrieval.py` both declare `pytestmark = [pytest.mark.integration]`. While unit mock logic exists inside them, the test files are categorized under the integration suite.

---

### B. `scripts/ci_churn.py`
- **Debt ID:** `debt:unused_import:scripts-ci-churn-py:51b6876e863ec208`
- **Exact Findings from `DeadCodeSensor.analyze` (2 items):**
  1. Line 37: `os` (`import os`, `sideEffectPossible: True`)
  2. Line 41: `timezone` (`from datetime import timezone`, `sideEffectPossible: False`)
- **Partial closure analysis:** Eliminating only `timezone` leaves `os` unaddressed. `DeadCodeSensor` will continue flagging `scripts/ci_churn.py`, so the debt item remains OPEN.
- **Bare stdlib initialization:** Line 39 imports `subprocess`, and line 35 imports `argparse`. Python stdlib `subprocess` unconditionally imports `os`. Thus, `os` is provably initialized by retained imports.
- **Existing tests & offline coverage:** `scripts/ci_churn.py` has **ZERO** test files across `tests/` and `scripts/`. There is no focused importing test to verify changes without introducing new test infrastructure.

---

### C. `scripts/contentEngine/generate_weekly_report.py`
- **Debt ID:** `debt:unused_import:scripts-contentengine-generate-weekly-report-py:68cf95ea87816616`
- **Exact Findings from `DeadCodeSensor.analyze` (3 items):**
  1. Line 27: `shutil` (`import shutil`, `sideEffectPossible: True`)
  2. Line 29: `tempfile` (`import tempfile`, `sideEffectPossible: True`)
  3. Line 32: `Any` (`from typing import Any`, `sideEffectPossible: False`)
- **Partial closure analysis:** Eliminating only `Any` leaves `shutil` and `tempfile`. `DeadCodeSensor` will continue reporting this file, so eliminating only `Any` **cannot** resolve the debt.
- **Bare stdlib initialization:** Retained imports are `argparse`, `json`, `os`, `re`, `sys`, `datetime`, `pathlib`, `typing`. AST and runtime inspection confirms that none of these imports `shutil` or `tempfile` (`'shutil' in sys.modules` is `False`, `'tempfile' in sys.modules` is `False`). Removing `import shutil` and `import tempfile` therefore alters module initialization state (side-effect uncertainty).
- **Public re-export contract & frontend gating:** No public re-export of `shutil`, `tempfile`, or `Any` is declared. Under CLAUDE.md § Frontend Changes, refactors with no rendered diff are exempt from human design gating; removing unused imports does not change output report JSON/HTML.
- **Existing tests & offline coverage:** Fully covered by `tests/contentEngine/test_generate.py`. Fast, offline unit test suite with NO `integration` marker, NO network calls, and NO HuggingFace/model dependencies.

---

## 2. Synthesis & Nomination Conclusion

| Subject | Total Findings | Can Single Subset Close Debt? | Retained Stdlib Initialized? | Offline Unit Test Exists? |
|---|---|---|---|---|
| `embeddings.py` | 9 | No (leaves 8 re-export items) | Yes (for `date`), but re-exports contract blocked | No (`pytestmark = [integration]`) |
| `scripts/ci_churn.py` | 2 | No (leaves `os`) | Yes (`os` initialized by `subprocess`) | **No (0 tests exist)** |
| `generate_weekly_report.py` | 3 | No (leaves `shutil`, `tempfile`) | **No** (`shutil`/`tempfile` not initialized by retained) | **Yes** (`tests/contentEngine/test_generate.py`) |

### Result:

1. **If strict whole-subject closure with ZERO side-effect uncertainty is required:**
   **Nomination: NONE.**
   - `embeddings.py`: Missing fact is lack of an approved deprecation/re-export contract for the 8 retrieval functions, plus integration test marking.
   - `scripts/ci_churn.py`: Missing fact is the total absence of existing tests for `ci_churn.py`.
   - `generate_weekly_report.py`: Missing fact is that `shutil` and `tempfile` are bare imports not initialized by retained imports.

2. **If Lead approves whole-subject cleanup of all 3 imports in `generate_weekly_report.py` accepting the documented stdlib initialization caveat:**
   - **One Feasible Subject:** `scripts/contentEngine/generate_weekly_report.py` (blob `05320fd195aa1386f71f0a95a0781fa551fa7a90`, debt `debt:unused_import:scripts-contentengine-generate-weekly-report-py:68cf95ea87816616`).
   - Requires removing all three unused bindings together (`shutil` at line 27, `tempfile` at line 29, `Any` at line 32).
   - Feasible test map: `python -m pytest tests/contentEngine/test_generate.py` (completely offline, fast, unmocked fixtures in `tmp_path`).
