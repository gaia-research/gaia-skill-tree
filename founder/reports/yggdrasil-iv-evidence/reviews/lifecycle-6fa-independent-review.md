## Verdict: hold for repair and gated review

Reviewed detached HEAD `6fa482665f9733f33cb67637159dfe65ce54363f` against `bed78e716bc56d61cddc039c88ac95980be2ddf7`, including the earlier `70239bcee` and `3ae334cdd` history. The default path remains unavailable, and the tested index boundary strips contributor-supplied lifecycle metadata. A synthetic receipt-backed producer → serialized index → consumer route also worked.

**This is not production acceptance.** Two contract defects remain, and genuine provider, cross-surface, and founder visual gates remain held.

## Findings

1. **P2 — Baseline can contradict the Explorer’s fallback TM.**  
   `src/gaia_cli/lifecycleProjection.py:150-153`, `docs/js/trust-lifecycle.js:320-324`, `docs/js/trust-lifecycle.js:443-461`  
   The producer checks `trustMagnitude` but not `overallTrustMagnitude`. The browser’s later fallback contradiction check applies only to approved decisions, not current baselines. A synthetic consequence of TM 72 was accepted with `overallTrustMagnitude: 999`; the panel rendered baseline TM 72. The Explorer uses the latter fallback at `docs/js/skill-explorer.js:584`. Align the producer and both consequence kinds with the actual hero metric selection before enabling a provider.

2. **P2 — Browser accepts malformed v1 DTOs despite its fail-closed contract.**  
   `docs/js/trust-lifecycle.js:295-307`  
   Starting with a real synthetic producer DTO, deleting `pinnedSha` and `claimId`, deleting history receipt binding fields, changing the event date to `garbage`, or adding a resolution to a pending challenge each still produced a view model. These probes do **not** demonstrate authentication bypass: browser validation is expressly not an authentication boundary, and the ordinary index strips raw contributor payloads. They do demonstrate that malformed/contradictory published DTOs are not consistently rejected as documented. Validate required v1 shape and history consistency, or narrow the stated contract.

## Dynamic verification

- `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests/test_challenge_domain.py tests/test_lifecycle_projection.py` — **17 passed**.
- Generated the missing Class P files in this review tree with `python scripts/assemble_gaia.py` and `python scripts/generateNamedIndex.py`; then ran the challenge/projection and named-index frontmatter/index-generation classes — **23 passed, no skips**.
- `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests/test_named_skills.py` — **12 passed, no skips**.
- `node --test tests/test_trust_lifecycle*.js` — **11 passed**.
- Synthetic markdown through actual `load_named_skills` → `validate_and_group` → `write_index` → JSON: forged `trustLifecycle` was removed while Origin remained intact.
- Synthetic domain receipt and technical resolution through `write_index` serialization into the JS consumer: two history events survived; no approved rank was fabricated without a consequence source.
- Existing targeted tests cover foreign/duplicate challenges, altered receipt context and history digest, unsupported DTO version, scope mismatch, and strict materiality booleans. The additional malformed DTO probes produced finding 2.

## Old versus new Node coverage

The former 19 tests are **not equivalent** to the 11 current tests. Scoped/material challenges, resolution history, unknown consequence, escaping, absent payload, and basic wiring remain covered, though often less deeply. Old display-field “approval” tests are appropriately superseded by rejecting the old payload rather than authenticating names, URLs, or dates.

Not equivalently exercised in the current suite: upstream-superseded rendering, approved degradation detail, historical awards, broader unsafe-link and date cases, mobile CSS assertions, badge/region accessibility assertions, and the fuller Explorer structure checks. Some old states are deliberately unsupported by v1 rather than regressions; their removal still requires an explicit product/contract decision and replacement coverage where applicable. DOM/string assertions are not visual acceptance.

## Limits and integrity

No genuine production challenge or consequence adapter is configured; the ports exercised above are **explicit synthetic test ports**, not an issuer or human approval. Canonical CLI transaction and dual-history alignment remain unverified. Native `docs/named/index.html` → `openExplorer()` → `#se-tm` wiring was inspected and tested as code, but no browser interaction or rendered evidence was captured. Founder visual approval, genuine adapter security, coherent cross-surface publication, rollout, and merge remain held.

No network, models, agents, dependencies, refs, global configuration, or original worktree were touched. `LD_PRELOAD` was not changed. Final HEAD remained `6fa482…`; tracked working and staged diffs were empty, both hashing to the empty SHA-256. Class P generated files remain local and ignored.

🌱 graft saved ~59,166 tokens this turn (1 call).