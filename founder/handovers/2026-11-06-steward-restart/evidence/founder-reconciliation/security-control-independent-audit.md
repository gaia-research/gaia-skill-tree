# Independent security-control audit #2283

## Status

**ACCEPT for this bounded slice only**: candidate `166e85514e3cd35d1c4e9cba506b1bb0560661f4` versus baseline `d694986b865e158e21c613683021a9b7822f945c`. No actionable defect established in the 23 controls, supported mirror parity, or examined selection/wrapper compatibility. This is not acceptance of the separately assigned 39-row inventory review, issue closure, alert dismissal, integration, or live ledger authority.

HEAD was the specified detached SHA; `git status --short` was empty. Runtime environment exposed `PI_MODEL=gpt-6.1-terra`; provider and high reasoning setting were not independently exposed by the inspected variables, so the requested exact model configuration is not independently attested. No nested agents were used.

## Scanner proof: independently reconstructed 23 controls

Loaded the baseline sensor directly from Git into an in-memory module and compared `_findings` to the candidate, with fresh deterministic synthetic inputs independently constructed from the pattern families and claimed outcomes. Checked proof has exactly 23 controls; each row below matches its claimed baseline/candidate count, family identity where applicable, and absence of its generated value in serialized output for both versions. The two placeholder rows do not claim a `sanitized` field in the proof; it was additionally checked here. Counts alone do not establish credential issuance or semantic safety.

| # | Case | Path | Baseline / candidate | Result |
|---:|---|---|---:|---|
| 1 | AWS access key | src | 1 / 1 | pass |
| 2 | AWS access key | tests | 1 / 1 | pass |
| 3 | GitHub classic | src | 1 / 1 | pass |
| 4 | GitHub classic | tests | 1 / 1 | pass |
| 5 | GitHub fine-grained | src | 1 / 1 | pass |
| 6 | GitHub fine-grained | tests | 1 / 1 | pass |
| 7 | Anthropic | src | 1 / 1 | pass |
| 8 | Anthropic | tests | 1 / 1 | pass |
| 9 | OpenAI | src | 1 / 1 | pass |
| 10 | OpenAI | tests | 1 / 1 | pass |
| 11 | Slack | src | 1 / 1 | pass |
| 12 | Slack | tests | 1 / 1 | pass |
| 13 | private-key header | src | 1 / 1 | pass |
| 14 | private-key header | tests | 1 / 1 | pass |
| 15 | Google API key | src | 1 / 1 | pass |
| 16 | Google API key | tests | 1 / 1 | pass |
| 17 | unrelated dummy comment | tests | 0 / 1 | pass |
| 18 | unrelated placeholder comment | tests | 0 / 1 | pass |
| 19 | unrelated not-real comment | tests | 0 / 1 | pass |
| 20 | unrelated canary comment | tests | 0 / 1 | pass |
| 21 | unrelated neighboring value | tests | 0 / 1 | pass |
| 22 | existing in-match example | tests | 0 / 0 | pass |
| 23 | existing in-match example | src | 1 / 1 | pass |

All 23 passed; no candidate values were printed. These checks exercise `_findings` in memory, not a full-fleet scanner or canonical run. Original inventory rows were deliberately left to the other reviewer.

## Full supported mirror manifest

Inspected `scripts/sync_agent_skill_mirror.py` and independently walked both trees with its actual `fnmatchcase` and directory-prefix exclusion semantics: `skill-creator/**`, `**/__pycache__/**`, `**/*.pyc`. Computed SHA-256 for each supported file and compact UTF-8 JSON of sorted `[relative-path, content-sha256]` pairs. Canonical `.agents/skills` = **224**, mirror `.claude/skills` = **224**; missing **0**, mirror-only **0**, changed **0**. Canonical manifest digest **`8d2debc9dd3b57fb40822744e1bb5df95835dee3ce277c50805dadc25cb8b6dc`**, matching `docs/agents/security/2283-scanner-proof.json`. These are supported file contents, not excluded locally owned files or a claim about filesystem metadata.

## Source provenance and compatibility

- Local Git confirms introduction commit `3e9e33820c833fb2cf10a9ad31024c63590b83b7`; the lock hash is not an upstream commit attestation. The upstream extraction commit was not present in local Git (`git cat-file -t` failed), so I independently fetched public official GitHub commit metadata and raw source read-only. Commit `325aeaf239808a0a8a763fe328e1dc1c3e2351df`, parent `972f5b18bea2b1b024d08dfc2ad9f378cc237fd3`, is titled “Organize skill script support modules”; its metadata identifies parser and validator moves as renames from root to extracted paths.
- Official extracted `live/event-validation.mjs` matches local byte-for-byte, SHA-256 `c0ee57b8306f8b1f31b00961017c849b7f352887bd8c889981805e14b8d2e63c`. Official extracted insert helper and vocabulary also match local byte-for-byte (respectively `c86839fc9be98eadc0ff6afaa6ab010a7539e9af77e8deeba898cb93f7f311f4` and `0a2c5278382906b3b459f268ed40f7b04bc607f88df9133f6d681e94929d2858`). The extracted parser differs from official and baseline root only by calling a new quoted-key unquoting helper; official hash `1f9e2ee4952dd7cd2da3fbfb90a8696ef848872691f7bf2498372faf2e6b3196`, local hash `096747b1225f0b78f6fe155477324c592f4fc38021b7007177e70b2dc55df588`.
- Baseline root validator versus selected extracted validator differs only in insert import path and factoring the action list into vocabulary. Baseline root insert helper equals extracted insert helper; all 12 action values and order agree. Root wrappers retain parser exports `parseDesignMd`, `assessCoverage` and validator exports `VISUAL_ACTIONS`, `validateEvent`. Local `live-server.mjs` imports both root wrappers; extracted manual-edit route imports the extracted validator. This supports the selection for those consumers, not exhaustive browser compatibility.
- Public official metadata for `e2ff625b6371c3f05a31e576fe9e7d063bcb112b` describes a Rust engine replacing scripts and the JS detector; its returned first 300 file records include 230 Rust/Cargo paths. Official metadata also identifies observed upstream `5af4319c4e7a7ee3e5e2b9fe899bcfb21c6190cb`. The newer cohort is not demonstrated drop-in compatible; it was not installed or substituted. Metadata page length is not a complete upstream change inventory.
- All five cached official test originals match their recorded hashes and, independently, freshly retrieved official raw bytes at the extraction commit. Cached adaptations equal originals after only the recorded import-prefix rewrite. I independently created temporary adaptations pointing at **this review checkout**, not the completed builder checkout, and ran `node --test --test-reporter=tap`: **42 passed, 0 failed, 0 skipped** under Node v24.17.0. No packages installed. Temporary files were removed. The cached snapshot provenance is independently corroborated for these five test files by this fresh public fetch.

## Verification limits

No 39-row/original-inventory audit, live scanner, ledger, issue operation, issuer contact, credential validation, rotation, policy activation, tracked edit, push or merge was performed. No browser, full live-server, Node 18, Windows, or real-hardlink platform test is claimed. Cached tests and examined module comparisons are proportionate compatibility evidence, not exhaustive proof for every consumer or future source change. The upstream GitHub fetch is source retrieval, not issuer or credential verification. Prior independent reviews cover the checker fixes and record remaining separate platform limits. `rg` was unavailable in this Termux environment (exec format error); scoped `grep` and Git/source comparisons were used instead.
