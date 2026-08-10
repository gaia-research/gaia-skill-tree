---
title: "99 Out of 100 Aren't Good Enough"
author: "Gaia Research"
summary: "We ran the skills.sh top-100 leaderboard through our curation pipeline. Here's what survived — and what the numbers say about skills marketplaces."
abstract: |
  skills.sh ranks agent skills by install count. We ran its top 100 non-Microsoft entries through Gaia's mechanical curation pipeline — embedding similarity, deduplication, precedence rules, and human L4 review. The result: only 2 contributors cleared our bar. This post shows the full funnel, flags a suspicious cluster, and introduces the Remotion suite we found along the way.
label: Curation Report
---

## Abstract

skills.sh ranks agent skills by install count. We ran its top 100 non-Microsoft entries through Gaia's mechanical curation pipeline — embedding similarity, deduplication, precedence rules, and human L4 review. The result: only 2 contributors cleared our bar. This post shows the full funnel, flags a suspicious cluster, and introduces the Remotion suite we found along the way.

## The Funnel

We ingested 77 candidate skills from the skills.sh top-100 non-Microsoft leaderboard (75 successfully fetched). Every row went through embedding similarity checks against Gaia's existing 321-node registry, followed by a mechanical deduplication pass, and then L4 human review with precedence and attribution rules applied.

Here's how the funnel collapsed:

| Stage | Count |
|---|---|
| **Total input** | 77 |
| **Total fetched** | 75 |
| **Exact duplicates** (already in Gaia) | 36 |
| **Deferred** (held for investigation) | 8 |
| **Review-ready** (cleared mechanical pass) | 33 |
| **Final approved contributors** | 2 |

Thirty-six of 77 inputs — nearly half — were exact duplicates of skills already in our registry. They weren't bad skills. They just weren't new. skills.sh's leaderboard doesn't know or care whether a skill is already in circulation elsewhere. We do.

Of the 33 that reached review-ready status, only two contributors' work was actually approved through human L4 gate: **supabase** and **remotion-dev**. Everyone else either duplicated existing Gaia nodes, failed attribution checks, got flagged as CLI-first rather than capability-first, or triggered active investigation holds.

## The Lark Problem

Here's a number that should give you pause: **50 of the 77 input packets** came from just one vendor — Lark/Feishu. Specifically: 27 packets had `open.feishu.cn` as their hostRepository, and another 23 had `larksuite/cli`. That's the same product appearing under two different source identities on the same leaderboard.

Lark is a collaboration platform made by ByteDance. larksuite.com and feishu.cn are the international and China-facing versions of the same product. The fact that they are represented as *separate skill authors* on skills.sh — and together account for nearly two-thirds of our input batch — is a meaningful signal about how their install count got that high.

We are not saying the Lark skills are useless. We are saying: when a single product line accounts for the majority of a leaderboard and shows up under two different source identities, that leaderboard is not measuring ecosystem breadth. It's measuring bundling. Install count for a skill that ships pre-configured with a major SaaS platform is not the same signal as install count for a community-authored skill that people deliberately sought out and installed.

All Lark rows are held pending investigation (see [issue #1512](https://github.com/gaia-research/gaia-skill-tree/issues/1512)). We need to resolve the canonical source topology — which repo is authoritative, who actually authors these skills, and whether the split is structural or cosmetic — before any of them get a registry node.

## Why Install Count Is a Bad Signal

skills.sh is essentially an npm registry for agent skills. Like npm, it is good at tracking distribution. Like npm, it is bad at tracking quality. Install count tells you how many agents have downloaded a file. It does not tell you whether the file describes a real, reusable capability, whether anyone actually verified the author wrote what they claim, or whether the skill would survive contact with a codebase that isn't the vendor's own product.

We are attribution-driven, not distribution-driven. Every Gaia registry node traces back to a real author, a real repo, and a real demonstrated capability. Trust Magnitude — our scoring system — weights peer review, benchmark evidence, and independently verifiable source quality. A skill with 472,000 installs and zero peer review evidence does not automatically outrank a skill with 12,000 installs and two independent benchmark citations.

This matters more as the ecosystem matures. The era of "install everything, sort it out later" produced npm's current state: millions of packages, a few thousand that actually matter, and a long tail of abandoned or trivially duplicated code. We are deliberately building a smaller, curated graph. The skills.sh run confirmed: if we had blindly imported the top 100, we would have duplicated roughly half our registry and introduced at least one leaderboard-inflated vendor cluster. Hard pass.

## What Actually Passed

**Supabase** — both their core skill and their Postgres best practices skill — passed cleanly. The Postgres one is worth noting: it comes in at rank 99 on the leaderboard with 338,426 installs, and its scope is genuinely broad. It's not just "use Supabase Postgres." It covers schema design, migrations, RLS policies, pgvector, pg_cron, pgmq, EXPLAIN plan analysis, connection exhaustion, locking, bloat — the full stack of operational Postgres concerns. The skill earns its place on capability grounds, not install count. Rank 99 on skills.sh; approved.

**Remotion** is the more interesting story. The skills.sh entry is rank 55, 472,033 installs, one skill. We pulled the source repo (`remotion-dev/skills`) and found twelve distinct skills covering the full Remotion production pipeline: core API, Lambda rendering, Player embedding, Cloudflare Workers, CLI tooling, GitHub Actions integration, Tailwind compatibility, and more. The single leaderboard entry was essentially a compressed archive of a complete skill suite. We expanded it. That's what good curation looks like — you don't just stamp the manifest, you find the actual shape of the capability and model it properly.

The Remotion suite is approved with one open question: issue [#1513](https://github.com/gaia-research/gaia-skill-tree/issues/1513) tracks whether the suite qualifies for router/suite elevation. That's a separate calibration question; the skills themselves cleared the bar.

## On Demotion

A short honest note: both the remotion-* skills and the supabase-* skills are tagged as non-standalone. They describe capabilities that are entirely specific to a single product ecosystem. That's not disqualifying — many valuable skills are product-specific — but it does create a ceiling on how highly they can rank without broader adoption evidence.

A future calibration pass may lower these skills one level under a "non-standalone" classification. The reasoning: a skill tied entirely to Remotion or Supabase cannot transfer to adjacent work without the product. That's a different kind of evidence requirement than, say, a skill about Postgres index design, which travels across any Postgres deployment. We are flagging this now, not acting on it yet. The approved skills keep their current levels while we watch how they perform in practice and gather independent benchmark evidence.

This is a live classification, not a verdict.

## References

- [skills.sh leaderboard](https://skills.sh)
- [remotion-dev/skills](https://github.com/remotion-dev/skills)
- [supabase/agent-skills](https://github.com/supabase/agent-skills)
- [Issue #1512 — Lark/Feishu source topology investigation](https://github.com/gaia-research/gaia-skill-tree/issues/1512)
- [Issue #1513 — Remotion suite router/suite elevation](https://github.com/gaia-research/gaia-skill-tree/issues/1513)
- [Issue #1514](https://github.com/gaia-research/gaia-skill-tree/issues/1514)
- [Issue #1515](https://github.com/gaia-research/gaia-skill-tree/issues/1515)
- [Issue #1516](https://github.com/gaia-research/gaia-skill-tree/issues/1516)
