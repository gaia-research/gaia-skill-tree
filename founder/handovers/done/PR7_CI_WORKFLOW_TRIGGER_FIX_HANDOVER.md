# Handover: PR-7 — CI Workflow Trigger Fix

**Type:** Infrastructure  
**Branch:** `infra/ci-trigger-fix`  

## Context
Discovered during the merge of #690, the main "Test, Build, and Smoke Test" workflow did not trigger because the head commit did not match the path filters, even though the PR as a whole contained relevant code changes. 

## Objectives
1. **Update GitHub Actions YAML**: Modify the workflow file(s) (e.g., `.github/workflows/python-package.yml`) so the path filters trigger on `pull_request` rather than just `push`.
2. **Diff Evaluation**: By shifting to `pull_request`, GitHub Actions will evaluate paths against the full `base...head` diff, ensuring the suite runs if ANY commit in the PR touched a qualifying path.

## Definition of Done
- Workflow file updated to use `pull_request` trigger with the correct path filters.
- Verified that a dummy PR touching a `src/` file triggers the suite correctly.
