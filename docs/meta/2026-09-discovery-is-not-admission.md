---
title: "Discovery Is Not Admission: What 95 Agent-Skill Candidates Taught Us"
author: "Gaia Research"
summary: "Five upstream release streams produced 95 candidate skills. A reviewed integration accepted 38, mapped 40 to existing capabilities, omitted 17, and deferred none."
abstract: |
  Automated discovery can find more candidate skills than a registry should admit. In a single Gaia Skill Tree integration, five upstream release streams surfaced 95 candidates. Review accepted 38, mapped 40 to capabilities already represented, omitted 17, and deferred none. Thirty-one ambiguous cases received an explicitly stronger review pass; the final integration record shows no unresolved escalations. The engineering lesson is not that one batch proves a universal method, but that discovery needs its own admission system: source evidence, semantic deduplication, escalation, and one coherent integration boundary.
label: Engineering note
---

## Abstract

## When discovery works, admission becomes the problem

An agent-skill watcher did what it was meant to do: notice upstream release changes and gather possible additions from projects building agent workflows, coding skills, video tools, and persistent agent memory. Five streams converged: [Superpowers](https://github.com/obra/superpowers), [Addy Osmani’s Agent Skills](https://github.com/addyosmani/agent-skills), [Hyperframes](https://github.com/heygen-com/hyperframes), [GBrain](https://github.com/garrytan/gbrain), and [Ruflo/AgentDB](https://github.com/ruvnet/ruflo).

That success created a different question. When a release advertises dozens of plausible skills, should a registry reproduce every name—or identify which behaviors are truly distinct, reusable capabilities?

In this batch, the answer was emphatically not “add all 95.” The reviewed outcomes were 38 accepted, 40 mapped to capabilities Gaia already represented, 17 omitted, and zero deferred. These are measured counts from the [integration record](https://github.com/gaia-research/gaia-skill-tree/pull/1915), not a benchmark of the watcher or a general estimate of curation accuracy.

<figure id="decision-funnel">
  <img src="assets/discovery-is-not-admission.svg" alt="Of 95 candidate skills, 38 were accepted, 40 mapped to existing capabilities, 17 omitted, and zero deferred; only the accepted 38 were additions." style="display:block;max-width:100%;height:auto;margin:auto" />
  <figcaption><strong>Figure 1.</strong> Discovery produced 95 candidates, not 95 additions. Mapping is a useful outcome: it preserves the connection to a distinct upstream implementation without creating a duplicate capability.</figcaption>
</figure>

## A name is not a capability boundary

Upstream projects package work for their own tools and communities. That context is valuable, but it does not determine whether each folder deserves a separate place in a cross-project registry.

The release-pinned source files show why the question has to be semantic. Superpowers describes a software-development methodology and includes explicit procedures for [test-driven development](https://github.com/obra/superpowers/blob/v6.4.1/skills/test-driven-development/SKILL.md) and [writing skills](https://github.com/obra/superpowers/blob/v6.4.1/skills/writing-skills/SKILL.md). Addy’s collection includes practices such as [doubt-driven development](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/doubt-driven-development/SKILL.md) and [source-driven development](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/source-driven-development/SKILL.md). Hyperframes describes an agent-oriented way to create video from HTML, with workflows such as [general video composition](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/general-video/SKILL.md). GBrain is an agent “brain” project whose release contains workflows spanning research, knowledge intake, and maintenance; its [research-compendium](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/research-compendium/SKILL.md) is one concrete example. The Ruflo-linked AgentDB change in this batch was narrow: a release/provenance sync, with no candidate skill additions recorded.

These projects are not interchangeable, and the examples above do not imply that each source skill is unique. The same behavior can appear under different names; a distinct behavior can also be buried inside a project-specific package. Names, folder counts, and release notes help locate candidates, but deciding where one capability ends and another begins takes comparison of the actual instructions and existing entries. A shared package format does not answer that semantic question: the [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx) defines a skill directory around a `SKILL.md` file with metadata and instructions, not a cross-project test for capability identity.

That is what “mapped” meant here. It did not mean “rejected as useless.” It meant that the candidate was worth recognizing, but not as another capability entry. Likewise, omission was a deliberate boundary: some items were product-local utilities, narrow wrappers, or otherwise too dependent on the upstream project to stand alone. The registry’s usefulness is not measured by how many directories an upstream release happens to contain.

## Separate throughput from judgment

A dependable process has at least two different kinds of work. Mechanical tasks—collecting source files, preserving provenance, consolidating review packets, and regenerating output—benefit from repeatability and throughput. Deciding whether two procedures express the same capability, or whether a behavior is portable beyond its home product, requires semantic review.

In this integration, 31 cases were explicitly routed through a stronger review pass. The final record says all 31 ended with dispositions and reports zero unresolved escalations. That is different from saying the first pass was right, or that every hard case can be resolved automatically. The [final integration record](https://github.com/gaia-research/gaia-skill-tree/blob/main/docs/agents/upstream-integration-2026-09-23.md) says eight of the 31 dispositions differed from the initial proposals after deeper review and maintainer rulings. Escalation was useful precisely because it preserved the chance to revise an earlier interpretation rather than disguising uncertainty as a confident label.

<figure id="review-pipeline">
  <img src="assets/review-architecture.svg" alt="Seven stages: automated discovery, mechanical consolidation, semantic review, stronger review for ambiguity, one combined integration, validation, and merge to main." style="display:block;max-width:100%;height:auto;margin:auto" />
  <figcaption><strong>Figure 2.</strong> Discovery and consolidation can scale; semantic decisions need a review path that makes uncertainty visible and resolvable.</figcaption>
</figure>

This separation is an engineering choice, not a claim that one model or one human is infallible. A practical design pattern is to use cheaper, predictable processing for organizing evidence, then reserve deeper reasoning and human attention for disputed boundaries. Every layer should leave enough provenance for the next reviewer to check what the candidate actually contained and why it was accepted, mapped, omitted, or escalated.

## Many streams, one admission boundary

The five upstream sources did not each get an independent route to the default branch. Their release updates were brought together as inputs to one reviewed integration. The accepted decisions and source changes were assembled, generated projections were rebuilt from the combined source state, and validation ran against that combined result before the integration reached `main`.

That sequence matters because generated files are projections, not independent decisions. Combining already-generated outputs from several branches can preserve incompatible snapshots or create noisy conflicts. Rebuilding after the source decisions converge gives reviewers one coherent result to validate. In this batch, the integration record reports that the combined documentation generation and registry validation passed; it also records that a local documentation check initially found installability-index drift, followed by a timeout on its next local run. The final pull request’s required CI checks passed. Keeping both facts in the receipt is more informative than reducing the verification story to “everything was green.”

GitHub’s documentation describes [pull requests](https://docs.github.com/en/pull-requests/reference/pull-requests) as a place to propose and review changes before merging, and [GitHub Actions](https://docs.github.com/en/actions/get-started/understand-github-actions) as a way to automate repository workflows. Those platform mechanics do not guarantee good curation. They do make it possible to keep many incoming changes reviewable while giving the combined result one explicit merge boundary.

<figure id="integration-boundary">
  <img src="assets/many-signals-one-boundary.svg" alt="Five upstream projects feed candidate packets into shared semantic review; decisions converge into one reviewed integration, then validation, then main." style="display:block;max-width:100%;height:auto;margin:auto" />
  <figcaption><strong>Figure 3.</strong> Multiple sources can produce independent evidence packets without creating multiple unreviewed paths into the shared registry.</figcaption>
</figure>

## A lesson, not a reliability claim

This one batch does not prove a universal optimum for review depth, show that automation is generally reliable, or establish that the same disposition ratios will recur. It does offer a concrete design pattern worth testing in other registries:

- **Treat discovery as candidate generation.** Finding a file or release change is not an admission decision.
- **Compare behavior, not just labels.** Check the upstream instructions against existing capabilities and preserve their source links.
- **Make mapping a first-class outcome.** A duplicate capability can still contain a useful implementation worth linking.
- **Escalate uncertainty with a defined destination.** Stronger review should resolve or explicitly retain uncertainty—not silently convert it to “yes.”
- **Integrate once from canonical inputs.** Rebuild derived outputs after source decisions converge, then validate the assembled state.
- **Record enough to revisit the decision.** A future reviewer should be able to see what changed, which version was inspected, and why the outcome was chosen.

The operational handoff also exposed a genuine improvement area: repeated upstream releases refreshed existing Hyperframes and GBrain release threads, while their accumulated candidates needed to be reviewed as consolidated sets. The [public triage and integration record](https://github.com/gaia-research/gaia-skill-tree/blob/main/docs/agents/upstream-integration-2026-09-23.md) documents those refreshes and the decision to consolidate rather than treat each as a clean-slate intake. That is evidence of duplicate-work pressure in this batch—not evidence that the watcher made duplicate admissions. A next iteration could make “already reviewed at this source revision” easier to detect while still allowing a changed source file to re-enter review.

The most useful output of an automated discovery system may therefore be neither a larger list nor a higher acceptance count. It may be a well-sourced set of candidates, explicit non-admissions, and a review boundary that lets people say “already represented,” “not portable,” or “needs another look” without losing the evidence that prompted the question.

## References

[1] obra. (2026). *Superpowers: Agentic skills framework and software development methodology*. Source repository and release-pinned [test-driven development](https://github.com/obra/superpowers/blob/v6.4.1/skills/test-driven-development/SKILL.md) and [writing-skills](https://github.com/obra/superpowers/blob/v6.4.1/skills/writing-skills/SKILL.md) source files. [Repository](https://github.com/obra/superpowers).

[2] Addy Osmani. (2026). *Agent Skills: Production-grade engineering skills for AI coding agents*. Source repository, release `0.6.10`; examples: [doubt-driven development](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/doubt-driven-development/SKILL.md) and [source-driven development](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/source-driven-development/SKILL.md). [Repository](https://github.com/addyosmani/agent-skills).

[3] HeyGen. (2026). *Hyperframes: Write HTML. Render video. Built for agents.* Release-pinned [general-video skill](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/general-video/SKILL.md). [Repository](https://github.com/heygen-com/hyperframes).

[4] Garry Tan. (2026). *GBrain: Garry’s opinionated OpenClaw/Hermes agent brain*. Release-pinned [research-compendium skill](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/research-compendium/SKILL.md). [Repository](https://github.com/garrytan/gbrain).

[5] ruvnet. (2026). *Ruflo: agent harness and orchestration project*. The integration synced Ruflo’s AgentDB-linked release metadata at v3.42.4; no candidate skills were added from that stream. [Ruflo repository](https://github.com/ruvnet/ruflo) · [release tag](https://github.com/ruvnet/ruflo/tree/v3.42.4) · [AgentDB project](https://github.com/ruvnet/agentdb).

[6] Gaia Research. (2026). *Upstream watcher backlog — 2026-09-23*. Public integration pull request [#1915](https://github.com/gaia-research/gaia-skill-tree/pull/1915) and its [decision and validation receipt](https://github.com/gaia-research/gaia-skill-tree/blob/main/docs/agents/upstream-integration-2026-09-23.md). These are the sources for batch counts, stronger-review count, final escalation status, integration topology, and validation details.

[7] GitHub Docs. *About pull requests*. [https://docs.github.com/en/pull-requests/reference/pull-requests](https://docs.github.com/en/pull-requests/reference/pull-requests).

[8] GitHub Docs. *Understanding GitHub Actions*. [https://docs.github.com/en/actions/get-started/understand-github-actions](https://docs.github.com/en/actions/get-started/understand-github-actions).

[9] Agent Skills. *Agent Skills specification*. Public documentation for the convention of packaging agent instructions in skill files. [Specification source](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx).
