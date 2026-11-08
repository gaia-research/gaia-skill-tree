# Gaia Security integration handoff
Date: 2026-11-09. Reconciled against latest main (af57c7f6d6b796364d485688d35c1f5c871f1b04, post-PR #2427). Review proposal only; no merge or deployment authorized.

## 1. Architecture and implementation
[gaia-research/gaia-security](https://github.com/gaia-research/gaia-security) governs standards/profiles/validation contracts. Skill Tree retains scanning execution, GitHub-native alerts, Steward headquarters, existing ownership and authority gates. There is no new runtime dependency or duplicate scanner process.

## 2. Existing infrastructure discovered
Authenticated read-only GitHub reconnaissance verified CodeQL **default setup** (default suite, remote model, weekly; Python, JavaScript/TypeScript, Actions), recent main analyses on `3778d37bfcf93f25174c528cde78e20151ac21ef`, engine 2.27.4. Historical inventory: 50 alerts, 49 fixed and 1 open; these are scanner observations, not proven exploitation. Private Vulnerability Reporting and native secret scanning enabled; push protection and Dependabot alert/update features disabled. No Semgrep/Trivy/Gitleaks/OSV config or Dependabot YAML found before this mission.

Existing named-skill scanner, HTML/model-format guards, 39-row credential-disposition integrity gate, pip-audit collector, Steward security sensors, CODEOWNERS, branch/metadata/author controls and founder locks are preserved. Workflow scope/concurrency discipline is retained; timeout coverage is mixed, not silently changed.

## 3. Changes made
- Root SECURITY.md establishes central governance and the **existing enabled private Skill Tree disclosure route**. Gaia Security's own PVR is pending approval; it is not advertised as live.
- Test assertion uses exact extracted hostname equality; regression test covers lookalike hosts. This is a defensive test-precision improvement, not evidence that a production exploit was demonstrated.
- Optional asset-tool Pillow minimum aligned to `>=13.0.0`, including scripts/README.md. This reduces an old allowed version floor; it does not assert which version every existing environment has installed.
- This self-contained handoff. No workflow, native CodeQL configuration, lockfile, historical credential disposition or Steward lock changed.

### Complete Diff Against Latest `main` (`af57c7f6d6b796364d485688d35c1f5c871f1b04`)
`git diff --stat main..HEAD`:
```
SECURITY.md                                   | 21 ++++++++++
docs/agents/security/GAIA_SECURITY_HANDOFF.md | 55 +++++++++++++++++++++++++++
scripts/README.md                             |  2 +-
scripts/compress-assets.requirements.txt      |  2 +-
tests/test_security_scanner.py                | 11 +++++-
5 files changed, 88 insertions(+), 3 deletions(-)
```
Strictly 5 files in scope. Zero Steward files from PR #2427 (Class B 323 -> 191, 48 canonical repairs, 45 demotions) or earlier Steward work were touched or reverted.

### Commit Lineage and Byte-Identity
- `e2c7c6281`: initial implementation.
- `a916456be`: historical PR head that completed the 24m51s green hosted Python Package run ([42486942861](https://github.com/gaia-research/gaia-skill-tree/actions/runs/42486942861)).
- `abcfafbe7`: mechanical merge of latest `main` (`af57c7f6d6b796364d485688d35c1f5c871f1b04`, post-PR #2427).
- Reconciled commits update this documentation handoff only.
- The four code, dependency, and test files (`SECURITY.md`, `scripts/README.md`, `scripts/compress-assets.requirements.txt`, `tests/test_security_scanner.py`) are 100% byte-identical between historical head `a916456be` and current `HEAD` (zero diff across all four files).

## 4. Validation evidence
- `PYTHONPATH=src python3 -m pytest tests/test_security_scanner.py -q`: **24 passed**, 0.18s on Termux/Python 3.14.6.
- `python3 scripts/check_security_dispositions.py`: **39 rows passed** count/shape/reviewed-source-byte checks. The check explicitly does not authenticate reviewer identity/scanner authority.
- `python3 scripts/check_rank_vocabulary.py`: **0 hard violations**; existing allowlisted vocabulary warnings retained.
- `python3 scripts/pr_guards.py --base origin/main`: **rank-vocabulary and lexicon passed**, including 42 lexicon self-tests, 0 failures.
- Native central baseline invocation: `gaia_security scan --repo gaia-research/gaia-skill-tree --path <checkout> --scanners gitleaks,osv-scanner,trivy --include-github-api`. It completed the native scanners and CodeQL API ingestion; Dependabot API was unavailable/disabled, so overall CLI returned **2/incomplete**, correctly.
- Baseline telemetry: Gitleaks working-tree **150 candidates** (local binary version unreported), OSV 2.7.0 **110 advisory records**, Trivy 0.76.2 misconfiguration **0 candidates**, CodeQL API **1 open alert**. Counts are time/scope specific. All **224 deduplicated baseline findings remained pending validation**; none were auto-dismissed/accepted. Existing possible secrets and private evidence were NOT published or altered.
- Founder-directed final `reviewer-shared` (`openai-codex/gpt-6.1-terra`, high, read-only) marked this integration **READY FOR REVIEW**, with no blockers in inspected source/tests/policy/handoff. Review did not independently rerun tests or inspect all references (search tools unavailable). No approval to merge or deploy is implied.
- Hosted native CodeQL (Actions, JavaScript/TypeScript, Python), vocabulary/lexicon PR guards, branch scope, author attribution, graph validation and skill quality gates passed. While an earlier intermediate hosted run ([Python package run 42486164856](https://github.com/gaia-research/gaia-skill-tree/actions/runs/42486164856) on commit `e2c7c6281a7b5756d66f0104741eb69d2e485e7a`) encountered an isolated transient loopback HTTPS probe failure in `test_trusted_certificate_sends_one_bearer_request_and_ignores_proxy_environment`, the subsequent head run ([Python package run 42486942861](https://github.com/gaia-research/gaia-skill-tree/actions/runs/42486942861) on commit `a916456be5f6de07c9051288274938a04bbc83b4`) **passed completely in 24m51s** with all 14 checks green across the entire package, test, build, and smoke-test matrix. Targeted defensive scanner suite (`tests/test_security_scanner.py`) verified locally with 24 passed in 0.33s.
- Scanner JSON/Markdown stayed owner-only outside the repository. Native alert payloads/locations/credentials are deliberately absent from this public handoff.

## 5. Scanner coverage
|Tool|Observed execution|Limit|
|---|---|---|
|CodeQL|Existing successful main analyses/config checked; open-alert API ingested|Not run locally; PR/default-setup scans must re-evaluate proposed revision|
|Gitleaks|Working-tree native scan executed with central profile|Not full history; candidates require private triage|
|OSV-Scanner 2.7.0|Native dependency scan executed|Advisories/version constraints do not prove reachable exploitation|
|Trivy 0.76.2|Native filesystem misconfiguration scan executed|Not image/OS CVE coverage|
|Semgrep CE|Central profile supplied; host CE CLI unavailable|No claim of a Semgrep CLI scan here|
|Native named-skill scanner|Exercised by 24 passing targeted tests|Static detection does not prove skill safety|
|Dependabot|Disabled/unavailable API recorded|Held for founder decision, not silently enabled|

## 6. Security limitations
Business logic, authorization, dynamic host/agent permissions, prompt semantics, CI/build-time exposure and credential validity need independent investigation. Test paths and optional ML/development labels do not establish safety. No active production testing, alert dismissal or automatic fix authorization occurred.

## 7. Costs and execution requirements
No new subscription, cloud infrastructure, paid AI Scan or automatic target workflow. Local CPU/network and existing GitHub default setup are used. Public standard runners are normally free; future private/larger runners and artifact storage require budget review. Python CLI has no third-party runtime dependencies; native tools are separate.

## 8. Outstanding issues
Privately triage existing scanner candidates and dependency graphs; coordinate any validated updates through authorized Steward work, batching compatible fixes into one integration PR per run. Historical findings are not reclassified by this PR. With hosted Python package run 42486942861 green (24m51s), CodeQL passed, all 24 targeted tests passed, and clean reconciliation against latest main preserving all Steward improvements: **handoff status READY FOR REVIEW**. No bypass, speculative out-of-scope repair or merge requested.

## 9. GitHub configuration changes awaiting approval
**NOT executed.** For founder consideration only:
```bash
printf '%s\n' '{"security_and_analysis":{"secret_scanning_push_protection":{"status":"enabled"}}}' | gh api --method PATCH repos/gaia-research/gaia-skill-tree --input -
gh api --method PUT repos/gaia-research/gaia-skill-tree/vulnerability-alerts
```
First blocks recognized secret pushes; second enables native alerts, **not** automatic update PRs. Recheck eligibility and existing policy. Any reversal/disable operation needs separate approval. No branch protection or existing security-control mutation was performed.
