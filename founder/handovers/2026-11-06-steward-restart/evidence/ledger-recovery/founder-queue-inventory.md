## Read-only inventory — tracking issue #2283

**Not adjudicated.** The 39 `credential_leak` entries are **unverified exposure / detector findings**, not confirmed secrets. The four `issue_founder_decision` entries are **pending founder decisions**, not ratified dispositions. No secret values or source excerpts are included. This inventory does not decide exposure, false positives, priority, remedy, or closure.

### Identity and count checks

- Checkout is **not on the requested stable integration root**: branch `dev/steward-campaign-2026-11-05`, HEAD `d9a39c1cdbdd0efabebbf6076c9ff6fff8674f0f`. The worktree also has untracked `.pi/delegate/`, `.pi/probes/`, and `.pi/tasks/`; I left them untouched.
- `.gaia/steward/debt.json`: 376 total entries; **43 open Class C** entries—39 `credential_leak` and 4 `issue_founder_decision`.
- Receipt run ID: `steward-20261104T172307Z-5c244581790fe867`; result `debt_reported`; receipt reports 43 Class C entries.
- No live `gh issue read` was performed. Thus issue #2283’s current live state is unverified.

**Source fingerprints**

- `.gaia/steward/debt.json`: `c7ea88b223ece4f10084dded2219ce03ba55d1c92b49d4cd7d4f9af1cdb3a222`
- `.gaia/steward/receipts/steward-20261104T172307Z-5c244581790fe867.json`: `956eee1f4f96721af3126b743d40ac5946ee9820eb062f382930c4bc2d6784d5`
- `founder/steward/routine-coverage.json`: `b11fc4348cca49652e9684bf9d7c2e022e5940f94f0a5ad67a519c6b3b3fa16b`
- All 43 rows remain marked `open` in the debt ledger. Provenance below refers only to the ledger’s detector finding line numbers and pattern categories; no finding contents are reproduced.

### Compact reusable decision menu — not a recommendation or ratification

- **Credential detector findings:** pending founder review; this inventory makes no determination about exposure or false positive.
- **Issue founder decisions:** pending founder decision; this inventory does not select or ratify an option.

### Inventory

| Debt ID | Subject path / issue | Routine IDs | Nonsecret provenance; detector finding / unresolved status |
|---|---|---|---|
| `debt:credential_leak:agents-skills-firecrawl-skill-md:dd0fc386f410185b` | `.agents/skills/firecrawl/SKILL.md` | 14, 16 | `debt.json` finding lines 256, 286; categories: credential-assignment, bearer-token. Unverified detector finding; open. |
| `debt:credential_leak:agents-skills-impeccable-scripts-detector-engine:7c8824c086679135` | `.agents/skills/impeccable/scripts/detector/engines/visual/screenshot-contrast.mjs` | 14, 16 | `debt.json` line 117; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:agents-skills-impeccable-scripts-live-browser-js:5f45d00d7f30b9c6` | `.agents/skills/impeccable/scripts/live-browser.js` | 14, 16 | `debt.json` lines 22, 9584, 9585; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:agents-skills-impeccable-scripts-live-complete-m:0b64558129c498be` | `.agents/skills/impeccable/scripts/live-complete.mjs` | 14, 16 | `debt.json` line 63; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:agents-skills-impeccable-scripts-live-manual-edi:a972d25ee1973c95` | `.agents/skills/impeccable/scripts/live/manual-edit-routes.mjs` | 14, 16 | `debt.json` line 261; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:agents-skills-impeccable-scripts-live-poll-mjs:bd8dca1fcdf7945b` | `.agents/skills/impeccable/scripts/live-poll.mjs` | 14, 16 | `debt.json` lines 121, 160; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:agents-skills-impeccable-scripts-live-server-mjs:a671be5f79c2a3ff` | `.agents/skills/impeccable/scripts/live-server.mjs` | 14, 16 | `debt.json` lines 1758, 2213, 2312, 2315; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:agents-skills-impeccable-scripts-live-status-mjs:f32377b5380cfa3e` | `.agents/skills/impeccable/scripts/live-status.mjs` | 14, 16 | `debt.json` line 17; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-firecrawl-skill-md:54ae5604e12e2a9b` | `.claude/skills/firecrawl/SKILL.md` | 14, 16 | `debt.json` finding lines 256, 286; categories: credential-assignment, bearer-token. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-impeccable-scripts-detector-engine:1deecfb89c8de90c` | `.claude/skills/impeccable/scripts/detector/engines/visual/screenshot-contrast.mjs` | 14, 16 | `debt.json` line 117; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-impeccable-scripts-live-browser-js:4560dad03a613faa` | `.claude/skills/impeccable/scripts/live-browser.js` | 14, 16 | `debt.json` lines 22, 9584, 9585; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-impeccable-scripts-live-complete-m:d8222ce8d9bd957f` | `.claude/skills/impeccable/scripts/live-complete.mjs` | 14, 16 | `debt.json` line 63; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-impeccable-scripts-live-manual-edi:0801364f7f0e77a3` | `.claude/skills/impeccable/scripts/live/manual-edit-routes.mjs` | 14, 16 | `debt.json` line 261; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-impeccable-scripts-live-poll-mjs:f8f331ec1404ea92` | `.claude/skills/impeccable/scripts/live-poll.mjs` | 14, 16 | `debt.json` lines 121, 160; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-impeccable-scripts-live-server-mjs:4df9c2b6ff80b3e6` | `.claude/skills/impeccable/scripts/live-server.mjs` | 14, 16 | `debt.json` lines 1758, 2213, 2312, 2315; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:claude-skills-impeccable-scripts-live-status-mjs:04765e48ffb67e0b` | `.claude/skills/impeccable/scripts/live-status.mjs` | 14, 16 | `debt.json` line 17; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:docs-samples-registry-3d-fonts-html:412fc74a40db779e` | `docs/samples/registry-3d-fonts.html` | 14, 16 | `debt.json` lines 160–162; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:founder-handovers-2026-10-21-steward-issue-hygie:e8be47c2eebc4b65` | `founder/handovers/2026-10-21-steward-issue-hygiene-architecture.md` | 14, 16 | `debt.json` lines 392, 517, 518; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:founder-issues-json:b132c45b86c3ebcb` | `founder/issues.json` | 14, 16 | `debt.json` line 1 (two findings); credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:github-workflows-sync-artifacts-yml:b526f075e4ecd1e6` | `.github/workflows/sync-artifacts.yml` | 14, 16 | `debt.json` line 177; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:scripts-jev-ci-budget-py:86888e095876410e` | `scripts/jev_ci_budget.py` | 14, 16 | `debt.json` line 387; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:scripts-upstream-watcher-live-py:2393fe51171e5834` | `scripts/upstream_watcher/live.py` | 14, 16 | `debt.json` line 465; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:src-gaia-cli-auth-py:2ed435a394e19f87` | `src/gaia_cli/auth.py` | 14, 16 | `debt.json` lines 241, 405, 420, 436; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:src-gaia-cli-jev-py:74fbb7100ac456ad` | `src/gaia_cli/jev.py` | 14, 16 | `debt.json` line 634; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:src-gaia-cli-securityscanner-py:ba7fcb08fe3ef5c9` | `src/gaia_cli/securityScanner.py` | 14, 16 | `debt.json` line 513; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-issuehygiene-test-b-script-py:82d92c373e57e5b6` | `tests/steward/issuehygiene/test_b_script.py` | 14, 16 | `debt.json` lines 15, 248; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-issuehygiene-test-b5-identity-py:affc47d215e53abe` | `tests/steward/issuehygiene/test_b5_identity.py` | 14, 16 | `debt.json` line 15; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-issuehygiene-test-b6-census-live-p:ec37ccfcb574c2d1` | `tests/steward/issuehygiene/test_b6_census_live.py` | 14, 16 | `debt.json` line 219; bearer-token. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-issuehygiene-test-b7-scrub-py:c82313badc903f74` | `tests/steward/issuehygiene/test_b7_scrub.py` | 14, 16 | `debt.json` lines 31, 32, 34, 35, 37; categories: JWT, credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-issuehygiene-test-b8-census-py:055f6db7f83bf7eb` | `tests/steward/issuehygiene/test_b8_census.py` | 14, 16 | `debt.json` lines 94–96; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-issuehygiene-test-b8-refusal-py:100e8e97ff9a51ef` | `tests/steward/issuehygiene/test_b8_refusal.py` | 14, 16 | `debt.json` line 82; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-issuehygiene-test-e-steward-full-e:8dd6930a15057584` | `tests/steward/issuehygiene/test_e_steward_full_e2e.py` | 14, 16 | `debt.json` line 135; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-steward-test-desk-py:d1900b51970bdc61` | `tests/steward/test_desk.py` | 14, 16 | `debt.json` line 187; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-test-auth-py:edc1563abdfa70e4` | `tests/test_auth.py` | 14, 16 | `debt.json` lines 351, 366, 404, 418; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-test-badge-reconcile-py:062a191c5b535bb7` | `tests/test_badge_reconcile.py` | 14, 16 | `debt.json` line 861; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-test-curation-assessment-py:b8c7a3d24c6492cf` | `tests/test_curation_assessment.py` | 14, 16 | `debt.json` line 433; bearer-token. Unverified detector finding; open. |
| `debt:credential_leak:tests-test-curation-error-contract-py:30a58d0ac04e28de` | `tests/test_curation_error_contract.py` | 14, 16 | `debt.json` line 175; credential-assignment. Unverified detector finding; open. |
| `debt:credential_leak:tests-test-installability-py:50a878d42ae01243` | `tests/test_installability.py` | 14, 16 | `debt.json` line 125; bearer-token. Unverified detector finding; open. |
| `debt:credential_leak:tests-test-jev-py:29db1b7469907462` | `tests/test_jev.py` | 14, 16 | `debt.json` line 438; bearer-token. Unverified detector finding; open. |
| `debt:issue_founder_decision:q-08ecd62d:b46650ebeefbdb87` | Issue 1833 (question `Q-08ecd62d`) | 18 | Ledger target `issue-question/q-08ecd62d`; affected issue 1833; manifest digest `075f845d6da517d785dae90f4f16a909392c6ae12f9945d2e98efb5ff3dddd26`. Pending founder decision; open. |
| `debt:issue_founder_decision:q-2568173e:749fb275800fe372` | Issue 2002 (question `Q-2568173e`) | 18 | Ledger target `issue-question/q-2568173e`; affected issue 2002; same manifest digest. Pending founder decision; open. |
| `debt:issue_founder_decision:q-6720aecf:e5f9c70bc8f1e0c9` | Issues 2126, 2127 (question `Q-6720aecf`) | 18 | Ledger target `issue-question/q-6720aecf`; affected issues 2126, 2127; same manifest digest. Pending founder decision; open. |
| `debt:issue_founder_decision:q-bfd37238:ac2f25b1b6af9db6` | Issue 1835 (question `Q-bfd37238`) | 18 | Ledger target `issue-question/q-bfd37238`; affected issue 1835; same manifest digest. Pending founder decision; open. |

**Routine binding note:** credential findings are bound here to routines 14 and 16 because the coverage file associates `secret-scan` with both; issue-founder-decision rows map to routine 18, GitHub Issue Hygiene. Callers and broader impact were not traced; affected callers are **unknown**.