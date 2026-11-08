# Gaia Security integration handoff
Date: 2026-11-08. Review proposal only; no merge or deployment authorized.

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

## 4. Validation evidence
- `PYTHONPATH=src python3 -m pytest tests/test_security_scanner.py -q`: **24 passed**, 0.18s on Termux/Python 3.14.6.
- `python3 scripts/check_security_dispositions.py`: **39 rows passed** count/shape/reviewed-source-byte checks. The check explicitly does not authenticate reviewer identity/scanner authority.
- `python3 scripts/check_rank_vocabulary.py`: **0 hard violations**; existing allowlisted vocabulary warnings retained.
- `python3 scripts/pr_guards.py --base origin/main`: **rank-vocabulary and lexicon passed**, including 42 lexicon self-tests, 0 failures.
- Native central baseline invocation: `gaia_security scan --repo gaia-research/gaia-skill-tree --path <checkout> --scanners gitleaks,osv-scanner,trivy --include-github-api`. It completed the native scanners and CodeQL API ingestion; Dependabot API was unavailable/disabled, so overall CLI returned **2/incomplete**, correctly.
- Baseline telemetry: Gitleaks working-tree **150 candidates** (local binary version unreported), OSV 2.7.0 **110 advisory records**, Trivy 0.76.2 misconfiguration **0 candidates**, CodeQL API **1 open alert**. Counts are time/scope specific. All **224 deduplicated baseline findings remained pending validation**; none were auto-dismissed/accepted. Existing possible secrets and private evidence were NOT published or altered.
- Founder-directed final `reviewer-shared` (`openai-codex/gpt-6.1-terra`, high, read-only) marked this integration **READY FOR REVIEW**, with no blockers in inspected source/tests/policy/handoff. Review did not independently rerun tests or inspect all references (search tools unavailable). No approval to merge or deploy is implied.
- Hosted native CodeQL (Actions, JavaScript/TypeScript, Python), vocabulary/lexicon PR guards, branch scope, author attribution, graph validation and skill quality gates passed on implementation commit `e2c7c6281a7b5756d66f0104741eb69d2e485e7a`. The [Python package run 42486164856](https://github.com/gaia-research/gaia-skill-tree/actions/runs/42486164856) subsequently **failed**: **8,382 passed, 5 skipped, 1 failed**, in `test_trusted_certificate_sends_one_bearer_request_and_ignores_proxy_environment` (`tests/steward/prmaintenance/test_readiness_safeguards.py`). The loopback HTTPS probe raised `CoordinationError`; package/full-suite stages did not complete. The test and transport implementation are byte-identical to base `3778d37bfcf93f25174c528cde78e20151ac21ef` (Git blob IDs `907966a820a37d7717e455d8a6d11caf3a57b33c` and `13f9d4fe946c77ef0a5bee25cd77f7e12aa893b5`). Local baseline reproduction stopped in fixture setup because the OpenSSL executable is unavailable; the same runtime failure is **not** claimed reproduced locally. Root cause remains unresolved. No gate, timeout, TLS control or production code was changed to hide it.
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
Privately triage existing scanner candidates and dependency graphs; coordinate any validated updates through authorized Steward work, batching compatible fixes into one integration PR per run. Historical findings are not reclassified by this PR. Final shared review and native CodeQL passed, but the Python package CI failure above remains an unresolved gate: **handoff status BLOCKED**. A repository owner must investigate the unchanged loopback-TLS test on a supported runner, then complete all package/full-suite/build gates. No bypass, speculative out-of-scope repair or merge requested.

## 9. GitHub configuration changes awaiting approval
**NOT executed.** For founder consideration only:
```bash
printf '%s\n' '{"security_and_analysis":{"secret_scanning_push_protection":{"status":"enabled"}}}' | gh api --method PATCH repos/gaia-research/gaia-skill-tree --input -
gh api --method PUT repos/gaia-research/gaia-skill-tree/vulnerability-alerts
```
First blocks recognized secret pushes; second enables native alerts, **not** automatic update PRs. Recheck eligibility and existing policy. Any reversal/disable operation needs separate approval. No branch protection or existing security-control mutation was performed.
