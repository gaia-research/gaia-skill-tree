> Historical lane evidence. Status statements describe the inspected commit, not the final integrated tree. The parent recovery report records subsequent merges and holds.

# Badge policy CodeQL repair receipt

- Outcome: local security and regression verification passed; PR CI pending.
- PR: https://github.com/gaia-research/gaia-skill-tree/pull/2100
- Base: `dev/issue-resolver-fleet-2026-10-15` at `e95cdf6fa`.
- Head: `dev/fleet-badge-codeql-repair` at `9d3d232a75c5845d166af283febbe12fe81b9521` (pushed).
- Commit author: Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>.
- Worktree: `<badge feature checkout>` (clean).

## Finding and patch

CodeQL alert 105 on integrated #2096 identified the `gaiaskilltree.com` substring check in `scripts/badge_policy.py::normalize_prior_items`. Attacker-controlled upstream issue or PR title/body text could falsely mark an unrelated URL as a Gaia reference via hostname prefixes/suffixes, userinfo, path, query, or fragment. This influences attribution, downstream comment inspection and the campaign-attribution component of approval provenance; it is not SSRF and does not by itself bypass recorded human approval or authenticated maintainer-comment gates.

The narrow shared repair parses intact URL/reference tokens with `urllib.parse.urlsplit`, permits HTTP(S) or scheme-less references only, rejects credentials and invalid ports, and requires exact `gaiaskilltree.com` / `www.gaiaskilltree.com` hosts (including the equivalent DNS trailing dot). Balanced Markdown outer markup is handled without splitting host/userinfo/path boundaries. Known campaign authors and explicit `Gaia Skill Tree` name references preserve their prior behavior. Prior items remain conservatively represented in receipts; no outreach restrictions are loosened.

Changed files: `scripts/badge_policy.py`, `tests/test_badge_policy.py`. No registry, schema, workflow, outbound campaign data, main branch, or issue-state changes.

## Verification

1. Original reproduction: 20 malicious-reference cases failed on the unpatched tree while legitimate controls passed.
2. Syntax/import: `python -m py_compile scripts/badge_policy.py tests/test_badge_policy.py` passed.
3. Security + legitimate workflows: `python -m pytest tests/test_badge_policy.py tests/test_badge_reconcile.py tests/test_plan_badge_provisioning.py -q` — **283 passed**, synthetic and network guarded. Includes real-site prior-contact dispatch refusal and spoof-site inability to satisfy campaign-attribution for recorded approval through reconcile / approval evaluation / dispatch evaluation.
4. Patch hygiene: `git diff --check` passed; worktree clean after commit.
5. Independent review: recovery lead inspected source and direct callers before and after the patch. The reviewer identified missing Markdown-wrapped bare-domain compatibility; implementation and regression controls were corrected. Independent helper + actual normalization probes confirmed six legitimate and six malicious inputs; evidence: `./badge-independent.log`.
6. GitHub: PR description re-read and confirmed exact newlines/body. Author identity, branch scope, PR guards, skill quality, fast-track checks, and schema/DAG/integrity all passed. Only the Python Package `Test, Build, and Smoke Test` job remained running in its Full tests step (run `38761171070`) when handed back to the parent for shared CI monitoring. CodeQL has no check attached to this dev-to-dev PR; confirm alert clearance on the integration PR. No local CodeQL analyzer was run.

## Integration

PR #2100 is open, targeting the existing fleet integration branch. Parent recovery lead owns final CI review and merge-commit integration. No merge performed by this worker; no founder decision required for this scoped repair beyond final integration-to-main approval.
