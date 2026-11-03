Source: https://github.com/gaia-research/gaia-skill-tree/issues/2148#issuecomment-6412751598

## Founder decision (2026-10-26): Gaia Frontier architecture, Yggdrasil IV handoff, and cleanup authority

**Decision: LOCKED.** Name the outward-facing ecosystem intelligence capability **Gaia Frontier**. Sol leads its initial, genuinely invocable agentic scaffolding as a bounded lane of the **existing** Yggdrasil IV campaign under RFC #2148 and draft integration PR #2151 (`dev/yggdrasil-iv`). This is authorization for implementation/engineering within existing gates, **not** authorization to change published trust, stars, Origin, or canonical claims.

### Canonical responsibility boundary

- **Gaia Frontier DISCOVERS:** Explore relevant *external* AI/agent ecosystems using the established Curation Core, `/gaia-full-pipeline`, crawlers, `/ev-scout`, and evidence pipeline. Produce source-backed discovery candidates for possible skill intake **and** challenger leads concerning existing Gaia capabilities. It is the home for outward-looking intelligence, not a new copy of each existing crawler or verifier.
- **Gaia Meta EVALUATES:** `/gaia-meta-audit` does prioritized triage; `/gaia-meta-sweep` appraises the tree and proposes rebalances; `/gaia-audit` conducts focused independent verification. Evaluation is not canonical publication.
- **Gaia Steward MAINTAINS:** Reactive governor of **tree-related observations, verified challenges and authorized maintenance**. It does **not** initiate general outside-the-tree scanning, speculative competitor hunts, or a new crawler programme. On *independently verified* challenges, retain D8's bounded, two-sided release/upstream monitoring and independently reproducible Class B *technical challenge-status closure only*. Class C still governs assertions, numbers, grades/stars, Origin and policy.
- **Governance DECIDES:** L4 skill/topology intake gates and Yggdrasil IV founder gates remain authoritative. Unverified challenger leads must never appear as verified public challenges or cause published numeric/Origin changes.

**Principle:** Frontier discovers. Meta evaluates. Steward maintains. Governance decides.

### Distinguish external challenger discovery from skill intake

Ordinary Curation Core `discovery-packet-v2` expects an actually fetched upstream `SKILL.md`; a native model/platform/CLI/API capability may not have one. Do **not** fabricate `SKILL.md`, force it into the named-skill intake, or weaken L4.

Provide a separate, versioned, validated **challenger-lead packet**, without a canonical trust assertion, containing at least: candidate identity and exact source/provenance, observed time and upstream version/SHA where possible; native or installable capability type; specific claim, task and comparator, possible affected named/generic skill; preliminary evidence and limitations; dedupe; proposed independent test; and a traceable disposition/handoff. Use a lifecycle like `observed → candidate → independently verified | rejected | deferred`. Only independently verified relevant challenges cross into the public challenge ledger and reactive Steward watch. Similarity, adoption counts, vendor marketing and model confidence remain leads, not proof.

### Authorized scope for Sol

1. **Continue, don't restart** the active Sol-led `/gaia-orchestrator` campaign on #2151, preserving already integrated work, active independent review and urgent engine/receipt/watcher blockers. Add a bounded **Frontier foundation and challenger handoff lane**.
2. Define one clear canonical ownership/contract document and connect existing discovery → Meta triage/focused evidence verification → challenge admission → Steward event handling. Prefer existing skills/CLI/provenance machinery.
3. Ship a *working, invocable* `/gaia-frontier` skill (with matching `.agents`/`.claude` mirrors), explicit user-invoked bounded discovery and challenger-reconnaissance modes, and examples. Compose existing `/gaia-full-pipeline`, `/ev-scout`, `/ev-pipeline`, `/gaia-meta-audit`, `/gaia-meta-sweep` rather than cloning them. Add specialized helpers only if real reusable behavior requires them.
4. Implement the challenger packet schema/validator/dedupe and receipt, and a reliable handoff to existing downstream verification/Meta triage. Show **one read-only end-to-end vertical slice** for an external non-`SKILL.md` native capability potentially challenging a Gaia skill. Independent checks must distinguish a substantiated challenge from weak similarity, vendor claims, duplicates, outages and unrelated features. Example Graphify versus Graft is an investigation, never a presumed verdict.
5. Prove the skill can actually be invoked agentically, packets can be consumed without manual glue, statuses/authority cannot be forged, and the entire flow leaves canonical score/rank/evidence/Origin untouched. Document limited search coverage, run budgets, provenance, independent review and clear next steps. Broad always-on exhaustive ecosystem scanning is **not** a prerequisite; expansion is separately reviewed.

### ADDITIONAL founder authorization: architecture simplification / trim the fat

Sol is **explicitly authorized to refactor, consolidate, retire, or remove redundant implementation paths, duplicated agent workflows/skills, stale instructions, dead adapters, and obsolete scaffolding** where the new Frontier/Meta/Steward division or Yggdrasil IV implementation demonstrably supersedes them. This is a real engineering-cleanup mandate, **not merely a documentation suggestion**, and ordinary non-consequential cleanup does **not** require repeated founder approval.

**Required discipline:** Inventory the overlapping paths, identify the surviving canonical owner, document why each removed/redirected path is superseded, preserve supported behavior through a migration/compatibility plan where needed, replace rather than multiply entry points, update both skill mirrors, add focused regression tests and receipts, and ship bounded reviewable PRs into the existing integration branch. Prefer deletion over leaving confusing duplicate active workflows, but preserve historical evidence/decision trails.

**Limits:** Cleanup cannot silently delete historical evidence, canonical skills, audit/timeline records or approved public behavior; break active user-facing invocations without an intentional migration; bypass independent review; change policy/Trust Magnitude/grades/stars/Origin; cross schema/canonical migration publication, pilot, final `main` merge, production rollout or RFC closure founder gates. Surface any genuinely consequential deprecation or migration decision with impact/rollback proof for founder approval rather than interpreting this cleanup mandate as blanket permission.

### Definition of done (Frontier lane)

- Architecture ownership is unambiguous; Steward has no general external-scan execution route.
- `/gaia-frontier` exists, works through the standard invocation surface, and has verified mirrors/examples.
- Schema-valid challenger packets, dedupe, source/verification receipts and safe handoff are exercised with positive and negative fixtures including non-installable platform-native capabilities.
- Distinct unverified-lead vs independently verified public-challenge states are enforced; no canonical mutation is permitted by Frontier/Steward handoff.
- Obsolete/conflicting entry points are cleaned up or explicitly deferred with rationale and compatibility plan; tests and independent review pass.
- Deliver all of this under #2151, preserving the ratified Yggdrasil IV P3–P5, pilot, final `main` merge and RFC closure gates.

**This decision modifies Sol's active execution scope; it is not a claim that Frontier is already built or that Yggdrasil IV has shipped.**
