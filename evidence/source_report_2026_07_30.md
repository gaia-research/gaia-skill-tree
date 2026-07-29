# Trust Methodology Source Report

**Date:** July 30, 2026
**Subject:** Evidence Seed Pipeline Run — Gaia Intake Queue (11 Skills)

---

## 1. Overview

This report covers the evidence seed pipeline run executed on 2026-07-30 for 11 skills from the Gaia intake queue (issues #1123, #1243, #1251, #1252, #1266, #1332, #1379, #1380). It was preceded by adversarial audits across all 11 skill slots and a link-validation sweep across 53 unique URLs. One suite skill (`disler/agent-fusion`) received a full Trust Magnitude suite appraisal.

---

## 2. Pipeline Run Summary

| Metric | Value |
|---|---|
| Skills processed | 11 |
| Named slugs ingested | 11 (including 1 suite) |
| New technical evidence rows | 10 (across all slots) |
| New social evidence rows | 37 (across all slots) |
| Unique URLs validated | 53 |
| Live links (200 OK) | 53 |
| Dead links (404) | 0 |
| Adversarial audit slots with blocks | 10 of 11 |
| Adversarial audit slots — pass-with-warnings only | 1 of 11 |
| Total blocked findings | 28 |
| Total warned findings | 30 |
| Total clean findings | 2 |

---

## 3. Per-Skill Sections

### 3.1 `token-observability` — gaia-research/skill-cost (Issue #1123)

**New evidence rows:** 2 (1 technical, 1 social)

- New technical: repo-own confirmation (multi-harness JSONL cost reporter, stdlib Python, prices.json CI-refreshed weekly).
- New social: github-stars-own (1 star, 0 forks at scrape time) — Stage-1 tier, modest signal.
- No Stage-2 evidence found. Searches for benchmark-result, arxiv, peer-review, and richer social-signal returned no direct hits. The arXiv paper arXiv:2606.09421 was considered but covers skill rewriting for token-cost reduction — a distinct problem domain — and was excluded. A Medium article describing an independent workspace token analyzer was also excluded (no mention of this repo).
- Rate limiting was a constraint; all 9 searches were eventually completed.

**Adversarial audit:** 1 blocked, 1 warned, 0 clean.

**Link validation:** 3 live, 0 dead.

---

### 3.2 `format-output` — ayghri/format-output (Issue #1252)

**New evidence rows:** 7 (2 technical, 5 social)

- New technical: SKILL.md blob/ path confirmed (correct); evals/ directory with 14-case weighted rubric harness (added 2026-07-22) — infrastructure confirmed but no published numerical results committed, so no benchmark-result upgrade.
- New social: Star growth trajectory (13,300 stars at scrape time; a Medium search result recorded 8,497 stars with +1,699 in a single day; repo debuted at ~7K stars on launch day). Strong viral growth signal.
- No arxiv or peer-review evidence found that is genuinely about this skill.

**Adversarial audit:** 1 blocked, 4 warned, 2 clean.

**Link validation:** 8 live, 0 dead.

---

### 3.3 `ux-audit` — nextlevelbuilder/ux-audit (Issue #1251)

**New evidence rows:** 7 (2 technical, 5 social)

- New technical: arXiv:2605.03353 (SkCC, accepted ACM CAIS 2026 Agent Skills Workshop) cites this repo as a real-world skill example in its test corpus. This is the first confirmed academic citation for this skill. The citation is indirect (the skill is a test subject for the SkCC compiler pipeline, not independently evaluated). Snyk editorial listing alongside official Anthropic/Vercel skills also logged as technical-social hybrid signal.
- New social: Repo grew from ~29k stars (Snyk article date) to 111k stars and 11.8k forks at current scrape. Two YouTube tutorials from the same channel (AI Stack Engineer) together account for ~53k verified views.
- No benchmark-result or standalone arxiv paper directly evaluating design output quality found.

**Adversarial audit:** 7 blocked, 0 warned, 0 clean.

**Link validation:** 7 live, 0 dead.

---

### 3.4 `scroll-world` — oso95/scroll-world (Issue #1266)

**New evidence rows:** 6 (1 technical, 5 social)

- New technical: repo-own confirmation (MIT, oso95). Repo reached 5.7k stars / 651 forks; Hyperautomation Labs recorded 2,596 stars in its first 10 days.
- New social: Two dedicated YouTube videos with verified view counts (64,616 and 11,008 views); a detailed blog post by a 156K-subscriber channel; a Korean-language tutorial confirming international reach.
- No academic papers, benchmarks, or peer-review evidence found — expected for a creative/production workflow tool.
- Curation note: The Chase AI blog post credits "Peter Wing" as the original author (oso95 is the GitHub handle). The cth9191 fork is a community fork, not canonical upstream.

**Adversarial audit:** 2 blocked, 4 warned, 0 clean.

**Link validation:** 8 live, 0 dead.

---

### 3.5 `agent-reach` — Panniantong/agent-reach (Issue #1332)

**New evidence rows:** 7 (0 technical, 7 social)

- New technical: 0. All six academic/benchmark searches returned irrelevant results. No arxiv or peer-review evidence found.
- New social: ~62.3k GitHub stars at discovery. LobeHub marketplace: 10.2k views, 1.4k installs. Better Stack YouTube tutorial: 12,600 views. SitePoint full tutorial (March 2026). Strong multi-platform social traction.
- Curation flag: The LobeHub SKILL.md link uses a `tree/` path rather than `blob/` path — must be corrected for installability before ingest.
- Classifier note: NEW_GENERIC, not agent-eval. The skill is an internet-access router, not an evaluation methodology.

**Adversarial audit:** 4 blocked, 3 warned, 0 clean.

**Link validation:** 9 live, 0 dead.

---

### 3.6 `react-performance-optimization` — vercel-labs/vercel-react-best-practices (Issue #1379)

**New evidence rows:** 8 (3 technical, 5 social)

- New technical: SKILL.md confirmed at blob/ path. 70 React/Next.js performance rules across 8 prioritized categories — substantively richer than a generic description. Parent repo vercel-labs/agent-skills: 29.6k stars, 2.7k forks.
- New social: InfoQ article (Feb 27 2026) and BetterStack YouTube video (26,698 views) are the strongest Stage-2 social signals. Vercel official docs listing is first-party self-attestation.
- No benchmark-result or arxiv paper found directly evaluating this skill's efficacy.

**Adversarial audit:** 4 blocked, 4 warned, 0 clean.

**Link validation:** 8 live, 0 dead.

---

### 3.7 `static-artwork-design` — anthropics/canvas-design (Issue #1380)

**New evidence rows:** 6 (2 technical, 4 social)

- New technical: OpenSkillEval arXiv paper (arXiv:2605.23657, May 2026) directly benchmarks canvas-design in a Poster Generation category across 10 models with numeric scores (3.56–4.09 range, skill delta -2.08). Peer-reviewed evaluation framework, not self-attestation. Already cited by two subsequent arxiv papers (2606.20659, 2606.10388). Parent repo anthropics/skills: 165k stars, 19.6k forks. Reported as benchmark-result with raw Likert-scale scores clearly noted (not percentile).
- New social: YouTube video "How to Use Claude Skills as a Designer" (245,613 views, Mar 2026) has a dedicated canvas-design chapter — strongest social-signal evidence in this batch.
- MAP note: canvas-design maps to static-artwork-design (not agentic-workflow-design). OpenSkillEval classifies it under "Poster Generation" supporting this MAP decision.

**Adversarial audit:** 2 blocked, 5 warned, 0 clean.

**Link validation:** 3 live, 0 dead.

---

### 3.8 `opinion` — disler/opinion (Issue #1243)

**New evidence rows:** 2 (0 technical, 2 social)

- New technical: 0. No benchmark-result, arxiv, or peer-review evidence found for this skill or repo.
- New social: IndyDevDan YouTube video (34,833 verified views, 8 days old at discovery) directly demoing /opinion. One low-signal note.com Japanese blog post found (view count unverifiable).
- Stage-1 evidence (238 GitHub stars, repo-own) already captured by gaia push.

**Adversarial audit:** 2 blocked, 3 warned, 0 clean.

**Link validation:** 5 live, 0 dead.

---

### 3.9 `plan-synthesis` — disler/merged-plan (Issue #1243)

**New evidence rows:** 3 (0 technical, 3 social)

- New technical: 0. Repo is very new (created 2026-07-16, ~13 days old at discovery). No arxiv papers, benchmarks, or peer-review found.
- New social: IndyDevDan YouTube video (34,833 verified views) demonstrates the skill. Rapid star growth (238 stars in ~2 weeks) is notable but Stage-1 evidence already captured. Skill implements plan synthesis via multi-model output merging — FUSION agent receives parallel answers from two frontier models, merges into a definitive fused answer with a consensus/divergence section.
- SKILL.md link confirmed as blob/ path.

**Adversarial audit:** 2 blocked, 2 warned, 0 clean.

**Link validation:** 2 live, 0 dead.

---

### 3.10 `auto-review` — disler/auto-validate (Issue #1243)

**New evidence rows:** 1 (0 technical, 1 social)

- New technical: 0. No arxiv papers, peer-reviewed publications, or benchmark results with numeric metrics found.
- New social: IndyDevDan YouTube video (34,833 views) prominently features /auto validate as a core harness command. A LinkedIn post by Gabor Szabo was found but view/engagement count unverifiable (LinkedIn blocked); excluded per social-signal rules. A udp.run GitHub trending mention returned no content on scrape; excluded.
- SKILL.md link confirmed as blob/ path.

**Adversarial audit:** pass-with-warnings, 0 blocked, 1 warned, 0 clean.

**Link validation:** (included in plan-synthesis sweep; shared URL set).

---

### 3.11 `agent-fusion` — disler/agent-fusion (Issue #1243) [SUITE]

**New evidence rows:** 6 (2 technical, 4 social)

- New technical: OpenRouter DRACO benchmark post (referenced in README) validates the fusion pattern architecture: Fable 5 + GPT-5.5 fused scored 69.0% vs 65.3% solo on 100 deep-research tasks. This validates the architectural pattern, not the harness code specifically. Repo: 238 stars, 51 forks, sole contributor (disler), created 2026-07-16 (~13 days old at discovery).
- New social: IndyDevDan YouTube video (34,833 views, ~8 days post-publish, README-linked). Multiple LinkedIn posts reference fusion-harness in the context of model fusion as a standard pattern (LinkedIn scraping blocked; view counts unverifiable — not logged as verified evidence). No dev.to or Medium articles specifically covering disler/fusion-harness found.
- Repo has no description field on GitHub, no releases.

**Suite TM appraisal result:**

| Repo | Archived | Stars | Components | Repo signals | TM by type | Total | Grade |
|---|---:|---:|---:|---|---|---:|---|
| `disler/fusion-harness` | False | 238 | 3 | 1 commits / 1 contributors | github-stars-own=0.08, repo-own=1.2, fusion-recipe=90.0 | 91.28 | B |

**Adversarial audit:** 3 blocked, 3 warned, 0 clean.

**Link validation:** (shared URL set with disler cluster).

---

## 4. Suite TM Interpretation — disler/agent-fusion

**Current Grade B (TM: 91.28)**

The grade is almost entirely carried by the `fusion-recipe` derived score (90.0 out of 91.28 total). Direct repo signals are minimal: github-stars-own contributes only 0.08 and repo-own only 1.2, reflecting a 13-day-old repo with 238 stars and a single contributor. The suite has 3 declared components (opinion, merged-plan, auto-validate).

**What would push to Grade A:**

1. **Independent social-signal verification at scale.** The IndyDevDan video (34,833 views) is promising but is a single channel with the author's direct collaboration. A second independent tutorial or write-up from an unaffiliated author would materially strengthen social evidence.
2. **Benchmark-result entry with percentile.** The DRACO benchmark reference in the README validates the architectural *pattern* but is not a direct evaluation of this repo's code. A direct benchmark result — e.g. community-published evaluation comparing fusion-harness output to solo-model output on a defined task set, with a numeric percentile — would be the single highest-impact upgrade.
3. **Repo growth over time.** The repo is 13 days old. At 238 stars now, trajectory matters. At ~1,000 stars with multiple contributors, github-stars-own and repo-own scores will increase meaningfully, shifting the grade from recipe-dependent to multi-signal.
4. **Peer-review or academic citation.** No arxiv paper references disler/fusion-harness directly. An independent academic treatment of the fusion-harness pattern referencing this repo would add a verified technical evidence tier.

Until at least one of (1) or (2) is met, Grade B is appropriate. The recipe score keeps it above Grade C but Grade A requires corroborating non-recipe evidence.

---

## 5. Recommendations for /gaia-ingest-batch

### Evidence-ready for ingest (no rework needed)

| Skill | Reason |
|---|---|
| `format-output` (ayghri) | Viral growth documented, blob/ path correct, evals infrastructure noted but not blocking |
| `ux-audit` (nextlevelbuilder) | Academic citation confirmed, strong star/view counts, no link issues |
| `scroll-world` (oso95) | Verified YouTube signals, repo confirmed, no link issues; author attribution discrepancy is cosmetic |
| `react-performance-optimization` (vercel-labs) | Blob/ path correct, strong parent-repo signal, InfoQ + YouTube social signal |
| `static-artwork-design` (anthropics/canvas-design) | Benchmark paper (arXiv:2605.23657) confirmed, 245k-view YouTube signal, blob/ path correct |
| `opinion` (disler) | Single strong social-signal, Stage-1 already captured; modest but complete |
| `plan-synthesis` (disler/merged-plan) | Shared YouTube signal, blob/ path correct; low signal expected for a 13-day-old skill |
| `auto-review` (disler/auto-validate) | Pass-with-warnings (no blocks); blob/ path correct; shared YouTube signal |
| `agent-fusion` (disler) [SUITE] | Grade B suite appraisal complete; ingest with Grade B designation |
| `token-observability` (gaia-research/skill-cost) | Stage-1 evidence complete; no Stage-2 found but absence documented |

### Needs rework before ingest

| Skill | Required fix |
|---|---|
| `agent-reach` (Panniantong) | SKILL.md link in LobeHub entry uses `tree/` path instead of `blob/` — must be corrected to `blob/main/...` per Curation Guidelines before ingest. Strong social signals will hold once the path is fixed. |

---

## 6. Collectors Directory Index

*   **Raw Evidence Dumps:**
    *   [Tiers 1–2 Raw Evidence](file:///home/gaia-skill-tree/evidence/collectors/tiers_1_2_evidence.md)
    *   [Tiers 3–6 Raw Evidence](file:///home/gaia-skill-tree/evidence/collectors/tiers_3_6_evidence.md)
*   **Social & Engagement Signals:**
    *   [YouTube Showcase Videos](file:///home/gaia-skill-tree/evidence/collectors/social/youtube_showcases.md)
    *   [Developer Blogs & Newsletters](file:///home/gaia-skill-tree/evidence/collectors/social/blogs_newsletters.md)
*   **Technical & Academic Evaluations:**
    *   [Objective Benchmark Results](file:///home/gaia-skill-tree/evidence/collectors/technical/benchmark_results.md)
    *   [Structured Peer Reviews & Audits](file:///home/gaia-skill-tree/evidence/collectors/technical/peer_reviews_audits.md)
    *   [Academic Papers & arXiv Preprints](file:///home/gaia-skill-tree/evidence/collectors/technical/academic_papers.md)
*   **Adversarial Audit Logs:**
    *   [Firecrawl URL Verification Sweep — 2026-07-30](file:///home/gaia-skill-tree/evidence/collectors/verification/firecrawl_validation_report_2026_07_30.md)
