# Security policy

## Governance
[Gaia Security](https://github.com/gaia-research/gaia-security) is the canonical Gaia Research security governance, scanner-profile and vulnerability-management reference. Skill Tree retains repository-local execution, native GitHub integrations, ownership and review gates.

## Report privately
Use [GitHub Private Vulnerability Reporting for Skill Tree](https://github.com/gaia-research/gaia-skill-tree/security/advisories/new). This channel is enabled. For ecosystem-wide concerns, prefix the private report with the affected project. Gaia Security's own private reporting is pending founder approval; use this existing private route in the interim.

**Do not post exploitable details, live credentials, user data or sensitive security evidence in public issues, PRs or gists.** Provide a minimal isolated synthetic reproduction, affected revision, impact hypothesis and redacted evidence privately. Do not test production destructively or access another user's data.

## Existing controls (preserved)
- GitHub CodeQL **default setup**, default query suite, remote threat model, weekly schedule, Python / JavaScript-TypeScript / Actions categories; recent main analyses verified through GitHub APIs. No duplicate CodeQL workflow is added.
- Named-skill defensive analyzer (`src/gaia_cli/securityScanner.py`) flags shell execution, destructive filesystem actions, outbound destinations, prompt-injection patterns and credential harvesting. Static patterns are defense in depth, not proof that a skill is safe.
- Model-format trust guidance (`docs/trust/security-guidelines.md`) and pickle-reference guards; use reviewed safer model formats rather than untrusted pickle deserialization.
- HTML sink checks and historical credential-disposition integrity (`scripts/check_html_sinks.py`, `scripts/check_security_dispositions.py`).
- Existing branch scope, metadata/Verifier, author identity and CODEOWNERS gates; Steward mutation-boundary, browser-sink and secret sensors. Existing locks and authority boundaries are not changed.

## Vulnerability lifecycle
Detection -> six-point evidence-based validation -> explicitly authorized remediation -> regression tests and re-scan -> independent PR review. Scanner output alone does not establish exploitation, justify dismissal, or authorize code changes, settings changes, merge or deployment. Unknown findings remain pending.

Follow Gaia Security's disclosure, severity, triage and remediation standards while preserving this repository's stricter existing controls. No paid security services or new automatic scanner workflows are activated by this policy.
