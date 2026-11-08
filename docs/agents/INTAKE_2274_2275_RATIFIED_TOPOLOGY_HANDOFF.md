# PR #2303 Replacement Handoff: Ratified Intake Batches for #2274 & #2275

**Date**: 2026-11-09  
**Branch**: `dev/intake-2274-2275-ratified-topology`  
**Supersedes**: `review/meta/intake-2274-2275-ratified-topology` (PR #2303)  
**Base**: `main` (`af57c7f6d6b796364d485688d35c1f5c871f1b04`, post-PR #2427)  
**Status**: READY FOR REVIEW  

---

## 1. Context and Branch-Scope Resolution
PR #2303 placed intake batch files under `registry-for-review/skill-batches/` on branch `review/meta/intake-2274-2275-ratified-topology`.
Under `.github/workflows/branch-scope.yml`, the `review/meta/` prefix only allows changes to `registry/` (excluding schema), `docs/`, `skill-trees/`, `evidence/`, and `*.md` files. This triggered a CI failure on `branch-scope`.

To resolve this without weakening branch protection, this replacement branch `dev/intake-2274-2275-ratified-topology` was created fresh from latest `main`. The `dev/` prefix is correctly classified as unrestricted in `branch-scope.yml`, fully permitting `registry-for-review/` intake batches.

The original branch `review/meta/intake-2274-2275-ratified-topology` is preserved (not deleted) as required by intake traceability. Original PR #2303 is kept open until this replacement PR is authorized.

---

## 2. Byte-Identical Batch File Transfer & Digest Verification
The two approved batch files were transferred byte-identically with no alterations:

1. **Intake #2275**:
   - Path: `registry-for-review/skill-batches/content-2f79d53f0c3459290085511633f0e5680a1e4fe1d9a395912338c017aa59aa0b-from-file.json`
   - File SHA-256: `a6bbb1e9d76d1c391e6af3ab53a04eba9521752b67d1c1b524b382525c1a1b72`
   - Target Skill: `mutation-based-test-adequacy` (fusion of `automated-testing`, `verification-before-completion`)
   - Upstream author: `timini`
   - Approval Workflow: `Intake Approval` [#42212983779](https://github.com/gaia-research/gaia-skill-tree/actions/runs/42212983779)
   - Immutable artifact: `gaia-intake-topology-2275-42212983779-1`
   - Issue revision SHA-256: `59d51bd4332a40c448e24a638c1d4693ebed839a3d66a4d912bd82b0c084361e` (body untouched)

2. **Intake #2274**:
   - Path: `registry-for-review/skill-batches/content-8963e6359eb6d3eb15e967744fa579b3dbb6186ced669756e76b52283732ac29-from-file.json`
   - File SHA-256: `a25efb1c36c23d735a7e446e84a9b01b6d1bb4ed556f6db81125cf0e1089989a`
   - Target Skill: `verified-adaptive-explanation` (fusion of `audience-model`, `code-explain`)
   - Upstream author: `mizchi`
   - Approval Workflow: `Intake Approval` [#42212853588](https://github.com/gaia-research/gaia-skill-tree/actions/runs/42212853588)
   - Immutable artifact: `gaia-intake-topology-2274-42212853588-1`
   - Issue revision SHA-256: `51a31f314aaf5d49da4552a3e2a4992e8b68624f3b48ae02fbc806a0b51d1869` (body untouched)

No issue bodies were edited, preserving the immutable issue body SHA-256 hash required by `.github/workflows/intake-approval.yml`.

---

## 3. Invariant & Steward Preservation
Current `main` at `af57c7f6d6b796364d485688d35c1f5c871f1b04` (post-PR #2427) is strictly preserved:
- No files in `registry/nodes/`, `registry/named/`, `founder/`, `src/`, or `tests/` were touched.
- No evidence is ingested and no canonical registry nodes are mutated.
- Zero merge conflicts against latest `main`.

---

## 4. Verification Evidence
1. **Intake Validation**:
   - `python3 scripts/validate_intake.py`: PASSED (all batch files satisfy schema and structure).
2. **PR Guards**:
   - `python3 scripts/pr_guards.py --all`: ALL PASSED (HTML sink, rank vocabulary, taxonomy authority, version stamp, lexicon, license).
3. **Branch Scope**:
   - `dev/` prefix complies with `.github/workflows/branch-scope.yml` unrestricted prefix policy.

---

## 5. Review & Merge Readiness
- Blockers: None.
- Status: READY FOR REVIEW (pending independent Luna review).
