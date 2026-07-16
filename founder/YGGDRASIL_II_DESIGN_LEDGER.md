# Yggdrasil II Design-Run — Asset & Decision Ledger

**Purpose:** the single durable record of every asset created/modified and every design decision made during the "Full Gas" end-to-end design run (2026-07-17, EPIC #1002 · #998). Complements the private MEMORY snapshot and the public EPIC proof-of-work. The runbook is `founder/handovers/YGGDRASIL_II_DESIGN_ALIGNMENT.md` §7; this file is the append-only outcome log.

**Branch:** `dev/yggdrasil-ii-staging` · **Commit identity:** `mbtiongson1` (Marcus Rafael B. Tiongson `<153011150+mbtiongson1@users.noreply.github.com>`) · **Target:** design fully integrated into staging, no follow-ups, zero Ygg-I legacy design.

---

## Ratified decisions (locked)

| # | Decision | Rationale |
|---|---|---|
| R1 | `--tier-unique` (#7c3aed violet) promoted to a first-class token family in `tokens.css` (`-rgb/-bg/-border/-edge/-symbol`). It already existed as an inline-hex-fallback value; the run canonicalizes it. Unique = the darker plaque hue. | Uniques need a distinct identity for the dark-plaque directive; no hex fallbacks (CI guard). |
| R2 | Correctness + design bundled per surface, BUT the shared resolver + token land as step 1 of Wave 0 (the plaque PR); everything imports it. One-agent-first, then fan. | The branch-derivation defect has one root; fixing it once prevents 16 re-implementations. |
| R3 | Mobile-first (N-12 deliverable 2) is INSIDE #998, not a spun-off EPIC. | Sprint-completeness ("no follow-ups"): mobile-first is #998's own remainder. |
| R4 | /impeccable design items (OG card, footer, reports, wreath) are reviewer-agent-gated, no founder gate — but reviewer prompts are adversarial (reject-by-default). | Founder chose velocity; the adversarial reviewer is the quality bar. |
| D1 | Gold-wreath frame authored as an SVG (`docs/assets/origin-wreath-gold.svg`), not raster. Replaces the honor-red `#origin-badge` sprite. | Scales cleanly, tokenizable gold, no image-gen dependency. |
| D2 | AOV4 asset set (C1–C6 suite, D4–D6 unique × badge/card/hero) is COMPLETE and reused as-is for plaques/OG/badges. No new rank art generated. | Verified present in `docs/assets/ascension-overdrive/`. |
| D3 | N-3 "frozen profile pages" fixed at the GENERATOR (`generateProfilePages.py` L197/L375), not by hand-editing `docs/u/*/index.html`. About stars likewise. | The pages are generated; source-fix propagates to all handles. |
| D4 | MCP canonical = `@gaia-registry/mcp@0.1.0` + `research.gaiaskilltree.com/mcp`. N-9 also fixes the stale `@gaia-registry/mcp-server` refs (main README is internally inconsistent). Sweep: `docs/index.html`×2, `docs/en/index.html`, `docs/en/mcp-server.html`, `docs/agent.md`, `README.md`×4. | Confirmed against `origin/main:README.md` L245. |
| D5 | N-11 skill-fuse CTA links to `https://github.com/gaia-research/skill-fuse` (verified PUBLIC) + the Research fuse page. Folded with N-9/N-10 into one shared cross-brand "Research product" component (Rimuru-Blue #38bdf8 bridge). | Cross-repo rule governs content, not hyperlinks. |
| D6 | Badge `_assets/*/` SVG regeneration lands on a SEPARATE `infra/badge-*` PR, not the design PR. | CLAUDE.md badge invariant: auto-sync never touches `docs/badges/`; regen is human-reviewed infra. |

---

## Assets created / modified (append per wave)

| Asset | Path | Wave | Status |
|---|---|---|---|
| gold-wreath frame SVG | `docs/assets/origin-wreath-gold.svg` | W0 | ✅ merged (abe32a4bb) |
| shared client resolver | `docs/js/skill-semantics.js` | W0 | ✅ merged (abe32a4bb) — `window.GaiaSemantics.{computeBranch,rankWord,rankLabel}` |
| `--tier-unique` token family | `docs/css/tokens.css` | W0 | ✅ merged (abe32a4bb) |
| plaque.js rewrite (AOV medallions, avatars+wreath, data-branch, no red origin, no GH button) | `docs/js/plaque.js` + `plaque.css` | W0 | ✅ merged (abe32a4bb) |

---

## PR / commit ledger (append per merge)

| Wave | Branch | PR | Merge SHA | Reviewer verdict |
|---|---|---|---|---|
| W0 | design/ygg2-w0-foundation | #1204 | abe32a4bb | PASS (adversarial, Playwright: 153 plaques, 119 avatars=119 wreaths, 0 broken, 0 banned words, desktop+mobile clean) |

**Wave 1 IN FLIGHT** — workflow `wf_d12fde93-4a3`, script `founder/workflows/ygg2-wave1.mjs` (resume via `resumeFromRunId`). Launched 2026-07-17. Run order (concurrency: opus-solo, then sonnet pairs): W1e (opus, Python scripts) → W1a+W1b (heroes, leaderboard) → W1c+W1d (named, explorer+N-11 CTA) → W1f (MCP sweep+N-1/N-2). `skip-scope-check` pre-authorized by founder for all lanes. N-11 URLs verified: repo `github.com/gaia-research/skill-fuse` PUBLIC; live product `research.gaiaskilltree.com/labs/infinite-skill-craft` (README-confirmed).

**Wave 1 RESUME (workflow died mid-run, recovered 2026-07-17):** first run checkpointed but couldn't resume in background fork. Ground-truth from journal + `git ls-remote`: **W1e PASSED** (build→review minor→remediate→re-review PASS; branch `design/ygg2-w1e-python`, 4 scripts + 159 OG SVGs + 47 profiles). **W1a built** (branch pushed, review was in-flight). **W1b built→review FAIL(major)→remediation in-flight** (worktree `w1b-leaderboard-fix`). **W1c/W1d/W1f never started.** Resumed via `resumeFromRunId=wf_d12fde93-4a3` (task `wzkzajpy5`) — cached lanes return instantly, execution continues from W1b remediation + W1c/W1d/W1f.

**⚠️ MERGE-GATE BLOCKER (W1e authorship taint):** branch `design/ygg2-w1e-python` carries **2 of 5 commits authored under `marcotiongson@users.noreply.github.com`** (the UNAPPROVED identity) — `36868a214` (generateProfilePages) and `643b94e36` (generateOgCards). Founder mandate is `mbtiongson1` ONLY. **MUST rewrite these 2 commits' author→`Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>` and force-push BEFORE opening the W1e PR.** W1a (`4350b21c4`) and W1b (`6506028c2`) verified CLEAN. Do the rewrite at merge-prep (workflow not touching W1e), isolated from the running lanes.

**Carried to Wave 1 (from W0 blockers):**
- **W1e MUST teach `scripts/generateCssTokens.py` to emit the `--tier-unique` family** (currently hand-authored in tokens.css; a `gaia dev docs` regen would drop it + re-expose hex fallbacks). May need `registry/schema/meta.json` + a `meta.typeColors.unique` entry — that's a `schema/`-scope change, so W1e (or a sibling schema PR) owns it.
- **W1 CSS cleanup:** prune orphaned `.plaque-orb--extra/--ultimate` dead classes in plaque.css (~L665-680) referencing nonexistent tokens.
- **W1 (skill-explorer lane) confirmed dead reads still live:** `skill-explorer.js:2398` `type==='unique'`+hex; `profile-timeline.js` hex; hero "Honor Red" copy.

---

## Token-spend log (append per push, per CLAUDE.md directive)

Format: `<date> <model> <effort>: <in>k in, <out>k out. ~$<cost>`

- _(pending — logged at each wave close)_
- 2026-07-17 W0 (Opus 4.8 high, workflow build+review): ~212k subagent tokens (build+adversarial review, 2 agents). Orchestrator planning/verify/merge overhead separate. ~$30 est.
