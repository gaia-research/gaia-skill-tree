# Gaia Engineering Routines

Routines are recurring stewardship jobs for an agent that has time to improve the repository but no feature brief. They are not scripts, rigid checklists, or substitutes for judgment. Each routine names an outcome, the evidence that should trigger it, the boundaries it must respect, and the proof required before it can stop.

This catalog stays deliberately high level. The agent should inspect the current repository, choose the smallest valuable intervention, and retain agency over implementation.

## Gaia Steward

The new `STEWARD.md` supersedes routines as of 08-09-2026. This document is maintained as a reference of all routines. This can be viewed at https://github.com/marcotiongson/gaia-skill-tree/blob/main/STEWARD.md

## Existing routines

Two self-contained routines already live in `docs/en/`:

- **English documentation stewardship** — `docs/en/ROUTINE_PROMPT.md`, supported by `DOCS.md` and `MEMORY.md`.
- **First-time skill submission learning routine** — the self-contained `MISSION.md`, `NOTES.md`, and `RESOURCES.md` package.

Do not duplicate either routine here. This file covers the rest of the repository.

## How to choose

1. Establish ground truth from the live tree, recent history, current failures, and the relevant source-of-truth documents.
2. Find evidence of a real problem or measurable opportunity. Do not manufacture work to satisfy a schedule.
3. Select by the **primary risk**, not every surface touched: code structure, tests, runtime contract, canonical data, build/release, public frontend, security, or knowledge drift.
4. Choose one routine first. Expand only when its evidence reveals a dependency owned by another routine.
5. Prefer diagnosis before mutation and the smallest coherent improvement over a broad cleanup.
6. Prove the outcome and stop. A routine is not permission to tidy unrelated surfaces.

If no routine owns the evidence, record **no routine selected** and stop, or route directly to the applicable project skill.

These routines define stewardship outcomes and selection criteria. When an existing project skill owns execution—evidence verification, curation, Trust Magnitude inspection, timeline repair, generated-doc sync, design review, CI churn, release, or PR review—invoke that skill rather than recreating its procedure here.

The trigger conditions below are prompts to inspect, not obligations to edit. A healthy run may conclude that no change is warranted.

## Non-negotiable boundaries

Every routine inherits the repository rules in `AGENTS.md`, `CLAUDE.md`, and the nearest domain instructions. Consult `CONTEXT.md` for nomenclature and user-facing product language, and `META.md` for registry policy.

- Never push directly to `main`. Confirm branch, worktree, target, and allowed path scope before mutation.
- Use `gaia dev` for canonical registry mutations. Validate the proposed state before writing it.
- Preserve authorization, attribution, and timeline provenance. Never invent evidence or history.
- Never hand-edit timeline arrays or canonical registry state. For a formally documented CLI gap, follow the exact current workaround and still emit required provenance.
- Distinguish canonical sources, tracked Class S projections, and gitignored Class P outputs.
- Do not mutate skill data, evidence, stars, schemas, or user trees without the applicable approval.
- Preserve test isolation and honest fast/integration/slow markers.
- Treat visual frontend changes as human-gated and provide rendered evidence.
- Do not weaken security, permissions, validation, or assertions merely to make a check green.
- Keep mirrored project skills synchronized across `.agents/skills/` and `.claude/skills/`.
- Do not commit secrets, binary masters, local output, or unrelated generated churn.
- Follow the approval gates in `AGENTS.md`, `CLAUDE.md`, `META.md`, and the applicable project skill. This catalog grants no approval by itself.

---

## 1. Dead-Code Gardener

**Outcome:** Unreachable code, expired compatibility paths, unused assets, abandoned scripts, and obsolete configuration disappear before they become misleading architecture.

**Run when:** A migration has settled, a feature has been removed, stale paths repeatedly confuse contributors, or analysis finds code with no credible consumer.

**Operating boundaries:** Prove absence of use across direct calls, runtime discovery, dynamic imports, packaging, workflows, docs, and supported external contracts. Prefer deletion over indefinite deprecation, but preserve compatibility while a supported consumer still needs it. Do not delete unfamiliar code on static analysis alone.

**Proof:** Usage and contract evidence, a focused deletion diff, relevant tests and package smoke checks, and no stale active references.

## 2. Architecture and Abstraction Doctor

**Outcome:** Modules have clear responsibilities, dependencies point in a sensible direction, and shared concepts have one authoritative implementation.

**Run when:** A change requires synchronized edits in many places, logic is copied across commands/scripts/renderers, large high-churn modules repeatedly fail, or a subsystem becomes difficult to test.

**Operating boundaries:** Diagnose with coupling, churn, duplication, and defect evidence—not line count alone. Extract abstractions around demonstrated variation; do not build frameworks for hypothetical futures. Prefer bounded seams over whole-system rewrites. Preserve public contracts unless migration is explicit.

**Proof:** A concise hotspot or dependency explanation, a stated boundary decision, measurable reduction in duplication/coupling/complexity, and focused behavioral tests.

## 3. Error, Diagnostics, and Incident Learner

**Outcome:** Failures are explicit, actionable, safe, reproducible, and less likely to recur in the same form.

**Run when:** Exceptions are swallowed, failures return success, CI output cannot locate the invariant, users cannot recover from an error, or an incident/repeated regression has just been resolved.

**Operating boundaries:** Preserve intentional best-effort behavior but label degraded results honestly. Do not leak secrets or sensitive paths. Improve the cheapest durable layer—error contract, test, guard, or guidance—rather than adding noise everywhere. Do not turn one incident into a speculative rewrite.

**Proof:** Reproduction and root cause, verified exit/log behavior, a clear recovery path, and one durable regression barrier proportional to the failure.

## 4. Test Portfolio Gardener

**Outcome:** The test suite protects current behavior at the right layer and cost, without preserving duplicate or obsolete expectations.

**Run when:** Behavior changes, a migration lands, test time grows, markers drift, coverage follows implementation details, or an area repeatedly regresses without useful protection.

**Operating boundaries:** Add tests for meaningful contracts and failure modes, not every line. Remove or archive tests that assert retired behavior, duplicate stronger coverage, or obstruct legitimate refactoring. Never remove a test merely because it fails; first decide whether the product, test, or specification is wrong. Optimize tier placement before dropping coverage.

**Proof:** Rationale for additions/removals, honest marker and tier placement, stable collection, relevant passing tiers, and improved signal relative to cost.

## 5. Flake and Isolation Hunter

**Outcome:** Intermittent failures become deterministic product defects, deterministic test defects, or explicitly bounded environmental exceptions.

**Run when:** CI reruns change outcomes, timeouts recur, order affects results, or tests touch clocks, processes, networks, global state, or shared filesystems.

**Operating boundaries:** Reproduce under controlled repetition. Prefer injected clocks, network seams, temporary homes, and explicit subprocess handling over sleeps and retries. Preserve process-replacement protections. Quarantine only with evidence and a clear exit condition.

**Proof:** Repetition evidence, failure classification, a deterministic repair or justified quarantine, and confirmation that isolation still holds.

## 6. CLI and Runtime Contract Steward

**Outcome:** Supported commands are discoverable, internally consistent, safe to configure, responsive enough for their purpose, and usable from a clean installation.

**Run when:** Commands, flags, imports, optional dependencies, config resolution, workspace behavior, or packaged entrypoints change; help output drifts; or startup/I/O regresses.

**Operating boundaries:** Treat command names, options, exit codes, machine output, and resolution precedence as public contracts. Keep optional features genuinely optional. Preserve explicit user intent and prevent writes to bundled/read-only targets. Measure before optimizing; add caching only with an invalidation model. Follow published setup rather than local shortcuts.

**Proof:** Discovery/help alignment, changed-contract tests, relevant clean-install and optional-dependency probes, configuration precedence evidence, and measurements for claimed performance improvements.

## 7. Mutation, Authorization, and Abuse-Boundary Examiner

**Outcome:** Every privileged operation validates the future state, authorizes the actor, writes only to an approved target, records provenance, and resists unsafe input.

**Run when:** A mutating command, verifier gate, scanner, redaction rule, workflow permission, or direct-edit workaround changes; or invalid canonical state appears.

**Operating boundaries:** Fail closed. Never bypass verifier controls, timeline logging, branch scope, secret scanning, unsafe-content checks, or explicit writable-target selection for convenience. Distinguish malformed input, hostile input, and unsupported-but-benign input. Route missing mutation capabilities into an explicit CLI design decision rather than an invisible workaround.

**Proof:** Positive and negative behavior across validation, authorization, filesystem effects, provenance, redaction/abuse cases, and least-privilege permissions.

## 8. Schema Evolution Steward

**Outcome:** A schema change arrives with the validators, CLI support, fixtures, migrations, bundled copies, and compatibility story needed to make it real.

**Run when:** A schema or canonical field changes, validation semantics diverge from data, or code starts depending on an unratified shape.

**Operating boundaries:** Establish the authoritative ruling before implementation. Do not mutate canonical data without an approved migration and rollback plan. Keep mirrored schema surfaces in lockstep. Preserve old-reader behavior when compatibility is promised, and do not encode policy in fixtures alone.

**Proof:** Impact map, migration/rollback story, synchronized schemas and consumers, representative old/new compatibility tests, and clean validation.

## 9. Evidence and Trust Reconciler

**Outcome:** Evidence provenance, liveness, type/layer policy, Trust Magnitude, stars, branch rules, installability, and promotion gates tell one coherent story.

**Run when:** Evidence is collected or ingested, policies change, links decay, a score or stars assignment looks wrong, or promotion/demotion is proposed.

**Operating boundaries:** Use the evidence pipeline and trust skills for execution. Quarantine uncertainty; never invent rows or infer unavailable metrics. Appraise and propose rather than auto-promoting or auto-demoting. Preserve no-self-promotion, Origin, reviewer, tenure, benchmark, and Star Bar rules.

**Proof:** Accepted/rejected evidence with reasons, per-skill calculation and gate explanation, dead or discounted evidence identified, and explicit human decisions for canonical changes.

## 10. Timeline Causality Keeper

**Outcome:** Every meaningful lifecycle change is explained by a coherent chain of events across canonical skills and user trees.

**Run when:** Stars, type, identity, fusion, evidence, or migration state changes; validation fails; or displayed history disagrees with current state.

**Operating boundaries:** Use supported timeline and trace tooling. Never hand-edit timeline arrays, fabricate dates, or create provenance merely to satisfy a validator. Follow only the currently documented exception for any missing CLI verb.

**Proof:** Current-state reconciliation, complete causal events, paired migration provenance where required, and clean timeline validation.

## 11. Registry Structure and Installability Examiner

**Outcome:** Prerequisites, generic references, suites, components, capstones, Origins, upstream links, and installer behavior form a unique, acyclic, usable graph.

**Run when:** A skill is added, fused, split, moved, renamed, linked, or assigned to a suite; upstreams move; or installer/link checks fail.

**Operating boundaries:** Keep fusion structure distinct from suite membership. Respect suite-specific and intentional non-installable states. Do not turn a repository homepage into proof of a skill artifact or silently rewrite provenance. Route mutations through approved CLI and curation paths.

**Proof:** Reference/duplicate/DAG analysis, suite and component closure, upstream classification, representative install probes, and a minimal intended graph diff.

## 12. Artifact, Branch, and Repository Hygiene Sentinel

**Outcome:** Canonical sources and tracked projections agree, regeneration is deterministic, and the branch contains only intentional files within its allowed scope.

**Run when:** Registry or rendering sources change, generated checks fail, tooling runs broadly, platform-specific churn appears, or work is ready to commit/push.

**Operating boundaries:** Generate through supported commands. Commit required Class S outputs, leave Class P outputs untracked, exclude documented rolling/platform-sensitive noise, and never hand-repair generated files. Confirm branch, target, worktree, staged paths, attribution, and integration strategy immediately before mutation. Honor explicit binary/redaction exemptions; ask before deleting uncertain data.

**Proof:** Clean generation check and rerun, expected-path classification, clean status, scope/redaction/binary results, correct branch/target, and no unrelated churn.

## 13. CI Architecture and Efficiency Steward

**Outcome:** Workflows provide strong, non-duplicative, least-privilege gates with minimal avoidable iteration cost.

**Run when:** CI repeatedly fails late, runtime grows, workflow ownership overlaps, repository layout changes, permissions drift, or a PR closes after multiple CI-fix rounds.

**Operating boundaries:** Use the CI churn skill for measurement. Separate legitimate feature/review iteration from avoidable churn. Do not remove security or release coverage merely for speed. Prefer precise triggers, earlier local feedback, and clear diagnostics over broad gate removal.

**Proof:** Trigger/responsibility and permission findings, churn/runtime evidence, one bounded improvement or explicit no-change verdict, and unchanged required coverage.

## 14. Release and Supply-Chain Examiner

**Outcome:** Versioned manifests, generated artifacts, package contents, dependencies, actions, tags, claims, and publication systems agree and are reproducible.

**Run when:** Dependencies or lockfiles change, advisories arrive, action versions age, external assets are added, automated version sync completes, or a release is proposed.

**Operating boundaries:** Read-only by default. Never tag, publish, promote, merge to `main`, or auto-accept a major upgrade without the human gate. Evaluate transitive changes, licenses, origins, and built artifacts—not only source manifests. Keep core and optional package expectations distinct.

**Proof:** Version/lockstep and dependency-origin findings, advisory/license disposition, reproducible package contents, clean install outside the repository, workflow status, and post-publication verification when a release is authorized.

## 15. Frontend Quality and Resilience Steward

**Outcome:** Public pages remain functional, accessible, responsive, performant, honest under degraded conditions, and visually coherent.

**Run when:** HTML, CSS, JavaScript, design tokens, navigation, rendering data, entrypoints, caching, or hosting assumptions change; periodically sample core pages after registry growth.

**Operating boundaries:** Test only relevant surfaces, including representative desktop/mobile behavior, keyboard and screen-reader semantics, reduced motion, loading/error/empty states, route depth, and console/network behavior. Apply design-entrypoint and known-surface rules. Do not present stale fallback data as current. Human review owns visual judgment.

**Proof:** Rendered before/after evidence for changed surfaces, relevant interaction/accessibility and degraded-state results, payload/performance evidence for performance claims, and explicit founder approval when gated.

## 16. Browser, Privacy, and External Trust Auditor

**Outcome:** Registry, API, URL, user-controlled, and third-party values cannot become unsafe markup, navigation, data leakage, or misleading browser output.

**Run when:** Browser rendering, HTML sinks, templates, SVG, links, clipboard behavior, API consumption, analytics, CDNs, previews, permissions, or external integrations change.

**Operating boundaries:** Trace data from source to sink and production to third party. Preserve escaping, URL validation, origin separation, and minimal data disclosure rather than trusting current payloads. Do not weaken a guard because fixtures happen to be safe.

**Proof:** Data-flow or sink findings proportional to the change, adversarial regression cases, external-origin/permission disposition, and clean security/privacy guards.

## 17. Knowledge, Nomenclature, and Agent-Surface Editor

**Outcome:** Root docs, agent guidance, project skills, domain docs, public vocabulary, code behavior, and generated references do not contradict one another.

**Run when:** A contract or workflow changes, an agent follows stale guidance, terminology drifts, links break, project skills change, or the routine catalog itself stops routing work clearly.

**Operating boundaries:** Establish source-of-truth precedence before editing. Consult `CONTEXT.md` rather than inventing successor terms. Keep `.agents/skills/` and `.claude/skills/` byte-aligned. Respect archives and generated files. Leave `docs/en` work to its own routine. Update this catalog only from observed runs or incidents, not imagined completeness.

**Proof:** Implementation-grounded contradiction/link/nomenclature findings, synchronized agent surfaces where touched, stale active guidance removed, and a clearer—not larger—routing surface.

---

## Standard routine report

A routine should leave a short, auditable report proportional to the work:

- **Routine selected:** Why this routine, and what evidence triggered it.
- **Ground truth:** Sources, failures, measurements, or recent changes inspected.
- **Finding:** The concrete risk or opportunity, including a no-change verdict when appropriate.
- **Action:** What changed and why it was the smallest coherent intervention.
- **Boundaries honored:** Human gates, data restrictions, source-of-truth rules, and intentionally untouched surfaces.
- **Proof:** Tests, validators, measurements, rendered evidence, clean generation, or install/package results.
- **Residual risk:** Only genuinely independent, out-of-scope risk discovered during the run. A routine may not defer or file follow-up work that is a direct consequence of its own change; finish that work before calling the run complete.

The quality of a routine is not how many files it changes. It is whether the repository ends the run simpler to trust.