# zizmor high/high triage (advisory baseline)

Refs #2283. Measured 2026-11-08 on `dev/steward-campaign-2026-11-05` at `b9028e9a6`.

```bash
zizmor --offline --min-severity high --min-confidence high .github/workflows/   # zizmor 1.32.0
```

140 findings: `unpinned-uses` 112, `template-injection` 22, `excessive-permissions` 6.
`unpinned-uses` (tag instead of commit SHA) is a repository policy choice, not a per-site defect,
so it is counted and not triaged here. The other 28 are triaged by hand below.

zizmor stays **advisory** in `workflow-hygiene-guard.yml`. Nothing in this file changes a
Steward sensor, a census count or a workflow.

## Classes

- **TP**: real and worth fixing. The value reaches the shell unescaped from free-form input, the
  site contradicts a rule the repository already states, or a write grant reaches a job that does
  not need it.
- **Accepted**: the expansion or grant is real, but only write-access maintainers control the value
  or every job in the workflow needs the grant. No privilege is gained; fixing it is hardening.
- **FP**: the value cannot carry an injection. GitHub constrains its character set (login, repo
  `owner/name`), or the trigger fixes it (`ref_name` on a `push: [main]` workflow).

## Triage

| # | Location | Rule | Class | Reason |
|---|---|---|---|---|
| 1 | `benchmark-humaneval-ci.yml:84` | template-injection | TP | Free-form `inputs.datasetUrl` spliced into shell; use `env:`. Dispatch is write-access only. |
| 2 | `benchmark-humaneval-ci.yml:102` | template-injection | TP | Free-form `inputs.skillId` in shell. |
| 3 | `benchmark-humaneval-ci.yml:104` | template-injection | TP | Free-form `inputs.promptTemplate` in shell; a template containing `"` or `$(` also breaks the run. |
| 4 | `benchmark-humaneval-ci.yml:118` | template-injection | TP | `inputs.pendingScore` is `type: string`, not a number. |
| 5 | `benchmark-humaneval-ci.yml:120` | template-injection | TP | `inputs.scoreTolerance` is `type: string`. |
| 6 | `benchmark-humaneval-ci.yml:146` | template-injection | TP | `inputs.skillId` in a `gaia dev evidence` call under a `contents: write` token. |
| 7 | `benchmark-humaneval-ci.yml:172` | template-injection | TP | `inputs.skillId` inside a commit message string. |
| 8 | `benchmark-humaneval-ci.yml:178` | template-injection | TP | `inputs.targetBranch` in `git push`. |
| 9 | `branch-scope.yml:95` | template-injection | FP | `pull_request.head.repo.full_name` is `owner/name`, charset-constrained by GitHub. |
| 10 | `docs-cohesion.yml:307` | template-injection | Accepted | Label names are free text, but only write access creates labels (`labels-sync`). |
| 11 | `fast-track-ci.yml:79` | template-injection | Accepted | `github.base_ref` is a branch of this repo; only write access creates one. |
| 12 | `intake-approval.yml:74` | template-injection | FP | `github.actor` is a GitHub login (`[A-Za-z0-9-]`). |
| 13 | `intake-approval.yml:77` | template-injection | FP | `sender.login`, same charset. |
| 14 | `intake-approval.yml:95` | template-injection | TP | A **shell comment** contains `${{ inputs.base_ref }}`. Actions expands expressions before the shell runs, so the comment re-creates the free-form interpolation it says the step avoids. A value with a newline ends the comment and runs. Rephrase the comment without `${{ }}`. |
| 15 | `intake-approval.yml:306` | template-injection | FP | `github.actor`. |
| 16 | `intake-approval.yml:309` | template-injection | FP | `sender.login`. |
| 17 | `release.yml:9` | excessive-permissions | TP | Workflow-level `contents: write` reaches `test-python` and `validate-graph`, which install deps and run the full suite. Only `release` needs it. Scope it to that job. |
| 18 | `sync-artifacts.yml:270` (1) | template-injection | FP | `github.ref_name` under `push: branches: [main]` is always `main`. |
| 19 | `sync-artifacts.yml:270` (2) | template-injection | FP | Same expression, second occurrence. |
| 20 | `upstream-approve.yml:26` | excessive-permissions | Accepted | `issues: write`; all three jobs comment, label or close issues. Job-level scoping is hardening. |
| 21 | `upstream-approve.yml:27` | excessive-permissions | Accepted | `contents: write`; `approve` and `legacy-approve` push. `skip-child-gate-guard` may not need it (hardening). |
| 22 | `upstream-approve.yml:28` | excessive-permissions | Accepted | `pull-requests: write`; the approve jobs open PRs. |
| 23 | `upstream-approve.yml:974` | template-injection | TP | Free-form `inputs.issue_number` (`type: string`) written into shell and `$GITHUB_OUTPUT`; a newline can forge extra step outputs. |
| 24 | `upstream-approve.yml:975` | template-injection | FP | `github.actor`. |
| 25 | `upstream-approve.yml:978` | template-injection | FP | `sender.login`. |
| 26 | `upstream-reject.yml:8` | excessive-permissions | Accepted | `issues: write`; `legacy-reject` closes issues and `reject` overrides at job level. |
| 27 | `upstream-reject.yml:220` | template-injection | FP | `sender.login`. |
| 28 | `upstream-watcher.yml:53` | excessive-permissions | Accepted | `issues: write`; `watcher` files issues and `challenge-watch` overrides at job level. |

## Result

| Class | Count |
|---|---|
| TP | 11 |
| Accepted | 7 |
| FP | 10 |

Precision on the 28: 11/28 (39%) worth fixing; 18/28 (64%) describe something real. Every FP is
a GitHub-constrained value (`actor`, `sender.login`, `head.repo.full_name`) or a trigger-fixed
`ref_name`. None of the 11 TPs is reachable by a non-maintainer: every one needs
`workflow_dispatch` (write access) or is a least-privilege gap. They are hardening, not an open
exploit.

TPs worth routing (none is a `missing-timeout` debt, so none fits Steward routine 13 today):
- `intake-approval.yml:95`: one-line comment rephrase; contradicts the step's own stated rule.
- `upstream-approve.yml:974`: move `inputs.issue_number` to `env:`.
- `benchmark-humaneval-ci.yml` (8 sites): move every `inputs.*` to `env:`.
- `release.yml`: move `contents: write` from workflow to the `release` job.

## Proposed ratchet criteria (later step, not enabled)

1. Fix the 11 TPs first.
2. Record each FP and Accepted site in a committed `.github/zizmor.yml` `ignore` list, with a
   one-line reason per entry. Use no blanket audit disables.
3. Block on new `template-injection`, `excessive-permissions` and `dangerous-triggers` at
   `--min-severity high --min-confidence high`, against that config. A clean run is then the only
   passing state, so the same shrink-only property holds without a second baseline file.
4. Only after two consecutive weekly runs show zero unexplained new findings, and an independent
   reviewer has re-triaged a sample of at least 10.
5. Keep `unpinned-uses` advisory until there is a founder decision on SHA pinning: 112 sites, and a
   pinning policy needs an update mechanism (Dependabot `github-actions`) first.
