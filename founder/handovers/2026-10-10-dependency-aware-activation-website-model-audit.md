# Founder Handoff — Dependency-Aware Skill Activation, Website Contract, and October Audit

**Date:** 2026-10-10  
**Status:** Founder direction / handoff, not implementation or acceptance  
**Canonical Skill Tree issue:** [#2063](https://github.com/gaia-research/gaia-skill-tree/issues/2063)  
**Skill Heaven owner:** [#199](https://github.com/gaia-research/gaia-skill-heaven/issues/199)  
**Console reference only:** [Skill Heaven PR #196](https://github.com/gaia-research/gaia-skill-heaven/pull/196)

## Founder decision

A skill is a capability, while its upstream execution stack is an implementation. Gaia must honestly expose prerequisites and installation side effects, obtain explicit consent before installing external dependencies, and support an ephemeral **Essence Mode** that adopts portable methodology with available tools and repository rules. An Essence run is not a native install or a claim of full parity. This release frontier is separate from #196 and may ship **ahead of the masterplans**.

**Additional non-negotiable:** Skill Tree itself, not only Skill Heaven, must house the dependency contract **both in canonical data models and on its public website**. Plain prose in a handoff or an installer warning alone is insufficient.

## Skill Tree responsibility: canonical model

Define backward-compatible, versioned typed metadata for each named skill/suite and its dependencies:
- identity, dependency type (CLI, local helper/script, runtime/library, harness feature, API/service, credential, hook), role (required, optional, alternative, native-only), environment and harness applicability;
- install provenance/source/version/constraint, scope and supported installation method, permission/privilege, network/data egress, license/monetary cost, credential prerequisites, disk writes, hooks/persistence, removal/rollback;
- evidence provenance and freshness, validation status, confidence, unknown/unverified markers, and explicit native/Essence capability limitations.

Separate **skill artifact installed**, **dependency available**, **runtime configured**, **capability verified**, and **portable Essence supported**. Trust grade/rank is not an installability grade. Unknown must never silently become none, approved, safe, or ready. Existing records without metadata remain legible and explicitly unaudited. Do not mutate rankings merely to fix packaging.

The canonical registry schema must feed validators, CLI/installer preflight, generated JSON/public API, site build and both Python/TypeScript consumers. Avoid divergent handwritten website metadata. Add model serialization, migration/backward-compatibility and generation parity tests.

## Skill Tree responsibility: website

On named-skill details and appropriate suite pages, expose:
- dependency summary, current audit status, platform/harness compatibility and verified installation route;
- requirement grouping (required / optional / alternative), third-party links, exact versions when verified;
- meaningful warnings before install: cost, key/auth, network data exposure, system modifications, privileged commands, persistent hooks, uninstall/rollback;
- native versus session-only Essence explanation, unavailable/unsupported/unknown states and factual reductions;
- provenance/freshness and a route to report stale or missing dependency metadata.

Retain progressive disclosure for dense dependency lists. Site labels must never imply that reading a `SKILL.md` or successful `gaia install` proves external functionality. Search/filter for dependencies or CLI requirements is valuable, but do not block initial shipping on an unproven broad taxonomy redesign.

## CLI and Skill Heaven boundary

**Skill Tree:** authoritative metadata, environment discovery, read-only plan, scoped user consent and safe native installation/removal receipts; never shell-interpolate untrusted commands.  
**Skill Heaven:** activation/adaptation planner, session-only Essence and truthful run receipts; console presentation later projects the same contract if available.  
No second installer or hidden reliance on #196. No persistent changes in Essence mode. User and repository constraints outrank third-party skill instructions. Missing equivalence must be marked reduced/blocked.

## October 2026 dependency-gap audit

Prepare a registry-wide audit for October, with an evidence-based queue rather than a speculative automatic backfill. **Prioritize Graft and Graphify**, both already represented in the tree, then Office skills, Firecrawl, CLI-generated skills, suites, scripts, external services and harness-specific orchestration.

Per record inspect primary source, discoverable `SKILL.md` or CLI-mediated generation flow, runtime dependencies, actual execution commands, permissions, cost and verification. Produce:
1. denominator and coverage stats (records inspected, fields populated, unknown, stale, noninstallable, CLI-managed);
2. risk and effort-ranked remediation ledger with upstream links, source commit/time, and confidence;
3. sampled real execution/install parity evidence where safe and authorized;
4. separate issues for substantial upstream packaging gaps and source disputes;
5. follow-up passes for sustainable refresh/monitoring, not invented dependency values.

**Graphify caution:** current `safishamsi/graphify` registry installation link points to `graphify/__init__.py`, and #1445 noted unresolved install shape. Determine whether native package/CLI generates a skill before making claims. **Graft:** inspect its actual registered records and upstream entrypoint, not assumed behavior. No counterfeit upstream SKILL.md. Preserve trust grading absent independent recalibration evidence.

## Pilot acceptance and release gate

Prove Office skills, Firecrawl, Graphify and Herdr-methodology-on-OpenCode-subagent adaptation. Include Graft in dependency metadata audit readiness and add a runnable pilot if source/tooling permits. Test read-only/no-write preflight, denied consent, shell injection/hostile instructions, no-install Essence, distinct native-vs-reduced receipts, missing tools, rollback and cross-platform behavior.

Implementation owner must land reviewed PRs, test website/model/API parity and document actual installation results. A docs-only handoff can be fast-merged with optional checks skipped **only where repository rules permit**. This handoff itself does not complete #2063 or #199.

## Routing

Execute [Skill Tree #2063](https://github.com/gaia-research/gaia-skill-tree/issues/2063) as the canonical registry+CLI+website lane, coordinated with [Skill Heaven #199](https://github.com/gaia-research/gaia-skill-heaven/issues/199). Keep [#196](https://github.com/gaia-research/gaia-skill-heaven/pull/196), the Desktop Mod, and other masterplans outside critical path. File the October audit execution follow-up when initial schema and coverage tooling can produce verifiable denominators.
