# PR #2302 Reconciliation Handoff: Canonical Generic Listing

**Date**: 2026-11-09  
**Branch**: `cli/dev-list-canonical-nodes-2301`  
**Commit**: `8549217d397aa4c6db0881f19f5feb598fd3205f` (PR #2302)  
**Base**: `main` (`af57c7f6d6b796364d485688d35c1f5c871f1b04`, post-PR #2427)  
**Status**: READY FOR REVIEW  

---

## 1. Summary and Scope
PR #2302 resolves #2301 by making `gaia dev list` read canonical source nodes directly from checkout-local `registry/nodes/{basic,fusion}/` instead of requiring the generated/gitignored Class P artifact `registry/gaia.json`.

Files touched (narrowly scoped to original PR intention):
1. `src/gaia_cli/commands/dev/list.py`
2. `tests/test_dev_list_fresh_checkout.py`
3. `docs/agents/DEV_LIST_CANONICAL_NODES_HANDOFF.md` (this handoff)

No unrelated refactoring or changes to other CLI commands or registry nodes were introduced.

---

## 2. Invariant & Steward Preservation
Current `main` at `af57c7f6d6b796364d485688d35c1f5c871f1b04` (which landed Steward campaign PR #2427: Class B 323 → 191, 48 canonical repairs, 45 demotions) is strictly preserved.
- No files modified by PR #2427 or earlier Steward work were touched or reverted.
- Zero merge conflicts encountered during mechanical reconciliation against latest `main`.
- Effective diff against `main` is strictly limited to the intended list command fix, its unit tests, and this documentation handoff.

---

## 3. Verification Evidence
1. **311-generic snapshot verification**:
   - `registry/nodes/basic`: 158 nodes
   - `registry/nodes/fusion`: 153 nodes
   - Total canonical nodes: 311 nodes
   - Executing `python3 -m gaia_cli --registry . dev list --generic --json` accurately returns a 311-element JSON array of generic skills.
   - Non-JSON execution (`gaia dev list --generic`) outputs 311 formatted entries.
2. **JSON behavior & edge cases**:
   - With `--json`, empty result emits `[]` (valid parseable JSON array).
   - Without `--json`, empty result emits human-readable `No skills found.`.
   - `--description` flag correctly includes description text from node files.
3. **Automated tests**:
   - `python3 -m pytest tests/test_dev_list_fresh_checkout.py`: 3 passed (100%) covering node reading, priority, fallback, empty JSON (`[]`), and empty non-JSON (`No skills found.`).
4. **Repository guards**:
   - `python3 scripts/pr_guards.py --all`:
     - HTML sink guard: PASS (warn-only, 0 new)
     - Rank vocabulary guard: PASS (0 hard violations)
     - Taxonomy authority guard: PASS (0 read-time derivation sites)
     - Version stamp guard: PASS (0 literal version stamps in scope)
     - Lexicon guard: PASS (42 self-tests passed, 0 new findings)
     - License validator: PASS (311 skills validated, no conflicts)
5. **Branch scope**:
   - Branch `cli/dev-list-canonical-nodes-2301` adheres to the `cli/` branch rule (`src/*|packages/*|tests/*|*.md`).

---

## 4. Review & Merge Readiness
- **Independent Review**: Completed by Luna HIGH via shared `openai-codex` provider (`openai-codex/gpt-6-luna:high`).
  - **Verdict**: **READY FOR REVIEW**.
  - **Findings**: Verified `list.py` reads canonical node JSON directly from `registry/nodes/`, sorts generic results deterministically by ID, preserves legacy graph fallback when no node directory exists, and emits valid `[]` JSON for empty results. Unit tests in `tests/test_dev_list_fresh_checkout.py` verify fresh-checkout listing and filters, node precedence, legacy graph fallback, empty JSON output, and empty non-JSON message.
- **Ruff Gate**: PASS (unused import `Path` removed, 0 new ratchet violations).
- **PR Guards**: PASS (all 6 guards green).
- **Blockers**: None.
- **Status**: READY FOR REVIEW.

---

## 5. Effective Diff Against Latest `main` (`af57c7f6d6b796364d485688d35c1f5c871f1b04`)
`git diff --stat main..HEAD`:
```
docs/agents/DEV_LIST_CANONICAL_NODES_HANDOFF.md | 76 +++++++++++++++++++++++++
src/gaia_cli/commands/dev/list.py               | 20 ++++++---
tests/test_dev_list_fresh_checkout.py           | 49 +++++++++++++++++++++
3 files changed, 140 insertions(+), 5 deletions(-)
```
Zero files from PR #2427 or earlier Steward work were touched or reverted.
